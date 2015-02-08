import unittest
from yawtext.categories import YawtCategories
from whoosh.fields import DATETIME, STORED, ID, KEYWORD, Schema
from whoosh.index import create_in
from yawt import create_app
from flask import g
import shutil
import os
from datetime import datetime
from yawt.utils import save_file
from yawt.article import ArticleInfo, Article
import jsonpickle
from mock import patch

class TestYawtWhoosh(unittest.TestCase):
    def setUp(self):
        self.site_root = '/tmp/blah'
        self.plugin = YawtCategories()
        self.app = create_app(self.site_root, extension_info = extension_info(self.plugin))
        self.index_root = os.path.join(self.site_root, self.app.config['YAWT_STATE_FOLDER'], 'whoosh')
        self.app.config['WHOOSH_INDEX_ROOT'] = self.index_root
        self.app.config['YAWT_WHOOSH_ARTICLE_INFO_FIELDS'] = \
            {'create_time': DATETIME, 'categories': KEYWORD(commas=True)}

    def test_default_category_template(self):
        self.assertEqual('article_collection', self.app.config['YAWT_CATEGORY_TEMPLATE'])

    def test_on_article_fetch_sets_categories(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.category = 'cooking/indian'
            article = Article()
            article.info = info
            article = g.site._on_article_fetch(article)
        self.assertEqual(['cooking/indian', 'cooking'], article.info.categories)
  
    def test_on_404_skips_rendering_if_fullname_is_not_index_file(self): 
        with self.app.test_request_context():
            self.app.preprocess_request()
            self.assertFalse(self.plugin.on_404('blah', 'html'))

    def test_on_404_renders_if_fullname_is_root_index_file(self):
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

        info1 = ArticleInfo('article1', '', 'article1', 'txt',datetime(2004, 11, 03) )
        writer.add_document(fullname=u'article1', create_time=datetime(2004, 11, 04), content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1))
        info2 = ArticleInfo('article2', '', 'article2', 'txt', datetime(2004, 11, 05))
        writer.add_document(fullname=u'article2', create_time=datetime(2004, 11, 05), content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2))
        info3 = ArticleInfo('article3', '', 'article3', 'txt', datetime(2004, 11, 04))
        writer.add_document(fullname=u'article3', create_time=datetime(2004, 11, 04), content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3))
        info4 = ArticleInfo('article4', '', 'article4', 'txt', datetime(2004, 11, 02))
        writer.add_document(fullname=u'article4', create_time=datetime(2004, 11, 02), content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4))
        writer.commit()

        with self.app.test_request_context():
            self.app.preprocess_request()
            with patch('yawtext.categories.render') as mock:
                mock.return_value = ''
                page = self.plugin.on_404('index', 'html')
                mock.assert_called_with('index', 'html', 
                                        {'article_infos': [info2, info3, info1, info4]},
                                        None)

    def test_on_404_renders_if_fullname_is_categorized_index_file(self):
        content_root = os.path.join(self.site_root, self.app.config['YAWT_CONTENT_FOLDER'])
        os.makedirs(content_root)
        os.makedirs(os.path.join(content_root, 'foo'))
        os.makedirs(os.path.join(content_root, 'bar'))
        
        save_file(os.path.join(content_root, 'foo/article1.txt'), u'stuff1')
        save_file(os.path.join(content_root, 'bar/article2.txt'), u'stuff2')
        save_file(os.path.join(content_root, 'foo/article3.txt'), u'stuff3')
        save_file(os.path.join(content_root, 'bar/article4.txt'), u'stuff4')
        os.makedirs(self.index_root)
        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root, schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('foo/article1', 'foo', 'article1', 'txt',datetime(2004, 11, 03) )
        writer.add_document(fullname=u'foo/article1', create_time=datetime(2004, 11, 04), 
                            content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1), categories=u"foo")
        info2 = ArticleInfo('bar/article2', 'bar', 'article2', 'txt', datetime(2004, 11, 05))
        writer.add_document(fullname=u'bar/article2', create_time=datetime(2004, 11, 05), 
                            content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2), categories=u"bar" )
        info3 = ArticleInfo('foo/article3', 'foo', 'article3', 'txt', datetime(2004, 11, 04))
        writer.add_document(fullname=u'foo/article3', create_time=datetime(2004, 11, 04), 
                            content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3), categories=u"foo")
        info4 = ArticleInfo('bar/article4', 'bar', 'article4', 'txt', datetime(2004, 11, 02))
        writer.add_document(fullname=u'bar/article4', create_time=datetime(2004, 11, 02), 
                            content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4), categories=u"bar")
        writer.commit()

        with self.app.test_request_context():
            self.app.preprocess_request()
            with patch('yawtext.categories.render') as mock:
                mock.return_value = ''
                page = self.plugin.on_404('foo/index', 'html')
                mock.assert_called_with('foo/index', 'html', 
                                        {'article_infos': [info3, info1]},
                                        None)

    def test_on_404_renders_if_fullname_is_nested_categorized_index_file(self):
        content_root = os.path.join(self.site_root, self.app.config['YAWT_CONTENT_FOLDER'])
        os.makedirs(content_root)
        os.makedirs(os.path.join(content_root, 'foo/har'))
        os.makedirs(os.path.join(content_root, 'foo/gad'))
        os.makedirs(os.path.join(content_root, 'bar'))
        
        save_file(os.path.join(content_root, 'foo/har/article1.txt'), u'stuff1')
        save_file(os.path.join(content_root, 'bar/article2.txt'), u'stuff2')
        save_file(os.path.join(content_root, 'foo/gad/article3.txt'), u'stuff3')
        save_file(os.path.join(content_root, 'bar/article4.txt'), u'stuff4')
        os.makedirs(self.index_root)
        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root, schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('foo/har/article1', 'foo/har', 'article1', 'txt',datetime(2004, 11, 03) )
        writer.add_document(fullname=u'foo/har/article1', create_time=datetime(2004, 11, 04), content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1), categories=u"foo,foo/har")
        info2 = ArticleInfo('bar/article2', 'bar', 'article2', 'txt', datetime(2004, 11, 05))
        writer.add_document(fullname=u'bar/article2', create_time=datetime(2004, 11, 05), content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2), categories=u"bar" )
        info3 = ArticleInfo('foo/gad/article3', 'foo/gad', 'article3', 'txt', datetime(2004, 11, 04))
        writer.add_document(fullname=u'foo/gad/article3', create_time=datetime(2004, 11, 04), content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3), categories=u"foo,foo/gad")
        info4 = ArticleInfo('bar/article4', 'bar', 'article4', 'txt', datetime(2004, 11, 02))
        writer.add_document(fullname=u'bar/article4', create_time=datetime(2004, 11, 02), content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4), categories=u"bar")
        writer.commit()

        with self.app.test_request_context():
            self.app.preprocess_request()
            with patch('yawtext.categories.render') as mock:
                mock.return_value = ''
                page = self.plugin.on_404('foo/index', 'html')
                mock.assert_called_with('foo/index', 'html', 
                                        {'article_infos': [info3, info1]},
                                        None)

            with patch('yawtext.categories.render') as mock:
                mock.return_value = ''
                page = self.plugin.on_404('foo/har/index', 'html')
                mock.assert_called_with('foo/har/index', 'html', 
                                        {'article_infos': [info1]},
                                        None)

   
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
    from yawtext.indexer import YawtWhoosh
    yawtwhoosh = YawtWhoosh()
    return ({'whoosh': whoosh, 'yawtwhoosh': yawtwhoosh, 'categories':plugin},
            [plugin], mk_init_app(whoosh, yawtwhoosh, plugin))

def mk_init_app(whoosh, yawtwhoosh, yawtcategories):
    def init_app(app):
        whoosh.init_app(app)
        yawtwhoosh.init_app(app)
        yawtcategories.init_app(app)
    return init_app
