#pylint: skip-file

import os
import shutil
import subprocess

from flask import g
from flask.ext.testing import TestCase

import yawt
from yawt import create_app
from yawtext.test import TempGitFolder
from yawt.utils import save_file, remove_file, load_file
from yawtext import Plugin
from yawtext.git import _git_cmd
from yawtext.vc import vc_status, vc_add_tracked, vc_add_tracked_and_new,\
    vc_commit, post_commit, ChangedFiles


class TestYawtGitNewSite(TestCase):
    YAWT_EXTENSIONS = ['yawtext.vc.YawtVersionControl']
    YAWT_VERSION_CONTROL_IFC = 'yawtext.git'

    def create_app(self):
        self.root_dir = '/tmp/blah'
        return create_app(self.root_dir, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_git_saves_ignore_file(self):
        self.assertFalse(os.path.isfile(os.path.join(self.root_dir,
                                                     '.gitignore')))
        g.site.initialize()
        self.assertTrue(os.path.isfile(os.path.join(self.root_dir,
                                                    '.gitignore')))

    def tearDown(self):
        shutil.rmtree(self.root_dir)


class TestFolder(TempGitFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'content/index.txt': 'index text',
            'content/entry.txt': 'entry text',
            'content/random.txt': 'random text',
            'content/food.txt': 'random food text, let us make this longer',
        }


class TestGitPlugin(TestCase):
    YAWT_EXTENSIONS = ['yawtext.vc.YawtVersionControl']
    YAWT_VERSION_CONTROL_IFC = 'yawtext.git'

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()
        self.site.initialize_git()

    def test_status_gives_changed_files(self):
        # modify one file
        self.site.save_file('content/index.txt', 'different stuff')

        # add another new file
        self.site.save_file('content/newfile.txt', 'blah')

        # remove yet another
        self.site.delete_file('content/random.txt')

        # move a file
        filename1 = 'content/food.txt'
        filename2 = 'content/newfood.txt'
        self.site.save_file(filename2, self.site.load_file(filename1))
        self.site.delete_file(filename1)

        # add all changes to index
        cmd = _git_cmd(['add', '-A'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

        changed = vc_status()
        expected = ChangedFiles(added=['content/newfile.txt'],
                                modified=['content/index.txt'],
                                deleted=['content/random.txt'],
                                renamed={'content/food.txt':
                                         'content/newfood.txt'})
        self.assertEquals(expected, changed)

    def test_add_tracked(self):
        # modify one file
        self.site.save_file('content/index.txt', 'different stuff')

        # add another new file
        self.site.save_file('content/newfile.txt', 'blah')

        vc_add_tracked()
        changed = vc_status()
        expected = ChangedFiles(modified=['content/index.txt'])
        self.assertEquals(expected, changed)

    def test_add_tracked_and_new(self):
        # modify one file
        self.site.save_file('content/index.txt', 'different stuff')

        # add another new file
        self.site.save_file('content/newfile.txt', 'blah')

        vc_add_tracked_and_new()
        changed = vc_status()
        expected = ChangedFiles(added=['content/newfile.txt'],
                                modified=['content/index.txt'])
        self.assertEquals(expected, changed)

    def test_commit(self):
        # modify one file
        self.site.save_file('content/index.txt', 'different stuff')

        vc_add_tracked()
        vc_commit('hello')
        changed = vc_status()
        expected = ChangedFiles()
        self.assertEquals(expected, changed)

    def tearDown(self):
        self.site.remove()


class TestPlugin(Plugin):
    def __init__(self):
        self.changed = None

    def on_files_changed(self, changed):
        self.changed = changed


class TestGitHooks(TestCase):
    YAWT_EXTENSIONS = ['yawtext.vc.YawtVersionControl',
                       'yawtext.test.test_git.TestPlugin']
    YAWT_VERSION_CONTROL_IFC = 'yawtext.git'

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()
        self.site.initialize_git()

    def test_post_commit(self):
        # modify one file
        self.site.save_file('content/index.txt', 'different stuff')

        # add another new file
        self.site.save_file('content/newfile.txt', 'blah')

        # remove yet another
        self.site.delete_file('content/random.txt')

        # move a file
        filename1 = 'content/food.txt'
        filename2 = 'content/newfood.txt'
        self.site.save_file(filename2, self.site.load_file(filename1))
        self.site.delete_file(filename1)

        # add all changes to index
        vc_add_tracked_and_new()
        vc_commit('hello')
        post_commit(self.site.site_root, self.app)
        expected = ChangedFiles(added=['content/newfile.txt'],
                                modified=['content/index.txt'],
                                deleted=['content/random.txt'],
                                renamed={'content/food.txt':
                                         'content/newfood.txt'})

        test_plugin_name = 'yawtext.test.test_git.TestPlugin'
        plugin = self.app.extension_info[0][test_plugin_name]
        self.assertEquals(expected, plugin.changed)

    def tearDown(self):
        self.site.remove()
