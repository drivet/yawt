#pylint: skip-file
import os

import jsonpickle
from flask_testing import TestCase

from yawt import create_app
from yawt.utils import abs_state_folder, load_file
from yawtext.test import TestCaseWithIndex, TestCaseWithSite


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


class TestArchiveCounts(TestCaseWithIndex):
    # Archive plugin MUST come before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchiveCounter'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    walkOnSetup = False
    files = {
        'templates/article.html': 'does not really matter',
        'content/reading/hamlet.txt': HAMLET,
        'content/cooking/indian/madras.txt': MADRAS,
        'content/cooking/soup.txt': SOUP,
    }

    def test_counts_archives_with_count_file_on_walk(self):
        self.app.config['YAWT_ARCHIVE_COUNT_FILE'] = '_anothercountfile'
        self._walk()

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
        self._walk()

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
        self._walk()
        self.site.change(added={'content/reading/emma.txt':
                                EMMA},
                         modified={'content/cooking/indian/madras.txt':
                                   NEW_MADRAS},
                         deleted=['content/cooking/soup.txt'])

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/archivecounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/archivecounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(2, readingcountobj.count)
        self.assertEquals(1, cookingcountobj.count)

    def test_archive_count_variable_supplied(self):
        self._walk()
        # really this should work with any URL
        response = self.client.get('/reading/hamlet')

        countobj = self.get_context_variable('archivecounts')
        self.assertEquals(3, countobj.count)


class TestArchivePages(TestCaseWithIndex):
    # Archive plugin MUST come before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS

    files = {
        'templates/article.html': 'does not really matter',
        'templates/article_list.html': 'does not really matter',
        'content/reading/hamlet.txt': HAMLET,
        'content/cooking/indian/madras.txt': MADRAS,
        'content/cooking/soup.txt': SOUP,
    }

    def test_archive_template_used_when_using_pure_date_url(self):
        response = self.client.get('/2007/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/')
        self.assert_template_used('article_list.html')

    def test_archive_template_used_when_using_date_index_url(self):
        response = self.client.get('/2007/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/index')
        self.assert_template_used('article_list.html')

    def test_archive_template_used_when_using_date_index_flavour_url(self):
        response = self.client.get('/2007/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/2007/06/01/index.html')
        self.assert_template_used('article_list.html')

    def test_archive_template_used_when_using_category_date_url(self):
        response = self.client.get('/reading/2007/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/')
        self.assert_template_used('article_list.html')

    def test_archive_template_used_when_using_category_date_index_url(self):
        response = self.client.get('/reading/2007/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/index')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/index')
        self.assert_template_used('article_list.html')

    def test_archive_template_used_when_using_category_date_index_flavour_url(self):
        response = self.client.get('/reading/2007/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/index.html')
        self.assert_template_used('article_list.html')

        response = self.client.get('/reading/2007/06/01/index.html')
        self.assert_template_used('article_list.html')

    def test_article_template_used_when_using_permalink_url(self):
        response = self.client.get('/reading/2007/06/01/hamlet')
        self.assert_template_used('article.html')

        response = self.client.get('/reading/2007/06/01/hamlet.html')
        self.assert_template_used('article.html')

        response = self.client.get('/2007/06/01/hamlet.html')
        self.assert_template_used('article.html')

        response = self.client.get('/2007/06/01/hamlet')
        self.assert_template_used('article.html')

    def test_articles_variable_supplied(self):
        response = self.client.get('/2007/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))

        response = self.client.get('/2008/')
        articles = self.get_context_variable('articles')
        self.assertEquals(1, len(articles))


class TestArchiveFilters(TestCaseWithSite):
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    YAWT_META_TYPES = {'create_time': 'iso8601'}

    files = {
        'templates/article.html': 'permalink: {{article.info|permalink}}',
        'content/reading/hamlet.txt': HAMLET,
        'content/cooking/indian/madras.txt': MADRAS,
        'content/cooking/soup.txt': SOUP,
    }

    def test_permalink_filter_extracts_date(self):
        # really this should work with any URL
        response = self.client.get('/reading/hamlet')
        assert 'permalink: /2007/06/02/hamlet' in str(response.data)


class TestArchiveFiltersWithBase(TestCaseWithSite):
    YAWT_EXTENSIONS = ['yawtext.archives.YawtArchives'] + \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    YAWT_META_TYPES = {'create_time': 'iso8601'}
    YAWT_ARCHIVE_BASE = ['reading']

    files = {
        'templates/article.html': 'permalink: {{article.info|permalink}}',
        'content/reading/hamlet.txt': HAMLET,
        'content/cooking/indian/madras.txt': MADRAS,
        'content/cooking/soup.txt': SOUP,
    }

    def test_permalink_filter_extracts_date(self):
        # really this should work with any URL
        response = self.client.get('/reading/hamlet')
        assert 'permalink: /reading/2007/06/02/hamlet' in str(response.data)
