from __future__ import absolute_import

import datetime
import os
import subprocess

from flask import g, current_app
from flask_script import Command, Option

from yawt.utils import call_plugins, ensure_path, load_file, write_post


def _cfg(key):
    return current_app.config[key]


def _draft_folder():
    return _cfg('YAWT_DRAFT_FOLDER')


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _git_cmd(root_dir, args):
    git_dir = root_dir + '/.git'
    return ['/usr/bin/git', '--git-dir='+git_dir,
            '--work-tree='+root_dir] + args


def _git_mv(root_dir, draft, fullname):
    repo_draft = os.path.join(_draft_folder(), draft)
    repo_fullname = os.path.join(_content_folder(), fullname)
    ensure_path(os.path.dirname(repo_fullname))
    cmd = _git_cmd(root_dir, ['mv', repo_draft, repo_fullname])
    subprocess.check_call(cmd)


def _git_add(root_dir, path):
    subprocess.check_call(_git_cmd(root_dir, ['add', path]))


def _git_commit(root_dir, message):
    subprocess.check_call(_git_cmd(root_dir, ['commit', '-m', message]))


def _git_push(root_dir):
    subprocess.check_call(_git_cmd(root_dir, ['push']))


def _post_fb(post, metadata):
    from facepy import GraphAPI
    token_file = os.path.expanduser(_cfg('YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE'))
    access_tok = load_file(token_file)
    graph = GraphAPI(access_tok)

    print "trying to post to facebook..."
    response = graph.post('me/feed', message=post)
    print "response: "+str(response)
    fid = None
    retid = response['id']
    if retid:
        pids = retid.split('_')
        if len(pids) < 2:
            print "unexpected id format"
        fid = pids[1]
    posturl = _cfg('YAWT_MICROPOST_FB_POST_URL')
    if fid:
        metadata['fbpost'] = posturl % (fid)


def _post_social(post):
    metadata = {}
    for network in current_app.config['YAWT_MICROPOST_NETWORKS']:
        if network == 'facebook':
            _post_fb(post, metadata)
    return metadata


def _extract_tags(post):
    return set([tag.strip('#') for tag in post.split()
                if tag.startswith('#') and len(tag) > 1])


class Micropost(Command):
    """Micropost command"""
    def __init__(self):
        super(Micropost, self).__init__()

    def get_options(self):
        return [Option('post'),
                Option('--commit', '-c', action='store_true'),
                Option('--message', '-m'),
                Option('--push', '-p', action='store_true')]

    def run(self, post, commit, message, push):
        current_app.preprocess_request()

        if not message:
            message = 'posted %s' % (post)

        if self._post(post, commit, message, push):
            call_plugins('on_micropost')

    def _post(self, post, commit, message, push):
        metadata = _post_social(post)
        now = datetime.datetime.now()
        metadata.update({'md_create_time': now.isoformat(),
                         'md_modified_time': now.isoformat()})

        tags = _extract_tags(post)
        if len(tags) > 0:
            metadata['tags'] = ','.join(tags)

        root_dir = g.site.root_dir
        repo_category = os.path.join(_content_folder(),
                                     _cfg('YAWT_MICROPOST_CATEGORY'))
        ensure_path(os.path.join(root_dir, repo_category))

        slug = "%d%d%d%d%d%d" % (now.year, now.month, now.day, now.hour, now.minute, now.second)
        repo_file = os.path.join(repo_category, slug)
        repo_file += "." + _cfg('YAWT_MICROPOST_EXTENSION')
        write_post(metadata, post, os.path.join(root_dir, repo_file))
        if commit:
            _git_add(root_dir, repo_file)
            _git_commit(root_dir, message)
        if push:
            _git_push(root_dir)
            return True
        return False


class YawtMicropost(object):
    """Micropost extension, allowing you to post on Facebook"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_MICROPOST_CATEGORY', 'microposts')
        app.config.setdefault('YAWT_MICROPOST_EXTENSION', 'txt')
        app.config.setdefault('YAWT_MICROPOST_NETWORKS', ['facebook'])
        app.config.setdefault('YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE',
                              '~/.fbaccesstoken')
        app.config.setdefault('YAWT_MICROPOST_FB_POST_URL',
                              'http://www.facebook.com/desmond.rivet/posts/%s')

    def on_cli_init(self, manager):
        """add the micropost command to the CLI manager"""
        manager.add_command('micropost', Micropost())
