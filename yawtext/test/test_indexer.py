#pylint: skip-file
import glob
import os
import shutil

from flask import g, current_app
from flask.ext.testing import TestCase
from whoosh.fields import TEXT

from yawt import create_app
from yawt.article import Article, ArticleInfo
from yawt.cli import Walk
from yawt.test import TempFolder
from yawt.utils import cfg, call_plugins, base_and_ext, fullname
from yawtext.indexer import init_index, add_article, commit, search
from yawtext.vc import ChangedFiles


def _idx_root():
    return cfg('WHOOSH_INDEX_ROOT')


class TestYawtIndexerInitialize(TestCase):
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh', 'yawtext.indexer.YawtIndexer']
    WHOOSH_INDEX_ROOT = '/tmp/blah/_state/index'

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_indexer_has_default_config(self):
        self.assertEquals('yawtext.whoosh', self.app.config['YAWT_INDEXER_IFC'])
        self.assertEquals({}, self.app.config['YAWT_INDEXER_WHOOSH_INFO_FIELDS'])
        self.assertEquals({'content': TEXT()}, self.app.config['YAWT_INDEXER_WHOOSH_FIELDS'])

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


# Proper indexer tests
#
def _article(fullname, extension, content):
    info = ArticleInfo()
    info.fullname = unicode(fullname)
    info.extension = unicode(extension)
    article = Article()
    article.info = info
    article.content = unicode(content)
    return article


class TestIndexedFolder(TempFolder):
    def __init__(self):
        super(TestIndexedFolder, self).__init__()
        self.files = {
            'content/entry.txt': 'blah',
            'content/random.txt': 'random',
            'content/food.txt': 'food',
        }

    def index_all(self):
        with current_app.app_context():
            init_index()
            for repofile in self.files.keys():
                fname = fullname(repofile)
                _, ext = base_and_ext(repofile)
                add_article(_article(fname, ext, self.files[repofile]))
            commit()


class TestYawtIndexer(TestCase):
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh', 'yawtext.indexer.YawtIndexer']
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'

    def create_app(self):
        self.site = TestIndexedFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_clears_index_and_reindexes_all_articles_on_walk(self):
        # set up index so that it looks nothing like the site
        init_index()
        add_article(_article('oldentry', 'txt', 'oldentry'))
        commit()
        # quick check that there's something in the index
        self.assertEquals(1, len(search('')))

        # after the search and commit, I need a new app context for the walk.
        # I'm not sure if this should be consided a bug or not
        with self.app.app_context():
            walk = Walk()
            walk.run()
            self.assertEquals(3, len(search('')))
            self.assertEquals(1, len(search('content:blah')))
            self.assertEquals(1, len(search('content:random')))
            self.assertEquals(1, len(search('content:food')))

    def test_adds_incremental_changes_to_index(self):
        # index everything
        self.site.index_all()
        # make some changes
        self.site.save_file('content/newentry.txt', 'newentry')
        self.site.save_file('content/food.txt', 'newfood')
        self.site.delete_file('content/random.txt')
        changed = ChangedFiles(added=['content/newentry.txt'],
                               modified=['content/food.txt'],
                               deleted=['content/random.txt'])
        call_plugins('on_files_changed', changed)
        with self.app.app_context():
            self.assertEquals(3, len(search('')))
            self.assertEquals(1, len(search('content:blah')))
            self.assertEquals(1, len(search('content:newentry')))
            self.assertEquals(1, len(search('content:newfood')))

    def tearDown(self):
        if os.path.exists(_idx_root()):
            shutil.rmtree(_idx_root())
        self.site.remove()
