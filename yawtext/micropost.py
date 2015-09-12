from __future__ import absolute_import

import os

import datetime

from flask import g, current_app
from flask_script import Command, Option

from yawt.utils import ensure_path, cfg, content_folder
from yawtext import Plugin
from yawtext.facebook import post_fb
from yawtext.twitter import post_twitter


def write_post(metadata, content, filename):
    """Quick and easy way to save a post with metadata"""
    with open(filename, 'w') as f:
        f.write(u'---\n')
        for key in metadata:
            f.write(u'{0}: {1}\n'.format(key, metadata[key]))
        f.write(u'---\n')
        f.write(unicode(content))


def _extract_tags(post):
    return set([tag.strip('#') for tag in post.split()
                if tag.startswith('#') and len(tag) > 1])


def post_social(post, networks=None):
    """Post the supplied post to the supplied social networks.  If none are
    supplied, use the YAWT_MICROPOST_NETWORKS configuration
    """
    networks = networks or current_app.config['YAWT_MICROPOST_NETWORKS']
    metadata = {}
    for network in networks:
        if network == 'facebook':
            metadata.update(post_fb(post))
        elif network == 'twitter':
            metadata.update(post_twitter(post))
    return metadata


def _post_and_save(post, networks):
    metadata = post_social(post, networks)
    now = datetime.datetime.utcnow()
    metadata.update({'create_time': now.isoformat(),
                     'modified_time': now.isoformat()})

    tags = _extract_tags(post)
    if tags:
        metadata['tags'] = ','.join(tags)

    root_dir = g.site.root_dir
    repo_category = os.path.join(content_folder(),
                                 cfg('YAWT_MICROPOST_CATEGORY'))
    ensure_path(os.path.join(root_dir, repo_category))

    slug = "{0:02d}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}"
    slug = slug.format(now.year, now.month, now.day, now.hour, now.minute, now.second)
    repo_file = os.path.join(repo_category, slug)
    repo_file += "." + cfg('YAWT_MICROPOST_EXTENSION')
    write_post(metadata, post, os.path.join(root_dir, repo_file))
    return repo_file


class Micropost(Command):
    """Micropost command"""
    def __init__(self):
        super(Micropost, self).__init__()

    def get_options(self):
        return [Option('post'),
                Option('--network', '-n', action='append', default=[])]

    def run(self, post, network):
        current_app.preprocess_request()
        return _post_and_save(post, network)


class YawtMicropost(Plugin):
    """Micropost extension, allowing you to post on Facebook"""
    def __init__(self, app=None):
        super(YawtMicropost, self).__init__(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_MICROPOST_CATEGORY', 'microposts')
        app.config.setdefault('YAWT_MICROPOST_EXTENSION', 'txt')
        app.config.setdefault('YAWT_MICROPOST_NETWORKS', ['twitter'])
        app.config.setdefault('YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE',
                              '~/.fbaccesstoken')
        app.config.setdefault('YAWT_MICROPOST_FB_POST_URL',
                              'http://www.facebook.com/desmond.rivet/posts/{0}')
        app.config.setdefault('YAWT_MICROPOST_TWITTER_CREDENTIALS_FILE',
                              '~/.twittercfg')
        app.config.setdefault('YAWT_MICROPOST_TWITTER_POST_URL',
                              'http://www.twitter.com/desmondrivet/status/{0}')

    def on_cli_init(self, manager):
        """add the micropost command to the CLI manager"""
        manager.add_command('micropost', Micropost())
