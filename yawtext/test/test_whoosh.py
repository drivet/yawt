from __future__ import absolute_import

import glob
import os
import shutil

from flask.ext.testing import TestCase
from whoosh.fields import KEYWORD, TEXT, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every

import yawt
from yawt.article import Article, ArticleInfo
from yawt.test import TempFolder
from yawt.utils import cfg
from yawtext.indexer import init_index, add_article, commit,\
    remove_article, search, search_page
from yawtext.whoosh import _schema, _field_values, BadFieldType


class TestSite(TempFolder):
    def __init__(self):
        super(TestSite, self).__init__()
        self.files = {
            # entries
            'content/index.txt': 'index text',
            'content/entry.txt': 'entry text',
            'content/cooking/index.txt': 'cooking index text',
            'content/cooking/madras.txt': 'madras text',
            'content/specific.txt': 'specific text',
            'content/reading/hyperion.txt': 'hyperion text'
        }


def _idx_root():
    return cfg('WHOOSH_INDEX_ROOT')


def _article(fullname, tags, content):
    info = ArticleInfo()
    info.fullname = unicode(fullname)
    info.tags = tags
    article = Article()
    article.info = info
    article.content = unicode(content)
    return article


def _create_index():
    os.makedirs(_idx_root())
    return create_in(_idx_root(), _sch())


def _sch():
    fields = _schema()
    return Schema(**fields)


def _query(qstr):
    qp = QueryParser("content", schema=_sch())
    return qp.parse(qstr)


def _searcher():
    ix = open_dir(_idx_root())
    return ix.searcher()


def _count_total():
    with _searcher() as s:
        results = s.search(Every())
        return len(results)


class TestWhooshIndexing(TestCase):
    # no real reason why the index has to be colocated with the site
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh', 'yawtext.indexer.YawtIndexer']
    YAWT_INDEXER_IFC = 'yawtext.whoosh'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'tags': KEYWORD()}

    def create_app(self):
        self.site = TestSite()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def test_init_index_creates_index(self):
        self.assertFalse(os.path.exists(_idx_root()))
        init_index()
        self.assertTrue(os.path.exists(_idx_root()))
        self.assertTrue(glob.glob(os.path.join(_idx_root(), '*.toc')))

    def test_add_article_indexes_article_content(self):
        _create_index()

        add_article(_article('cooking/indian/madras',
                             [u'spicy', u'curry'],
                             'this is an awesome article'))
        add_article(_article('reading/scifi/clarke',
                             [u'monolith', u'alien'],
                             'this is a crappy article'))
        commit()

        # proof that we added it correctly - we can pull it back out
        with _searcher() as s:
            results = s.search(_query('awesome'))
            self.assertEquals(1, len(results))
            self.assertIn('cooking/indian/madras', results[0]['article_info_json'])

    def test_add_article_indexes_article_info(self):
        _create_index()

        add_article(_article('cooking/indian/madras',
                             [u'spicy', u'curry'],
                             'this is an awesome article'))
        add_article(_article('reading/scifi/clarke',
                             [u'monolith', u'alien'],
                             'this is a crappy article'))
        commit()

        # proof that we added it correctly - we can pull it back out
        with _searcher() as s:
            results = s.search(_query("tags:spicy"))
            self.assertEquals(1, len(results))
            self.assertIn('cooking/indian/madras', results[0]['article_info_json'])

    def test_remove_article_deindexes_article(self):
        ix = _create_index()
        writer = ix.writer()
        article = _article('cooking/indian/madras',
                           [u'spicy', u'curry'],
                           'this is an awesome article')
        doc = _field_values(article)
        writer.add_document(**doc)

        article = _article('reading/scifi/clarke',
                           [u'monolith', u'alien'],
                           'this is a crappy article')
        doc = _field_values(article)
        writer.add_document(**doc)
        writer.commit()

        self.assertEquals(2, _count_total())

        remove_article('reading/scifi/clarke')
        commit()

        self.assertEquals(1, _count_total())


    def test_search_returns_results(self):
        ix = _create_index()
        writer = ix.writer()
        article = _article('cooking/indian/madras',
                           [u'spicy', u'curry'],
                           'this is an awesome article')
        doc = _field_values(article)
        writer.add_document(**doc)

        article = _article('reading/scifi/clarke',
                           [u'monolith', u'alien'],
                           'this is a crappy article')
        doc = _field_values(article)
        writer.add_document(**doc)
        writer.commit()

        articles = search('tags:monolith')
        self.assertEquals(1, len(articles))
        self.assertEquals('reading/scifi/clarke', articles[0].fullname)

    def test_search_page_returns_page_results_and_total(self):
        ix = _create_index()
        writer = ix.writer()
        article = _article('cooking/indian/madras',
                           [u'spicy', u'curry'],
                           'this is an awesome article')
        doc = _field_values(article)
        writer.add_document(**doc)

        article = _article('reading/scifi/clarke',
                           [u'monolith', u'alien'],
                           'this is a crappy article')
        doc = _field_values(article)
        writer.add_document(**doc)
        writer.commit()

        articles, total = search_page('', None, page=1, pagelen=1)
        self.assertEquals(1, len(articles))
        self.assertEquals(2, total)


    def tearDown(self):
        if os.path.exists(_idx_root()):
            shutil.rmtree(_idx_root())
        self.site.remove()


class TestWhooshIndexingBadConfig(TestCase):
    # no real reason why the index has to be colocated with the site
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh', 'yawtext.indexer.YawtIndexer']
    YAWT_INDEXER_IFC = 'yawtext.whoosh'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'tags': TEXT()}

    def create_app(self):
        self.site = TestSite()
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def test_add_article_raises_exception(self):
        _create_index()

        article = _article('cooking/indian/madras',
                           [u'spicy', u'curry'],
                           'this is an awesome article')
        self.assertRaises(BadFieldType, add_article, article)

    def tearDown(self):
        if os.path.exists(_idx_root()):
            shutil.rmtree(_idx_root())
        self.site.remove()
