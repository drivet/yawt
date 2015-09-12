from yawtext.test import fake_tweepy
from yawtext.twitter import post_twitter
from flask.ext.testing import TestCase
from yawt.utils import save_file, remove_file
from yawt import create_app
import yawtext

twittercred = """
consumer_key: "CONSUMER_KEY"
consumer_secret: "CONSUMER_SECRET"
access_token: "ACCESS_TOKEN"
access_token_secret: "ACCESS_TOKEN_SECRET" 
"""

class TestTwitter(TestCase):
    YAWT_EXTENSIONS = ['yawtext.micropost.YawtMicropost']
    YAWT_MICROPOST_TWITTER_CREDENTIALS_FILE = '/tmp/twittercred.yml'

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def setUp(self):
        self.old_tweepy = yawtext.twitter.tweepy
        yawtext.twitter.tweepy = fake_tweepy
        fake_tweepy.clear()
        save_file('/tmp/twittercred.yml', twittercred)

    def test_post_interacts_with_twitter_api(self):
        post_twitter('this is a test message')
        self.assertEquals(1, len(fake_tweepy.oauths))
        self.assertEquals('CONSUMER_KEY', fake_tweepy.oauths[0].consumer_key)
        self.assertEquals('CONSUMER_SECRET', fake_tweepy.oauths[0].consumer_secret)
        self.assertEquals('ACCESS_TOKEN', fake_tweepy.oauths[0].access_token)
        self.assertEquals('ACCESS_TOKEN_SECRET', fake_tweepy.oauths[0].access_token_secret)
        
        self.assertEquals(1, len(fake_tweepy.apis))
        self.assertEquals('this is a test message', fake_tweepy.apis[0].status)

    def tearDown(self):
        remove_file('/tmp/twittercred.yml')
        yawtext.twitter.tweepy = self.old_tweepy
        
