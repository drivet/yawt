#pylint: skip-file
import frontmatter
from flask.ext.testing import TestCase
from mock import Mock

import yawtext.micropost
from yawt import create_app
from yawt.cli import create_manager
from yawt.test import BaseTestSite, TestCaseWithSite


class TestMicropostInitialization(TestCase):
    YAWT_EXTENSIONS = ['yawtext.micropost.YawtMicropost']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_micropost_has_default_config(self):
        self.assertEquals('microposts',
                          self.app.config['YAWT_MICROPOST_CATEGORY'])
        self.assertEquals('txt',
                          self.app.config['YAWT_MICROPOST_EXTENSION'])
        self.assertEquals(['twitter'],
                          self.app.config['YAWT_MICROPOST_NETWORKS'])

    def test_sync_is_added_to_commands(self):
        self.app.preprocess_request()
        manager = create_manager(self.app)
        self.assertTrue('micropost' in manager._commands)


class TestMicropost(TestCaseWithSite):
    YAWT_EXTENSIONS = ['yawtext.micropost.YawtMicropost']
    YAWT_MICROPOST_NETWORKS = ['facebook', 'twitter']
    YAWT_MICROPOST_CATEGORY = 'microposts'
    YAWT_MICROPOST_EXTENSION = 'txt'

    folders = ['content']

    def setUp(self):
        self.old_post_fb = yawtext.micropost.post_fb
        yawtext.micropost.post_fb = Mock(return_value={'fbpost': 'fb_url'})

        self.old_post_twitter = yawtext.micropost.post_twitter
        yawtext.micropost.post_twitter = Mock(return_value={'twitterpost': 'tp'})

        self.micropostCmd = yawtext.micropost.Micropost()

    def test_micropost_calls_fb_with_post(self):
        self.micropostCmd.run(post='this is a post', network=None)
        yawtext.micropost.post_fb.assert_called_with("this is a post")

    def test_micropost_calls_twitter_with_post(self):
        self.micropostCmd.run(post='this is a post', network=None)
        yawtext.micropost.post_twitter.assert_called_with("this is a post")

    def test_micropost_writes_post_with_timestamps(self):
        filename = self.micropostCmd.run(post='this is a post', network=None)
        post = frontmatter.loads(self.site.load_file(filename))
        self.assertTrue('create_time' in post.metadata)
        self.assertTrue('modified_time'in post.metadata)

    def test_micropost_writes_post_with_post_text(self):
        filename = self.micropostCmd.run(post='this is a post', network=None)
        post = frontmatter.loads(self.site.load_file(filename))
        self.assertEquals('this is a post', post.content)

    def test_micropost_extracts_tags(self):
        filename = self.micropostCmd.run(post='this is a post #giggles #stuff', network=None)
        post = frontmatter.loads(self.site.load_file(filename))
        self.assertEquals('giggles,stuff', post.metadata['tags'])

    def tearDown(self):
        super(TestMicropost, self).tearDown()
        yawtext.micropost.post_fb = self.old_post_fb
        yawtext.micropost.post_twitter = self.old_post_twitter
