from __future__ import absolute_import

import datetime
import os

from flask import g, current_app
from flask_script import Command, Option

from yawt.utils import call_plugins, ensure_path, load_file, write_post
from yawtext.base import Plugin

def _cfg(key):
    return current_app.config[key]


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _post_fb(post):
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
    metadata = {}
    if fid:
        metadata['fbpost'] = posturl % (fid)
    return metadata


def _extract_tags(post):
    return set([tag.strip('#') for tag in post.split()
                if tag.startswith('#') and len(tag) > 1])


def post_social(post, networks=None):
    """Post the supplied post to the supplied social networks.  If none are
    supplied, use the YAWT_MICROPOST_NETWORKS configuration
    """
    networks = networks or current_app.config['YAWT_MICROPOST_NETWORKS']
    metadata = None
    for network in networks:
        if network == 'facebook':
            metadata = _post_fb(post)
    return metadata or {}


def _post(post):
    metadata = post_social(post)
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


class Micropost(Command):
    """Micropost command"""
    def __init__(self):
        super(Micropost, self).__init__()

    def get_options(self):
        return [Option('post')]

    def run(self, post):
        current_app.preprocess_request()
        _post(post)
        call_plugins('on_micropost')


class YawtMicropost(Plugin):
    """Micropost extension, allowing you to post on Facebook"""
    def __init__(self, app=None):
        super(YawtMicropost, self).__init__(app)

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
