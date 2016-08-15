#pylint: skip-file
from flask_testing import TestCase
from mock import Mock

import yawt.utils
import yawtext
from yawt.cli import create_manager
from yawtext.sync import Sync
from yawtext.test import TempGitFolder


class TestFolder(TempGitFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'content/index.txt': 'index text',
        }


class TestSync(TestCase):
    YAWT_EXTENSIONS = ['yawtext.vc.YawtVersionControl',
                       'yawtext.sync.YawtSync']

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.site.initialize_git()
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

        self.old_call_plugins = yawtext.sync.call_plugins
        yawtext.sync.call_plugins = Mock()

    def test_sync_is_added_to_commands(self):
        self.app.preprocess_request()
        manager = create_manager(self.app)
        self.assertTrue('sync' in manager._commands)

    def test_sync_commits_in_strict_mode(self):
        syncCmd = Sync()
        syncCmd.run(strict=True,
                    addnew=False,
                    push=False,
                    message='commit message')
        yawtext.sync.vc_commit.assert_called_with('commit message')

    def test_sync_supplies_commit_message(self):
        syncCmd = Sync()
        syncCmd.run(strict=True,
                    addnew=False,
                    push=False,
                    message=None)
        yawtext.sync.vc_commit.assert_called_with('synced changes')

    def test_sync_pushes_if_asked(self):
        syncCmd = Sync()
        syncCmd.run(strict=True,
                    addnew=False,
                    push=True,
                    message='commit message')
        yawtext.sync.vc_push.assert_called_with()

    def test_sync_skips_push_when_in_nopush_mode(self):
        syncCmd = Sync()
        syncCmd.run(strict=True,
                    addnew=False,
                    push=False,
                    message='commit message')
        yawtext.sync.vc_push.assert_not_called()

    def test_sync_skips_adding_and_status_in_strict_mode(self):
        syncCmd = Sync()
        syncCmd.run(strict=True,
                    addnew=False,
                    push=False,
                    message='commit message')
        yawtext.sync.vc_add_tracked.assert_not_called()
        yawtext.sync.vc_add_tracked_and_new.assert_not_called()
        yawtext.sync.vc_status.assert_not_called()

    def test_sync_adds_new_when_asked(self):
        syncCmd = Sync()
        syncCmd.run(strict=False,
                    addnew=True,
                    push=False,
                    message='commit message')
        yawtext.sync.vc_add_tracked_and_new.assert_called_with()
        yawtext.sync.vc_add_tracked.assert_not_called()

    def test_sync_adds_only_tracked_when_asked(self):
        syncCmd = Sync()
        syncCmd.run(strict=False,
                    addnew=False,
                    push=False,
                    message='commit message')
        yawtext.sync.vc_add_tracked_and_new.assert_not_called()
        yawtext.sync.vc_add_tracked.assert_called_with()

    def test_call_plugins_called_with_status_results(self):
        changed = yawt.utils.ChangedFiles(modified=['content/index.txt'])
        yawtext.sync.vc_status.return_value = changed
        syncCmd = Sync()
        syncCmd.run(strict=False,
                    addnew=False,
                    push=False,
                    message='commit message')
        yawtext.sync.call_plugins.assert_called_with('on_pre_sync',
                                                     changed)

    def tearDown(self):
        yawtext.sync.vc_add_tracked = self.old_vc_add_tracked
        yawtext.sync.vc_add_tracked_and_new = self.old_vc_add_tracked_and_new
        yawtext.sync.vc_status = self.old_vc_status
        yawtext.sync.vc_commit = self.old_vc_commit
        yawtext.sync.vc_push = self.old_vc_push
        yawtext.sync.call_plugins = self.old_call_plugins
        self.site.remove()
