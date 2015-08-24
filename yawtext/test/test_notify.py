#pylint: skip-file

import unittest
import tempfile
from mock import Mock

import yawtext.notify
from yawt import create_app
from flask import g
import shutil


class Config(object):
    YAWT_NOTIFY_CATEGORIES = ['cat1']
    YAWT_NOTIFY_BASE_URL = 'http://www.example.com'


class TestNotify(unittest.TestCase):
    def setUp(self):
        self.old_post_social = yawtext.micropost.post_social
        yawtext.notify.post_social = Mock()

    def test_notify_posts_message_on_networks(self):
        self.tempdir = tempfile.mkdtemp()
        self.app = create_app(self.tempdir)
        self.notify = yawtext.notify.YawtNotify(self.app)
        with self.app.test_request_context():
            self.notify.on_files_changed(['content/cat1/a.txt', 'content/cat2/b.txt'],
                                         ['content/cat3/c.txt','content/cat4/d.txt'],
                                         ['content/cat5/e.txt', 'content/cat6/f.txt'],
                                         {})
        args_list = yawtext.notify.post_social.call_args_list
        call = args_list[0]
        msg = call[0][0]
        self.assertTrue('cat1/a' in msg)

        call = args_list[1]
        msg = call[0][0]
        self.assertTrue('cat2/b' in msg)

    def test_notify_sends_notifications_for_specified_categories(self):
        self.tempdir = tempfile.mkdtemp()
        self.app = create_app(self.tempdir, config=Config())
        self.notify = yawtext.notify.YawtNotify(self.app)
        with self.app.test_request_context():
            self.notify.on_files_changed(['content/cat1/a.txt', 'content/cat2/b.txt'],
                                         ['content/cat3/c.txt', 'content/cat4/d.txt'],
                                         ['content/cat5/e.txt', 'content/cat6/f.txt'], 
                                         {})
        args_list = yawtext.notify.post_social.call_args_list
        self.assertEquals(1, len(args_list))
        call = args_list[0]
        msg = call[0][0]
        self.assertTrue('cat1/a' in msg)

    def tearDown(self):
        yawtext.micropost.post_social = self.old_post_social
        assert self.tempdir.startswith('/tmp/')
        shutil.rmtree(self.tempdir)
