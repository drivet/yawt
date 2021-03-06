#pylint: skip-file
from __future__ import absolute_import

from flask_testing import TestCase
from yawt import create_app
from yawtext.test import TestCaseWithIndex


class TestYawtSearchInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.search.YawtSearch']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_search_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_SEARCH_TEMPLATE'])


class TestSearchPages(TestCaseWithIndex):
    YAWT_EXTENSIONS = ['yawtext.search.YawtSearch'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    files = {
        'templates/article_list.html': 'does not really matter',
        'content/reading/hamlet.txt': 'hamlet',
        'content/cooking/indian/madras.txt': 'madras',
        'content/cooking/soup.txt': 'soup',
    }

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
