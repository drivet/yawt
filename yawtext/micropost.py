from __future__ import absolute_import

import os

import datetime
import yaml
from flask import g, current_app
from flask_script import Command, Option

from yawt.utils import call_plugins, ensure_path, load_file,\
    cfg, content_folder
from yawtext import Plugin


def write_post(metadata, content, filename):
    """Quick and easy way to save a post with metadata"""
    with open(filename, 'w') as f:
        f.write(u'---\n')
        for key in metadata:
            f.write(u'%s: %s\n' % (key, metadata[key]))
        f.write(u'---\n')
        f.write(unicode(content))


def _get_twitter_api():
    credfile = cfg('YAWT_MICROPOST_TWITTER_CREDENTIALS_FILE')
    cfgfile = os.path.expanduser(credfile)
    cfgobj = yaml.load(load_file(cfgfile))
    consumer_key = cfgobj['consumer_key']
    consumer_secret = cfgobj['consumer_secret']
    access_token = cfgobj['access_token']
    access_token_secret = cfgobj['access_token_secret']
    import tweepy
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)


def _post_twitter(post):
    api = _get_twitter_api()
    status = api.update_status(status=post)
    posturl = cfg('YAWT_MICROPOST_TWITTER_POST_URL')
    metadata = {}
    metadata['twitterpost'] = posturl % (status.id)
    return metadata


def _post_fb(post):
    from facepy import GraphAPI
    token_file = os.path.expanduser(cfg('YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE'))
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
    posturl = cfg('YAWT_MICROPOST_FB_POST_URL')
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
    metadata = {}
    for network in networks:
        if network == 'facebook':
            metadata.update(_post_fb(post))
        elif network == 'twitter':
            metadata.update(_post_twitter(post))
    return metadata


def _post(post, networks):
    metadata = post_social(post, networks)
    now = datetime.datetime.utcnow()
    metadata.update({'create_time': now.isoformat(),
                     'modified_time': now.isoformat()})

    tags = _extract_tags(post)
    if len(tags) > 0:
        metadata['tags'] = ','.join(tags)

    root_dir = g.site.root_dir
    repo_category = os.path.join(content_folder(),
                                 cfg('YAWT_MICROPOST_CATEGORY'))
    ensure_path(os.path.join(root_dir, repo_category))

    slug = "%d%d%d%d%d%d" % (now.year, now.month, now.day, now.hour, now.minute, now.second)
    repo_file = os.path.join(repo_category, slug)
    repo_file += "." + cfg('YAWT_MICROPOST_EXTENSION')
    write_post(metadata, post, os.path.join(root_dir, repo_file))


class Micropost(Command):
    """Micropost command"""
    def __init__(self):
        super(Micropost, self).__init__()

    def get_options(self):
        return [Option('post'),
                Option('--network', '-n', action='append', default=[])]

    def run(self, post, network):
        current_app.preprocess_request()
        _post(post, network)
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
        app.config.setdefault('YAWT_MICROPOST_TWITTER_CREDENTIALS_FILE',
                              '~/.twittercfg')
        app.config.setdefault('YAWT_MICROPOST_TWITTER_POST_URL',
                              'http://www.twitter.com/desmondrivet/status/%d')

    def on_cli_init(self, manager):
        """add the micropost command to the CLI manager"""
        manager.add_command('micropost', Micropost())
