#pylint: skip-file

import unittest
import yawt
from yawt.site_manager import YawtSiteManager,\
    SiteExistsError, ArticleNotFoundError
from yawt.article import ArticleInfo
import os.path
import shutil
from mock import Mock
from flask.ext.testing import TestCase
from yawt.test.siteutils import TempSite
from yawt.test import BaseTestSite
from yawt import create_app
from yawtext import Plugin
from yawt.test import TestCaseWithSite


class TestYawtSiteManagerInitialization(TestCase):
    def create_app(self):
        self.root_dir = '/tmp/temp_site'
        return create_app(self.root_dir)

    def setUp(self):
        self.old_call_plugins_args = yawt.site_manager.call_plugins_arg
        self.old_call_plugins = yawt.site_manager.call_plugins
        yawt.site_manager.call_plugins_arg = Mock()
        yawt.site_manager.call_plugins = Mock()

    def test_initialize_fails_if_root_folder_exists(self):
        store = YawtSiteManager(root_dir=self.root_dir)
        os.mkdir(self.root_dir)
        self.assertRaises(SiteExistsError, store.initialize)

    def test_initialize_sets_up_site_with_defaults(self):
        store = YawtSiteManager(root_dir=self.root_dir)
        store.initialize()
        assert os.path.exists(self.root_dir)
        assert os.path.exists(os.path.join(self.root_dir,
                                           store.template_folder))
        assert os.path.exists(os.path.join(self.root_dir,
                                           store.content_folder))
        assert os.path.exists(os.path.join(self.root_dir,
                                           'config.py'))
        assert os.path.exists(os.path.join(self.root_dir,
                                           store.template_folder,
                                           'article.html'))
        assert os.path.exists(os.path.join(self.root_dir,
                                           store.template_folder,
                                           '404.html'))

    def test_initialize_sets_up_site_with_non_defaults(self):
        store = YawtSiteManager(root_dir=self.root_dir,
                                template_folder='another_templates',
                                content_folder='another_content',
                                draft_folder='another_drafts')

        store.initialize()

        assert os.path.exists(os.path.join(self.root_dir, 'another_templates'))
        assert not os.path.exists(os.path.join(self.root_dir, 'templates'))

        assert os.path.exists(os.path.join(self.root_dir, 'another_content'))
        assert not os.path.exists(os.path.join(self.root_dir, 'content'))

        assert os.path.exists(os.path.join(self.root_dir, 'another_drafts'))
        assert not os.path.exists(os.path.join(self.root_dir, 'drafts'))

    def test_initialize_calls_plugins(self):
        store = YawtSiteManager(root_dir=self.root_dir)
        store.initialize()
        mock_plugins = yawt.site_manager.call_plugins_arg
        mock_plugins.assert_called_with('on_new_site',
                                        ['config.py',
                                         'article.html',
                                         '404.html'])

    def tearDown(self):
        assert self.root_dir.startswith('/tmp/')
        if os.path.exists(self.root_dir):
            shutil.rmtree(self.root_dir)
        yawt.site_manager.call_plugins_arg = self.old_call_plugins_args
        yawt.site_manager.call_plugins = self.old_call_plugins


class TestPlugin(Plugin):
    def __init__(self):
        self.pre_walk = False
        self.post_walk = False
        self.article = None
        self.visited = []

    def on_article_fetch(self, article):
        self.article = article
        return article

    def on_pre_walk(self):
        self.pre_walk = True

    def on_post_walk(self):
        self.post_walk = True

    def on_visit_article(self, article):
        self.visited.append(article)


class TestYawtSiteManager(TestCaseWithSite):
    # config
    DEBUG = True
    TESTING = True
    YAWT_EXTENSIONS = ['yawt.test.test_site_manager.TestPlugin']

    files = {
        # entries
        'content/index.txt': 'index text',
        'content/entry.txt': 'entry text',
        'content/cooking/index.txt': 'cooking index text',
        'content/cooking/madras.txt': 'madras text',
        'content/specific.txt': 'specific text',
        'content/reading/hyperion.txt': 'hyperion text',
        'content/reading/dummy.blah': 'funny guy',
        # drafts
        'drafts/weird.txt': 'kubla khan'
    }

    def setUp(self):
        self.store = YawtSiteManager(root_dir=self.site.site_root,
                                     file_extensions=['txt'])

    def test_fetch_article_by_repofile(self):
        repofile = 'content/cooking/madras.txt'
        article = self.store.fetch_article_by_repofile(repofile)
        self.assertEquals('cooking/madras', article.info.fullname)

    def test_raises_error_when_fetching_non_existent_repofile(self):
        self.assertRaises(ArticleNotFoundError,
                          self.store.fetch_article_by_repofile,
                          'content/cooking/vindaloo.txt')

    def test_fetch_articles_by_repofiles(self):
        repofiles = ['content/entry.txt', 'content/cooking/madras.txt']
        article_list = self.store.fetch_articles_by_repofiles(repofiles)
        self.assertEquals('entry', article_list[0].info.fullname)
        self.assertEquals('cooking/madras', article_list[1].info.fullname)

    def test_fetch_article_by_info(self):
        info = ArticleInfo()
        info.fullname = 'cooking/madras'
        article = self.store.fetch_article_by_info(info)
        self.assertEquals(info.fullname, article.info.fullname)

    def test_raises_error_when_fetching_non_existent_info(self):
        info = ArticleInfo()
        info.fullname = 'cooking/vindaloo'
        self.assertRaises(ArticleNotFoundError,
                          self.store.fetch_article_by_info,
                          info)

    def test_fetch_article_by_fullname(self):
        article = self.store.fetch_article('cooking/madras')
        self.assertEquals(article.info.fullname, 'cooking/madras')

    def test_raises_error_when_fetching_non_existent_fullname(self):
        self.assertRaises(ArticleNotFoundError,
                          self.store.fetch_article,
                          'cooking/vindaloo')

    def test_category_exists(self):
        self.assertTrue(self.store.category_exists('cooking'))
        self.assertFalse(self.store.category_exists('politics'))

    def test_article_exists(self):
        self.assertTrue(self.store.exists('cooking/madras'))
        self.assertFalse(self.store.exists('cooking/vindaloo'))

    def test_is_article(self):
        self.assertTrue(self.store.is_article('content/cooking/madras.txt'))
        self.assertFalse(self.store.is_article('drafts/weird.txt'))

    def test_visits_article(self):
        self.store.walk()
        test_plugin_name = 'yawt.test.test_site_manager.TestPlugin'
        plugin = self.app.extension_info[0][test_plugin_name]
        self.assertTrue(plugin.pre_walk)
        self.assertTrue(plugin.post_walk)
        visited_fullnames = [a.info.fullname for a in plugin.visited]
        self.assertEquals(4, len(visited_fullnames))
        self.assertTrue('entry' in visited_fullnames)
        self.assertTrue('cooking/madras' in visited_fullnames)
        self.assertTrue('specific' in visited_fullnames)
        self.assertTrue('reading/hyperion' in visited_fullnames)
