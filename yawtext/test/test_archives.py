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


class TestYawtArchivesInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives',
                       'yawtext.archives.YawtArchiveCounter']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_archives_has_default_config(self):
        self.assertEqual('article_list',
                         self.app.config['YAWT_ARCHIVE_TEMPLATE'])
        self.assertEqual('archivecounts',
                         self.app.config['YAWT_ARCHIVE_COUNT_FILE'])

HAMLET = """---
create_time: 2007-06-02 10:10:10
---

to be or not to be
"""

MADRAS = """---
create_time: 2007-06-01 10:10:10
---

spicy
"""

SOUP = """---
create_time: 2008-06-03 10:10:10
---

yummy
"""

EMMA = """---
create_time: 2010-06-01 10:10:10
---

funny
"""

NEW_MADRAS = """---
create_time: 2008-06-01 10:10:10
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


class TestArchiveCounts(TestCase):
    YAWT_META_TYPES = {'create_time': 'iso8601',
                       'modified_time': 'iso8601'}
    # Archive plugin MUST come before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives',
                       'yawtext.archives.YawtArchiveCounter',
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

    def test_counts_archives_with_count_file_on_walk(self):
        self.app.config['YAWT_ARCHIVE_COUNT_FILE'] = '_anothercountfile'

        with self.app.app_context():
            walk = Walk()
            walk.run()

        counts_path = os.path.join(abs_state_folder(), '_anothercountfile')
        countobj = jsonpickle.decode(load_file(counts_path))
        self.assertEquals(3, countobj.count)
        self.assertEquals(2, len(countobj.children))
        self.assertEquals(1, countobj.child('2008').count)
        self.assertEquals(2, countobj.child('2007').count)
        self.assertEquals(1, len(countobj.child('2007').children))
        self.assertEquals(2, countobj.child('2007').child('06').count)
        self.assertEquals(1, countobj.child('2007').child('06').child('01').count)
        self.assertEquals(1, countobj.child('2007').child('06').child('02').count)
        self.assertEquals(1, countobj.child('2008').child('06').child('03').count)

    def test_counts_archives_with_bases_on_walk(self):
        self.app.config['YAWT_ARCHIVE_BASE'] = ['reading', 'cooking']

        with self.app.app_context():
            walk = Walk()
            walk.run()

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/archivecounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/archivecounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(1, readingcountobj.count)
        self.assertEquals(2, cookingcountobj.count)

    def test_adjusts_archives_with_bases_on_update(self):
        self.app.config['YAWT_ARCHIVE_BASE'] = ['reading', 'cooking']

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
                                          'reading/archivecounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/archivecounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(2, readingcountobj.count)
        self.assertEquals(1, cookingcountobj.count)

    def tearDown(self):
        self.site.remove()


class TestArchivePages(TestCase):
    YAWT_META_TYPES = {'create_time': 'iso8601',
                       'modified_time': 'iso8601'}
    # Archive plugin MUST come before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives',
                       'yawtext.archives.YawtArchiveCounter',
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

    def test_archive_template_used_when_using_archive_url(self):
        response = self.client.get('/2007/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/index.html')
        self.assert_template_used('article_list.html')

        # permalinks
        response = self.client.get('/reading/2007/06/01/hamlet')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/hamlet.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/hamlet.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/hamlet')
        self.assert_template_used('article_list.html')

    def test_archive_count_variable_supplied(self):
        # really this should work with any URL
        response = self.client.get('/2007/')

        countobj = self.get_context_variable('archivecounts')
        self.assertEquals(3, countobj.count)

    def test_articles_variable_supplied(self):
        response = self.client.get('/2007/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))

        response = self.client.get('/2008/')
        articles = self.get_context_variable('articles')
        self.assertEquals(1, len(articles))

    def tearDown(self):
        self.site.remove()
