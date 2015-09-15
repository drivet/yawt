#pylint: skip-file
import glob
import os
import shutil

from flask import g
from flask.ext.testing import TestCase
from whoosh.fields import TEXT

from yawt import create_app
from yawt.cli import Walk
from yawt.utils import cfg
from yawtext.indexer import search
from yawtext.test import TestCaseWithIndex


def _idx_root():
    return cfg('WHOOSH_INDEX_ROOT')


# this doesn't extend TestCaseWithWalker because I want to see what
# happens upon *new* site creation.  TestCaseWithIndexedSite always reindexes
# each time you setUp()
class TestYawtIndexerInitialize(TestCase):
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh', 'yawtext.indexer.YawtIndexer']
    WHOOSH_INDEX_ROOT = '/tmp/blah/_state/index'

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_indexer_has_default_config(self):
        self.assertEquals('yawtext.whoosh',
                          self.app.config['YAWT_INDEXER_IFC'])
        self.assertEquals({},
                          self.app.config['YAWT_INDEXER_WHOOSH_INFO_FIELDS'])
        self.assertEquals({'content': TEXT()},
                          self.app.config['YAWT_INDEXER_WHOOSH_FIELDS'])

    def test_index_initialized_on_new_site(self):
        self.assertFalse(os.path.exists(_idx_root()))
        g.site.initialize()
        self.assertTrue(os.path.exists(_idx_root()))
        self.assertTrue(glob.glob(os.path.join(_idx_root(), '*.toc')))

    def tearDown(self):
        if os.path.exists('/tmp/blah'):
            shutil.rmtree('/tmp/blah')
        if os.path.exists(_idx_root()):
            shutil.rmtree(_idx_root())


class TestYawtIndexer(TestCaseWithIndex):
    files = {
        'content/entry.txt': 'blah',
        'content/random.txt': 'random',
        'content/food.txt': 'food',
    }

    def test_clears_index_and_reindexes_all_articles_on_walk(self):
        # quick check that there's something in the index
        self.assertEquals(3, len(search('')))
        self.assertEquals(1, len(search('content:blah')))
        self.assertEquals(1, len(search('content:random')))
        self.assertEquals(1, len(search('content:food')))

        # change contents completely
        self.site.delete_file('content/food.txt')
        self.site.delete_file('content/random.txt')
        self.site.delete_file('content/entry.txt')
        self.site.save_file('content/newentry.txt', 'newentry')

        with self.app.app_context():
            walk = Walk()
            walk.run()

            # now the extra file should be indexed
            self.assertEquals(1, len(search('')))
            self.assertEquals(1, len(search('content:newentry')))

    def test_adds_incremental_changes_to_index(self):
        # make some changes
        self.site.change(added={'content/newentry.txt': 'newentry'},
                         modified={'content/food.txt': 'newfood'},
                         deleted=['content/random.txt'])
        with self.app.app_context():
            self.assertEquals(3, len(search('')))
            self.assertEquals(1, len(search('content:blah')))
            self.assertEquals(1, len(search('content:newentry')))
            self.assertEquals(1, len(search('content:newfood')))
