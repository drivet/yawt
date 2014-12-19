import unittest
from yawtext.indexer import YawtWhoosh
from whoosh.fields import TEXT, DATETIME, STORED, ID, Schema
from whoosh.index import create_in
from whoosh.qparser import QueryParser
from yawt import create_app
from flask import g
import shutil
import glob
import os
from datetime import datetime
from yawt.fileutils import save_file

class TestYawtWhoosh(unittest.TestCase):
    def setUp(self):
        self.site_root = '/tmp/blah'
        self.plugin = YawtWhoosh()
        self.app = create_app(self.site_root, extension_info = extension_info(self.plugin))
        self.index_root = os.path.join(self.site_root, self.app.config['YAWT_STATE_FOLDER'], 'whoosh')
        self.app.config['WHOOSH_INDEX_ROOT'] = self.index_root

    def test_default_article_info_fields(self):
        self.assertEqual({'create_time': DATETIME}, self.app.config['YAWT_WHOOSH_ARTICLE_INFO_FIELDS'])
 
    def test_default_article_fields(self):
        self.assertEqual({'content': TEXT}, self.app.config['YAWT_WHOOSH_ARTICLE_FIELDS'])
 
    def test_index_initialized_on_new_site(self):
        self.assertFalse(os.path.exists(self.index_root))
        with self.app.test_request_context(): 
            self.app.preprocess_request()
            g.site.new_site()
            self.assertTrue(os.path.exists(self.index_root))
            self.assertTrue(glob.glob(os.path.join(self.index_root, '*.toc')))
 
    def test_walk_clears_index_and_reindexes_all_articles(self):
        content_root = os.path.join(self.site_root, self.app.config['YAWT_CONTENT_FOLDER'])
        os.makedirs(content_root)
        save_file(os.path.join(content_root, 'article1.txt'), u'stuff1')
        save_file(os.path.join(content_root, 'article2.txt'), u'stuff2')
        save_file(os.path.join(content_root, 'article3.txt'), u'stuff3')
        save_file(os.path.join(content_root, 'article4.txt'), u'stuff4')
        os.makedirs(self.index_root)
        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root, schema = schema)
        writer = idx.writer()
        now = datetime.utcnow()
        # index bears no resemblance to what's on disk
        writer.add_document(fullname=u'article5', create_time=now, content=u'stuff5')
        writer.add_document(fullname=u'article6', create_time=now, content=u'stuff6')
        writer.add_document(fullname=u'article7', create_time=now, content=u'stuff7')
        writer.add_document(fullname=u'article8', create_time=now, content=u'stuff8')
        writer.commit()
 
        qp = QueryParser('fullname', schema=schema)
        with idx.searcher() as searcher:
            results = searcher.search(qp.parse(u"article1"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article2"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article3"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article4"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article5"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article6"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article7"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article8"))
            self.assertEquals(1, len(results))

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.walk()
 
        qp = QueryParser('fullname', schema=schema)
        with idx.searcher() as searcher:
            results = searcher.search(qp.parse(u"article1"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article2"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article3"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article4"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article5"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article6"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article7"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article8"))
            self.assertEquals(0, len(results))

    def test_files_index_on_changed_files_call(self):
        content_root = os.path.join(self.site_root, self.app.config['YAWT_CONTENT_FOLDER'])
        os.makedirs(content_root)
        save_file(os.path.join(content_root, 'article1.txt'), u'stuff1')
        save_file(os.path.join(content_root, 'article2.txt'), u'stuff2')
        save_file(os.path.join(content_root, 'article5.txt'), u'stuff5')
        save_file(os.path.join(content_root, 'article6.txt'), u'stuff6')
        
        os.makedirs(self.index_root)
        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root, schema = schema)
        writer = idx.writer()
        now = datetime.utcnow()
        writer.add_document(fullname=u'article1', create_time=now, content=u'oldstuff1')
        writer.add_document(fullname=u'article2', create_time=now, content=u'oldstuff2')
        writer.add_document(fullname=u'article3', create_time=now, content=u'stuff3')
        writer.add_document(fullname=u'article4', create_time=now, content=u'stuff4')
        writer.commit()
        
        qp = QueryParser('fullname', schema=schema)
        with idx.searcher() as searcher:
            results = searcher.search(qp.parse(u"article1"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article2"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article3"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article4"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article5"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article6"))
            self.assertEquals(0, len(results))

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.files_changed(files_modified=['content/article1.txt', 'content/article2.txt'], 
                                 files_added=['content/article5.txt', 'content/article6.txt'],
                                 files_removed=['content/article3.txt', 'content/article4.txt'])

        qp = QueryParser('fullname', schema=schema)
        with idx.searcher() as searcher:
            results = searcher.search(qp.parse(u"article1"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article2"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article3"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article4"))
            self.assertEquals(0, len(results))
            results = searcher.search(qp.parse(u"article5"))
            self.assertEquals(1, len(results))
            results = searcher.search(qp.parse(u"article6"))
            self.assertEquals(1, len(results))

    def _schema(self):
        fields = {}
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_INFO_FIELDS'])
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_FIELDS'])
        fields['article_info_json'] = STORED
        fields['fullname'] = ID
        return fields

    def tearDown(self):
        if os.path.exists(self.site_root):
            shutil.rmtree(self.site_root)


def extension_info(plugin):
    from flask_whoosh import Whoosh
    whoosh = Whoosh()
    return ({'whoosh': whoosh, 'yawtwhoosh': plugin}, [plugin], mk_init_app(whoosh, plugin))

def mk_init_app(whoosh, yawtwhoosh):
    def init_app(app):
        whoosh.init_app(app)
        yawtwhoosh.init_app(app)
    return init_app
