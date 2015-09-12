"""Module for posting to twitter"""
from __future__ import absolute_import

import os

import tweepy
import yaml

from yawt.utils import cfg, load_file


def _get_twitter_api():
    credfile = cfg('YAWT_MICROPOST_TWITTER_CREDENTIALS_FILE')
    cfgfile = os.path.expanduser(credfile)
    cfgobj = yaml.load(load_file(cfgfile))
    consumer_key = cfgobj['consumer_key']
    consumer_secret = cfgobj['consumer_secret']
    access_token = cfgobj['access_token']
    access_token_secret = cfgobj['access_token_secret']
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)


def post_twitter(post):
    """Post a message to twitter"""
    api = _get_twitter_api()
    status = api.update_status(status=post)
    posturl = cfg('YAWT_MICROPOST_TWITTER_POST_URL')
    metadata = {}
    metadata['twitterpost'] = posturl.format(status.id)
    return metadata
