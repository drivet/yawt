#pylint: skip-file
from flask_testing import TestCase

import yawtext
from yawt import create_app
from yawt.utils import save_file, remove_file
from yawtext.facebook import post_fb
from yawtext.test import fake_facebook


access_token = """ACCESS_TOKEN
"""

class TestFacebook(TestCase):
    YAWT_EXTENSIONS = ['yawtext.micropost.YawtMicropost']
    YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE = '/tmp/fbtoken'

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def setUp(self):
        self.old_facebook = yawtext.facebook.facepy
        yawtext.facebook.facepy = fake_facebook
        fake_facebook.clear()
        save_file('/tmp/fbtoken', access_token)

    def test_post_interacts_with_facebook_api(self):
        fake_facebook.returnval = {'id': '1234_5678'}
        metadata = post_fb('this is a test message')
        self.assertEquals(1, len(fake_facebook.graphapis))
        self.assertEquals('me/feed', fake_facebook.graphapis[0].target)
        self.assertEquals('this is a test message',
                          fake_facebook.graphapis[0].message)
        self.assertEquals('http://www.facebook.com/desmond.rivet/posts/5678',
                          metadata['fbpost'])

    def tearDown(self):
        remove_file('/tmp/fbtoken')
        yawtext.facebook.facepy = self.old_facebook
