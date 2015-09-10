#pylint: skip-file

import os
import jsonpickle

from flask.ext.testing import TestCase
from whoosh.fields import IDLIST, DATETIME, KEYWORD

from yawt import create_app
from yawt.cli import Walk
from yawt.test import TempFolder
from yawt.utils import cfg, abs_state_folder, call_plugins, load_file
from yawtext import StateFiles
from yawtext.vc import ChangedFiles


class TestYawtTaggingInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagging']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_tagging_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_TAGGING_TEMPLATE'])
        self.assertEqual('tagcounts',
                         self.app.config['YAWT_TAGGING_COUNT_FILE'])

HAMLET = """---
tags: shakespeare,literature
---

to be or not to be
"""

MADRAS = """---
tags: curry,cumin
---

spicy
"""

SOUP = """---
tags: liquid,cumin
---

yummy
"""

EMMA = """---
tags: austen,literature
---

funny
"""

NEW_MADRAS = """---
tags: tumeric
---

not good
"""


class TestFolder(TempFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'templates/article_list.html': 'does not really matter',

            'content/reading/hamlet.txt': HAMLET,
            'content/cooking/indian/madras.txt': MADRAS,
            'content/cooking/soup.txt': SOUP,
        }


class TestTaggingCounts(TestCase):
    YAWT_META_TYPES = {'tags': 'list'}
    # Tagging plugin MUST comes before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagging',
                       'flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.collections.YawtCollections']
    WHOOSH_INDEX_ROOT = '/home/dcr/blogging/website/_state/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'create_time': DATETIME(sortable=True),
                                       'tags': KEYWORD()}
    YAWT_COLLECTIONS_SORT_FIELD = 'create_time'

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_counts_tagging_with_count_file_on_walk(self):
        self.app.config['YAWT_TAGGING_COUNT_FILE'] = '_anothercountfile'

        with self.app.app_context():
            walk = Walk()
            walk.run()

        counts_path = os.path.join(abs_state_folder(), '_anothercountfile')
        countobj = jsonpickle.decode(load_file(counts_path))
        self.assertEquals(5, len(countobj.keys()))

    def test_counts_tagging_with_bases_on_walk(self):
        self.app.config['YAWT_TAGGING_BASE'] = ['reading', 'cooking']

        with self.app.app_context():
            walk = Walk()
            walk.run()

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/tagcounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/tagcounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(2, len(readingcountobj.keys()))
        self.assertEquals(3, len(cookingcountobj.keys()))

    def test_adjusts_tagging_with_bases_on_update(self):
        self.app.config['YAWT_TAGGING_BASE'] = ['reading', 'cooking']

        with self.app.app_context():
            walk = Walk()
            walk.run()

        self.site.save_file('content/reading/emma.txt', EMMA)
        self.site.save_file('content/cooking/indian/madras.txt', NEW_MADRAS)
        self.site.delete_file('content/cooking/soup.txt')

        changed = ChangedFiles(added=['content/reading/emma.txt'],
                               modified=['content/cooking/indian/madras.txt'],
                               deleted=['content/cooking/soup.txt'])
        call_plugins('on_files_changed', changed)

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/tagcounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/tagcounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(3, len(readingcountobj.keys()))
        self.assertEquals(1, len(cookingcountobj.keys()))

    def tearDown(self):
        self.site.remove()


class TestTaggingPages(TestCase):
    YAWT_META_TYPES = {'tags': 'list'}
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagging',
                       'flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.collections.YawtCollections']
    WHOOSH_INDEX_ROOT = '/home/dcr/blogging/website/_state/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'create_time': DATETIME(sortable=True),
                                       'tags': KEYWORD()}
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

    def test_template_template_used_when_using_tag_url(self):
        response = self.client.get('/tags/shakespeare/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/tags/shakespeare/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/tags/shakespeare/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/tags/shakespeare/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/tags/shakespeare/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('reading/tags/shakespeare/index.html')
        self.assert_template_used('article_list.html')

    def test_tagging_count_variable_supplied(self):
        response = self.client.get('/tags/shakespeare/')
        countobj = self.get_context_variable('tagcounts')
        self.assertEquals(5, len(countobj.keys()))

    def test_articles_variable_supplied(self):
        response = self.client.get('/tags/shakespeare/')
        articles = self.get_context_variable('articles')
        self.assertEquals(1, len(articles))

        response = self.client.get('/tags/cumin/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))

    def tearDown(self):
        self.site.remove()
