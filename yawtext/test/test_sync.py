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
        self.old_vc_add_tracked = yawtext.sync.vc_add_tracked
        self.old_vc_add_tracked_and_new = yawtext.sync.vc_add_tracked_and_new
        yawtext.sync.vc_add_tracked = Mock()
        yawtext.sync.vc_add_tracked_and_new = Mock()

        self.old_vc_status = yawtext.sync.vc_status
        yawtext.sync.vc_status = Mock()

        self.old_vc_commit = yawtext.sync.vc_commit
        yawtext.sync.vc_commit = Mock()

        self.old_vc_push = yawtext.sync.vc_push
        yawtext.sync.vc_push = Mock()

        self.tempdir = tempfile.mkdtemp()
        self.app = create_app(self.tempdir)
        self.syncCmd = yawtext.sync.Sync()

    def test_sync_commits(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             addnew=True,
                             push=False,
                             message='commit message')
        yawtext.sync.vc_commit.assert_called_with('commit message')

    def test_sync_pushes(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             addnew=True,
                             push=True,
                             message='commit message')
        yawtext.sync.vc_push.assert_called_with()

    def test_sync_skips_push_when_in_nopush_mode(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             addnew=True,
                             push=False,
                             message='commit message')
        yawtext.sync.vc_push.assert_not_called()

    def test_sync_skips_adding_and_status_in_strict_mode(self):
        with self.app.test_request_context():
            self.syncCmd.run(strict=True,
                             addnew=True,
                             push=False,
                             message='commit message')
        yawtext.sync.vc_add_tracked.assert_not_called()
        yawtext.sync.vc_add_tracked_and_new.assert_not_called()
        yawtext.sync.vc_status.assert_not_called()

    def tearDown(self):
        yawtext.sync.vc_add_tracked = self.old_vc_add_tracked
        yawtext.sync.vc_add_tracked_and_new = self.old_vc_add_tracked_and_new
        yawtext.sync.vc_status = self.old_vc_status
        yawtext.sync.vc_commit = self.old_vc_commit
        yawtext.sync.vc_push = self.old_vc_push
        assert self.tempdir.startswith('/tmp/')
        shutil.rmtree(self.tempdir)
