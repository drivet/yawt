from __future__ import absolute_import

from flask.ext.testing import TestCase
from whoosh.fields import DATETIME

from yawt import create_app
from yawt.cli import Walk
from yawt.test import TempFolder


class TestYawtSearchInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.search.YawtSearch']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_search_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_SEARCH_TEMPLATE'])


class TestFolder(TempFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'templates/article_list.html': 'does not really matter',

            'content/reading/hamlet.txt': 'hamlet',
            'content/cooking/indian/madras.txt': 'madras',
            'content/cooking/soup.txt': 'soup',
        }


class TestSearchPages(TestCase):
    YAWT_EXTENSIONS = ['yawtext.search.YawtSearch',
                       'flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.collections.YawtCollections']
    WHOOSH_INDEX_ROOT = '/home/dcr/blogging/website/_state/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'create_time': DATETIME(sortable=True)}
    YAWT_COLLECTIONS_SORT_FIELD = 'create_time'

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()
        with self.app.app_context():
            walk = Walk()
            walk.run()

    def test_search_template_used_when_using_search_url(self):
        response = self.client.get('/search/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/search/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/search/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/search/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading//search/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading//search/index.html')
        self.assert_template_used('article_list.html')

    def test_articles_variable_supplied(self):
        response = self.client.get('/search/?searchtext=madras')
        articles = self.get_context_variable('articles')
        self.assertEquals(1, len(articles))
 
        response = self.client.get('/search/?searchtext=stuff')
        articles = self.get_context_variable('articles')
        self.assertEquals(0, len(articles))

    def tearDown(self):
        self.site.remove()
