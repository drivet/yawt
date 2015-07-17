#pylint: skip-file

import unittest
import tempfile
from mock import Mock

import yawtext.micropost
from yawt import create_app
from flask import g
import shutil


class Config(object):
    YAWT_MICROPOST_NETWORKS = ['facebook']
    YAWT_MICROPOST_CATEGORY = 'microposts'
    YAWT_MICROPOST_EXTENSION = 'txt'


class TestMicropost(unittest.TestCase):
    def setUp(self):
        self.old_post_fb = yawtext.micropost._post_fb
        yawtext.micropost._post_fb = Mock(return_value={'fbpost': 'fb_url'})

        self.old_git_add = yawtext.micropost.git_add
        yawtext.micropost.git_add = Mock()

        self.old_git_push = yawtext.micropost.git_push
        yawtext.micropost.git_push = Mock()

        self.old_git_commit = yawtext.micropost.git_commit
        yawtext.micropost.git_commit = Mock()

        self.old_write_post = yawtext.micropost.write_post
        yawtext.micropost.write_post = Mock()

        self.old_call_plugins = yawtext.micropost.call_plugins
        yawtext.micropost.call_plugins = Mock()

        self.tempdir = tempfile.mkdtemp()
        self.app = create_app(self.tempdir, config=Config())
        self.micropostCmd = yawtext.micropost.Micropost()

    def test_micropost_calls_fb_with_post(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=True)
        yawtext.micropost._post_fb.assert_called_with("this is a post")

    def test_micropost_writes_post_with_timestamps(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=True)
        args = yawtext.micropost.write_post.call_args
        metadata = args[0][0]
        self.assertTrue('md_create_time' in metadata)
        self.assertTrue('md_modified_time'in metadata)

    def test_micropost_writes_post_with_post_text(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=True)
        args = yawtext.micropost.write_post.call_args
        post = args[0][1]
        self.assertEquals('this is a post', post)

    def test_micropost_commits_with_message(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=True)
        yawtext.micropost.git_commit.assert_called_with(self.tempdir,
                                                        'commit message')

    def test_micropost_pushes(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=True)
        yawtext.micropost.git_push.assert_called_with(self.tempdir)

    def test_micropost_does_not_push_when_told(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  message='commit message',
                                  push=False)
        yawtext.micropost.git_push.assert_not_called()

    def test_micropost_does_not_commit_when_told(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=False,
                                  message='commit message',
                                  push=False)
        yawtext.micropost.git_commit.assert_not_called()

    def test_micropost_autogenerates_commit_message(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post',
                                  commit=True,
                                  push=False)
        yawtext.micropost.git_commit.assert_called_with(self.tempdir,
                                                        "posted 'this is a post'")

    def test_micropost_extracts_tags(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post #giggles #stuff')
        args = yawtext.micropost.write_post.call_args
        metadata = args[0][0]
        self.assertEquals(metadata['tags'], 'giggles,stuff')

    def test_micropost_extracts_tags(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post #giggles #stuff')
        args = yawtext.micropost.write_post.call_args
        metadata = args[0][0]
        self.assertEquals(metadata['tags'], 'giggles,stuff')

    def test_micropost_calls_plugins(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post', push=True)
        yawtext.micropost.call_plugins.assert_called_with('on_micropost')

    def test_micropost_doesn_not_call_plugins_when_not_pushed(self):
        with self.app.test_request_context():
            self.micropostCmd.run(post='this is a post', push=False)
        yawtext.micropost.call_plugins.assert_not_called()

    def tearDown(self):
        yawtext.micropost._post_fb = self.old_post_fb
        yawtext.micropost.git_add = self.old_git_add
        yawtext.micropost.git_push = self.old_git_push
        yawtext.micropost.git_commit = self.old_git_commit
        yawtext.micropost.write_post = self.old_write_post
        yawtext.micropost.call_plugins = self.old_call_plugins
        assert self.tempdir.startswith('/tmp/')
        shutil.rmtree(self.tempdir)
