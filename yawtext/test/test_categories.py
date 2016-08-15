#pylint: skip-file
import os

import jsonpickle
from flask_testing import TestCase

from yawt import create_app, utils
from yawt.utils import abs_state_folder, call_plugins, load_file, ChangedFiles
from yawtext.test import TestCaseWithIndex, TestCaseWithWalker
import yawtext


class TestYawtCategoriesInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.categories.YawtCategories',
                       'yawtext.categories.YawtCategoryCounter']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    # TODO more default config checking
    def test_categories_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_CATEGORY_TEMPLATE'])
        self.assertEqual('categorycounts',
                         self.app.config['YAWT_CATEGORY_COUNT_FILE'])


FILES = {
    'templates/article_list.html': 'does not matter',
    'templates/article.html': 'does not matter',

    'content/reading/hamlet.txt': 'to be or not to be',
    'content/cooking/indian/madras.txt': 'spicy',
    'content/cooking/soup.txt': 'yummy',
}


class TestCategoryCounts(TestCaseWithWalker):
    YAWT_EXTENSIONS = ['yawtext.categories.YawtCategoryCounter']
    files = FILES
    walkOnSetup = False

    def test_counts_categories_with_count_file_on_walk(self):
        self.app.config['YAWT_CATEGORY_COUNT_FILE'] = '_anothercountfile'
        self._walk()

        counts_path = os.path.join(abs_state_folder(), '_anothercountfile')
        countobj = jsonpickle.decode(load_file(counts_path))

        self.assertEquals(3, countobj.count)
        self.assertEquals(2, len(countobj.children))
        self.assertEquals(1, countobj.child('reading').count)
        self.assertEquals(2, countobj.child('cooking').count)
        self.assertEquals(1, len(countobj.child('cooking').children))
        self.assertEquals(1, countobj.child('cooking').child('indian').count)

    def test_counts_categories_with_bases_on_walk(self):
        self.app.config['YAWT_CATEGORY_BASE'] = ['reading', 'cooking']
        self._walk()

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/categorycounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/categorycounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(1, readingcountobj.count)
        self.assertEquals(2, cookingcountobj.count)

    def test_adjusts_categories_with_bases_on_update(self):
        self.app.config['YAWT_CATEGORY_BASE'] = ['reading', 'cooking']
        self._walk()

        self.site.change(added={'content/reading/emma.txt':
                                'pretty funny'},
                         modified={'content/cooking/indian/madras.txt':
                                   'mild'},
                         deleted=['content/cooking/soup.txt'])

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/categorycounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/categorycounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(2, readingcountobj.count)
        self.assertEquals(1, cookingcountobj.count)

    def test_category_count_variable_supplied(self):
        self._walk()

        response = self.client.get('/cooking/soup')
        countobj = self.get_context_variable('categorycounts')
        self.assertEquals(3, countobj.count)
        self.assertEquals(2, len(countobj.children))


class TestCategoryPages(TestCaseWithIndex):
    YAWT_EXTENSIONS = ['yawtext.categories.YawtCategories'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    files = FILES

    def test_category_template_used_when_index_file_missing(self):
        response = self.client.get('/cooking/')
        self.assert_template_used('article_list.html')

    def test_articles_variable_supplied(self):
        response = self.client.get('/cooking/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))
