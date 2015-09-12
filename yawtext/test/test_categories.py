#pylint: skip-file
import os
import shutil
import jsonpickle
from flask.ext.testing import TestCase
from whoosh.fields import IDLIST, DATETIME

from yawt import create_app
from yawt.cli import Walk
from yawt.test import TempFolder
from yawt.utils import abs_state_folder, call_plugins, load_file
from yawtext.vc import ChangedFiles


class TestYawtCategoriesInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.categories.YawtCategories',
                       'yawtext.categories.YawtCategoryCounter']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_categories_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_CATEGORY_TEMPLATE'])
        self.assertEqual('categorycounts',
                         self.app.config['YAWT_CATEGORY_COUNT_FILE'])


class TestFolder(TempFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'templates/article_list.html': 'does not really matter',

            'content/reading/hamlet.txt': 'to be or not to be',
            'content/cooking/indian/madras.txt': 'spicy',
            'content/cooking/soup.txt': 'yummy',
        }


class TestCategoryCounts(TestCase):
    YAWT_EXTENSIONS = ['yawtext.categories.YawtCategories',
                       'yawtext.categories.YawtCategoryCounter']

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_counts_categories_with_count_file_on_walk(self):
        self.app.config['YAWT_CATEGORY_COUNT_FILE'] = '_anothercountfile'

        with self.app.app_context():
            walk = Walk()
            walk.run()

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

        with self.app.app_context():
            walk = Walk()
            walk.run()

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

        with self.app.app_context():
            walk = Walk()
            walk.run()
        self.site.save_file('content/reading/emma.txt', 'pretty funny')
        self.site.save_file('content/cooking/indian/madras.txt', 'mild')
        self.site.delete_file('content/cooking/soup.txt')

        changed = ChangedFiles(added=['content/reading/emma.txt'],
                               modified=['content/cooking/indian/madras.txt'],
                               deleted=['content/cooking/soup.txt'])
        call_plugins('on_files_changed', changed)

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/categorycounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/categorycounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(2, readingcountobj.count)
        self.assertEquals(1, cookingcountobj.count)

    def tearDown(self):
        self.site.remove()


class TestCategoryPages(TestCase):
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.collections.YawtCollections',
                       'yawtext.categories.YawtCategories',
                       'yawtext.categories.YawtCategoryCounter']
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'create_time': DATETIME(sortable=True),
                                       'categories': IDLIST()}
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

    def test_category_template_used_when_index_file_missing(self):
        response = self.client.get('/cooking/')
        self.assert_template_used('article_list.html')

    def test_category_count_variable_supplied(self):
        response = self.client.get('/cooking/')
        countobj = self.get_context_variable('categorycounts')
        self.assertEquals(3, countobj.count)
        self.assertEquals(2, len(countobj.children))

    def test_articles_variable_supplied(self):
        response = self.client.get('/cooking/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))

    def tearDown(self):
        if os.path.exists('/tmp/whoosh/index'):
            shutil.rmtree('/tmp/whoosh/index')
        self.site.remove()
