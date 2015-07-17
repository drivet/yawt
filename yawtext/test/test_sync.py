#pylint: skip-file

import unittest
import tempfile
from mock import Mock

import yawtext.sync
from yawt import create_app
from flask import g
import shutil


class TestSync(unittest.TestCase):
    def setUp(self):
        self.old_git_add_all = yawtext.sync.git_add_all
        yawtext.sync.git_add_all = Mock()

        self.old_git_status = yawtext.sync.git_status
        yawtext.sync.git_status = Mock()

        self.old_git_commit = yawtext.sync.git_commit
        yawtext.sync.git_commit = Mock()

        self.old_git_push = yawtext.sync.git_push
        yawtext.sync.git_push = Mock()

        self.old_git_latest_changes = yawtext.sync.git_latest_changes
        yawtext.sync.git_latest_changes = Mock(return_value=[['stuff.txt'],
                                                             [],
                                                             []])

        self.old_call_plugins = yawtext.sync.call_plugins
        yawtext.sync.call_plugins = Mock()

        self.tempdir = tempfile.mkdtemp()
        self.app = create_app(self.tempdir)
        self.syncCmd = yawtext.sync.Sync()

    def test_sync_calls_plugins(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             nopush=False,
                             message='commit message')
        yawtext.sync.call_plugins.assert_called_with('on_sync',
                                                     ['stuff.txt'], [], [])

    def test_sync_commits(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             nopush=False,
                             message='commit message')
        yawtext.sync.git_commit.assert_called_with(self.tempdir,
                                                   'commit message')

    def test_sync_pushes(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             nopush=False,
                             message='commit message')
        yawtext.sync.git_push.assert_called_with(self.tempdir)

    def test_sync_skips_push_when_in_nopush_mode(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             nopush=True,
                             message='commit message')
        yawtext.sync.git_push.assert_not_called()

    def test_sync_skips_adding_and_status_in_strict_mode(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             nopush=False,
                             message='commit message')
        yawtext.sync.git_add_all.assert_not_called()
        yawtext.sync.git_status.assert_not_called()

    def tearDown(self):
        yawtext.sync.git_add_all = self.old_git_add_all
        yawtext.sync.git_status = self.old_git_status
        yawtext.sync.git_commit = self.old_git_commit
        yawtext.sync.git_push = self.old_git_push
        yawtext.sync.git_latest_changes = self.old_git_latest_changes
        yawtext.sync.call_plugins = self.old_call_plugins
        assert self.tempdir.startswith('/tmp/')
        shutil.rmtree(self.tempdir)
