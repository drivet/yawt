#pylint: skip-file
import os
import shutil
import unittest

from flask.ext.testing import TestCase
from mock import Mock

import yawt.site_manager
from yawt import create_app
from yawt.cli import NewSite, Walk, create_manager
from yawt.test import TempFolder


# for mocking purposes

path_to_site = "/tmp/testsite"


class TestCreateManager(unittest.TestCase):
    """Flask script manager tests"""
    def setUp(self):
        self.old_call_plugins = yawt.cli.call_plugins
        yawt.cli.call_plugins = Mock()

    def test_create_manager_adds_standard_commands(self):
        manager = create_manager()
        self.assertTrue('runserver' in manager._commands)
        self.assertTrue('newsite' in manager._commands)
        self.assertTrue('walk' in manager._commands)

    def test_create_manager_calls_plugins(self):
        manager = create_manager()
        yawt.cli.call_plugins.assert_called_with('on_cli_init', manager)

    def tearDown(self):
        yawt.cli.call_plugins = self.old_call_plugins


class TestNewSiteCommand(TestCase):
    """NewSite command tests"""

    def create_app(self):
        return create_app(root_dir=path_to_site)

    def setUp(self):
        self.app.preprocess_request()

    def test_creates_site_directory(self):
        self.assertFalse(os.path.exists(path_to_site))
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(path_to_site))

    def test_creates_content_directory(self):
        path_to_content = os.path.join(path_to_site, 'content')
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(path_to_content))

    def test_creates_draft_directory(self):
        path_to_drafts = os.path.join(path_to_site, 'drafts')
        self.assertFalse(os.path.exists(path_to_drafts))
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(path_to_drafts))

    def test_creates_template_directory(self):
        path_to_templates = os.path.join(path_to_site, 'templates')
        self.assertFalse(os.path.exists(path_to_templates))
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(path_to_templates))

    def test_creates_404_template(self):
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site,
                                                    'templates/404.html')))

    def test_creates_article_template(self):
        newsite = NewSite()
        newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site,
                                                    'templates/article.html')))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestSite(TempFolder):
    def __init__(self):
        super(TestSite, self).__init__()
        self.files = {
            'content/entry1.txt': 'entry text',
            'content/entry2.txt': 'entry text',
        }


class YawtWalkCommand(TestCase):
    """
    YAWT system level tests
    """

    # config
    DEBUG = True
    TESTING = True

    def create_app(self):
        self.site = TestSite()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.old_call_plugins = yawt.site_manager.call_plugins
        yawt.site_manager.call_plugins = Mock()

    def test_walk_visits_files(self):
        walkcmd = Walk()
        walkcmd.run()

        calls = yawt.site_manager.call_plugins.call_args_list
        self.assertEquals(4, len(calls))
        call_0_pargs = calls[0][0]
        self.assertEquals('on_pre_walk', call_0_pargs[0])

#        call_1_pargs = calls[1][0]
#        self.assertArticleVisited(call_1_pargs, 'entry2', 'txt')

#        call_2_pargs = calls[2][0]
#        self.assertArticleVisited(call_2_pargs, 'entry1', 'txt')

        call_3_pargs = calls[3][0]
        self.assertEquals('on_post_walk', call_3_pargs[0])

    def assertArticleVisited(self, call_pargs, fullname, ext):
        self.assertEquals('on_visit_article', call_pargs[0])
        article = call_pargs[1]
        self.assertEquals(fullname, article.info.fullname)
        self.assertEquals(ext, article.info.extension)

    def tearDown(self):
        self.site.remove()
        yawt.site_manager.call_plugins = self.old_call_plugins
