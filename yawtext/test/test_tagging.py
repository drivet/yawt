#pylint: skip-file
import os

import jsonpickle
from flask_testing import TestCase

from yawt import create_app
from yawt.utils import abs_state_folder, load_file
from yawtext.test import TestCaseWithIndex


class TestYawtTaggingInitialize(TestCase):
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagging',
                       'yawtext.tagging.YawtTagCounter']

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

FILES = {
    'templates/article.html': 'does not really matter',
    'templates/article_list.html': 'does not really matter',
    'content/reading/hamlet.txt': HAMLET,
    'content/cooking/indian/madras.txt': MADRAS,
    'content/cooking/soup.txt': SOUP,
}


class TestTaggingCounts(TestCaseWithIndex):
    # Tagging plugin MUST comes before indexing plugin
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagCounter']+ \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    files = FILES
    walkOnSetup = False

    def test_counts_tagging_with_count_file_on_walk(self):
        self.app.config['YAWT_TAGGING_COUNT_FILE'] = '_anothercountfile'
        self._walk()

        counts_path = os.path.join(abs_state_folder(), '_anothercountfile')
        countobj = jsonpickle.decode(load_file(counts_path))
        self.assertEquals(5, len(countobj.keys()))

    def test_counts_tagging_with_bases_on_walk(self):
        self.app.config['YAWT_TAGGING_BASE'] = ['reading', 'cooking']
        self._walk()

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
        self._walk()

        self.site.change(added={'content/reading/emma.txt': EMMA},
                         modified={'content/cooking/indian/madras.txt': NEW_MADRAS},
                         deleted=['content/cooking/soup.txt'])

        readingcounts_path = os.path.join(abs_state_folder(),
                                          'reading/tagcounts')
        readingcountobj = jsonpickle.decode(load_file(readingcounts_path))

        cookingcounts_path = os.path.join(abs_state_folder(),
                                          'cooking/tagcounts')
        cookingcountobj = jsonpickle.decode(load_file(cookingcounts_path))

        self.assertEquals(3, len(readingcountobj.keys()))
        self.assertEquals(1, len(cookingcountobj.keys()))

    def test_tagging_count_variable_supplied(self):
        self._walk()
        response = self.client.get('/reading/hamlet')
        countobj = self.get_context_variable('tagcounts')
        self.assertEquals(5, len(countobj.keys()))


class TestTaggingPages(TestCaseWithIndex):
    YAWT_EXTENSIONS = ['yawtext.tagging.YawtTagging']+ \
                      TestCaseWithIndex.YAWT_EXTENSIONS
    files = FILES

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

    def test_articles_variable_supplied(self):
        response = self.client.get('/tags/shakespeare/')
        articles = self.get_context_variable('articles')
        self.assertEquals(1, len(articles))

        response = self.client.get('/tags/cumin/')
        articles = self.get_context_variable('articles')
        self.assertEquals(2, len(articles))

