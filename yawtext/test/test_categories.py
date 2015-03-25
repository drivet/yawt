#pylint: skip-file

import unittest
from yawtext.categories import YawtCategories, HierarchyCount
from whoosh.fields import DATETIME, STORED, ID, KEYWORD, Schema
from whoosh.index import create_in
from yawt import create_app
from flask import g
import os
from yawt.utils import load_file
from yawt.article import ArticleInfo, Article
import jsonpickle
from yawt.test.siteutils import TempSite
from yawtext.test.utils import generate_collection_template
from datetime import datetime

def dt(year, month, day):
    dtime = datetime(year, month, day, 0, 0, 0)
    import time
    return long(time.mktime(dtime.timetuple()))

class TestConfig(object):
    def __init__(self, site):
        self.WHOOSH_INDEX_ROOT = os.path.join(site.abs_state_root(), 'whoosh')
        self.YAWT_WHOOSH_ARTICLE_INFO_FIELDS = \
            {'create_time': DATETIME(sortable=True), 'categories': KEYWORD(commas=True)}

class TestYawtCategories(unittest.TestCase):
    def setUp(self):
        self.site = TempSite()
        self.site.initialize()
        self.plugin = YawtCategories()
        self.app = create_app(self.site.site_root, 
                              config = TestConfig(self.site),
                              extension_info = extension_info(self.plugin))
        self.app.testing = True
        self.app.debug = True
        os.makedirs(self.app.config['WHOOSH_INDEX_ROOT'])

    def test_default_category_template(self):
        self.assertEqual('article_list', self.app.config['YAWT_CATEGORY_TEMPLATE'])

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
        template = generate_collection_template('a', 'articles', ['info.fullname'])
        self.site.save_template('article_list.html', template)
        self.site.save_content('article1.txt', u'stuff1')
        self.site.save_content('article2.txt', u'stuff2')
        self.site.save_content('article3.txt', u'stuff3')
        self.site.save_content('article4.txt', u'stuff4')

        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('article1', '', 'article1', 'txt', dt(2004, 11, 03) )
        writer.add_document(fullname=u'article1', create_time=datetime.fromtimestamp(dt(2004, 11, 04)), 
                            content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1))
        info2 = ArticleInfo('article2', '', 'article2', 'txt', dt(2004, 11, 05))
        writer.add_document(fullname=u'article2', create_time=datetime.fromtimestamp(dt(2004, 11, 05)), 
                            content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2))
        info3 = ArticleInfo('article3', '', 'article3', 'txt', dt(2004, 11, 04))
        writer.add_document(fullname=u'article3', create_time=datetime.fromtimestamp(dt(2004, 11, 04)), 
                            content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3))
        info4 = ArticleInfo('article4', '', 'article4', 'txt', dt(2004, 11, 02))
        writer.add_document(fullname=u'article4', create_time=datetime.fromtimestamp(dt(2004, 11, 02)), 
                            content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4))
        writer.commit()

        with self.app.test_client() as c:
            rv = c.get('/index.html')
            assert 'article1' in rv.data
            assert 'article2' in rv.data
            assert 'article3' in rv.data
            assert 'article4' in rv.data

    def test_on_404_renders_if_fullname_is_categorized_index_file(self):
        template = generate_collection_template('a', 'articles', ['info.fullname'])
        self.site.save_template('article_list.html', template)
        self.site.mk_content_category('foo')
        self.site.mk_content_category('bar')
        self.site.save_content('foo/article1.txt', u'stuff1')
        self.site.save_content('bar/article2.txt', u'stuff2')
        self.site.save_content('foo/article3.txt', u'stuff3')
        self.site.save_content('bar/article4.txt', u'stuff4')
        
        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('foo/article1', 'foo', 'article1', 'txt',dt(2004, 11, 03) )
        writer.add_document(fullname=u'foo/article1', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)),
                            content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1), categories=u"foo")
        info2 = ArticleInfo('bar/article2', 'bar', 'article2', 'txt', dt(2004, 11, 05))
        writer.add_document(fullname=u'bar/article2', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 05)),
                            content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2), categories=u"bar" )
        info3 = ArticleInfo('foo/article3', 'foo', 'article3', 'txt', dt(2004, 11, 04))
        writer.add_document(fullname=u'foo/article3', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)),
                            content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3), categories=u"foo")
        info4 = ArticleInfo('bar/article4', 'bar', 'article4', 'txt', dt(2004, 11, 02))
        writer.add_document(fullname=u'bar/article4', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 02)),
                            content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4), categories=u"bar")
        writer.commit()

        with self.app.test_client() as c:
            rv = c.get('/foo/index.html')
            assert 'article1' in rv.data
            assert 'article3' in rv.data
            assert 'article2' not in rv.data
            assert 'article4' not in rv.data
            

    def test_on_404_renders_if_fullname_is_nested_categorized_index_file(self):
        template = generate_collection_template('a', 'articles', ['info.fullname'])
        self.site.save_template('article_list.html', template)
        self.site.mk_content_category('foo')
        self.site.mk_content_category('foo/har')
        self.site.mk_content_category('foo/gad')
        self.site.mk_content_category('bar')

        self.site.save_content('foo/har/article1.txt', u'stuff1')
        self.site.save_content('bar/article2.txt', u'stuff2')
        self.site.save_content('foo/gad/article3.txt', u'stuff3')
        self.site.save_content('bar/article4.txt', u'stuff4')

        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('foo/har/article1', 'foo/har', 'article1', 'txt',dt(2004, 11, 03) )
        writer.add_document(fullname=u'foo/har/article1', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)),
                            content=u'stuff1', 
                            article_info_json=jsonpickle.encode(info1), categories=u"foo,foo/har")
        info2 = ArticleInfo('bar/article2', 'bar', 'article2', 'txt', dt(2004, 11, 05))
        writer.add_document(fullname=u'bar/article2', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 05)),
                            content=u'stuff2', 
                            article_info_json=jsonpickle.encode(info2), categories=u"bar" )
        info3 = ArticleInfo('foo/gad/article3', 'foo/gad', 'article3', 'txt', dt(2004, 11, 04))
        writer.add_document(fullname=u'foo/gad/article3', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)),
                            content=u'stuff3',
                            article_info_json=jsonpickle.encode(info3), categories=u"foo,foo/gad")
        info4 = ArticleInfo('bar/article4', 'bar', 'article4', 'txt', dt(2004, 11, 02))
        writer.add_document(fullname=u'bar/article4', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 02)),
                            content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4), categories=u"bar")
        writer.commit()

        with self.app.test_client() as c:
            rv = c.get('/foo/index.html')
            assert 'article3' in rv.data
            assert 'article1' in rv.data
            assert 'article2' not in rv.data
            assert 'article4' not in rv.data
            
            rv = c.get('/foo/har/index.html')
            assert 'article1' in rv.data
            assert 'article2' not in rv.data 
            assert 'article3' not in rv.data
            assert 'article4' not in rv.data
 
    def test_walking_produces_readable_categorycount_file(self):
        self.site.mk_content_category('foo')
        self.site.mk_content_category('bar')
        
        self.site.save_content('foo/article1.txt', u'stuff1')
        self.site.save_content('foo/article2.txt', u'stuff2')
        self.site.save_content('foo/article3.txt', u'stuff3')
        self.site.save_content('bar/article4.txt', u'stuff4')

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.walk()

        countfile = self.abs_category_count_file()
        self.assertTrue(os.path.exists(countfile))
        categorycounts = jsonpickle.decode(load_file(countfile))
        self.assertEquals(4, categorycounts.count)
        assert 'foo' in [c.category for c in categorycounts.children]
        assert 'bar' in [c.category for c in categorycounts.children]
        if categorycounts.children[0].category == 'foo':
            foocat = categorycounts.children[0]
            barcat = categorycounts.children[1]
        else:
            foocat = categorycounts.children[1]
            barcat = categorycounts.children[0]

        self.assertEquals(3, foocat.count)
        self.assertEquals(1, barcat.count)

    def test_changed_files_adjust_categories(self):
        self.site.mk_content_category('foo')
        self.site.mk_content_category('bar')
        
        self.site.save_content('foo/article1.txt', u'stuff1')
        self.site.save_content('foo/article2.txt', u'stuff2')
        self.site.save_content('foo/article3.txt', u'stuff3')
        self.site.save_content('bar/article4.txt', u'stuff4')

        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('foo/article1', 'foo', 'article1', 'txt', dt(2004, 11, 03) )
        info1.categories = ['foo']
        writer.add_document(fullname=u'foo/article1', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)),
                            content=u'stuff1',
                            article_info_json=jsonpickle.encode(info1))

        info2 = ArticleInfo('foo/article2', 'foo', 'article2', 'txt', dt(2004, 11, 05))
        info2.categories = ['foo']
        writer.add_document(fullname=u'foo/article2', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 05)), 
                            content=u'stuff2',
                            article_info_json=jsonpickle.encode(info2))

        info3 = ArticleInfo('foo/article3', 'foo', 'article3', 'txt', dt(2004, 11, 04))
        info3.categories = ['foo']
        writer.add_document(fullname=u'foo/article3',
                            create_time=datetime.fromtimestamp(dt(2004, 11, 04)), 
                            content=u'stuff3', 
                            article_info_json=jsonpickle.encode(info3))

        info4 = ArticleInfo('bar/article4', 'bar', 'article4', 'txt', dt(2004, 11, 02))
        info4.categories = ['bar']
        writer.add_document(fullname=u'bar/article4', 
                            create_time=datetime.fromtimestamp(dt(2004, 11, 02)),
                            content=u'stuff4',
                            article_info_json=jsonpickle.encode(info4))
        writer.commit()

        # set up category file
        catcount = HierarchyCount()
        catcount.count = 4
        catcount.category = ''
        
        foocat = HierarchyCount()
        foocat.category = 'foo'
        foocat.count = 3

        barcat = HierarchyCount()
        barcat.category = 'bar'
        barcat.count = 1

        catcount.children.append(foocat)
        catcount.children.append(barcat)

        self.site.save_state_file(self.abs_category_count_file(), jsonpickle.encode(catcount))

        self.site.save_content('foo/article1.txt', u'stuff_blah')
        modified = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'foo/article1.txt')]
        
        self.site.save_content('bar/article5.txt', u'stuff5')
        self.site.save_content('bar/article2.txt', u'stuff5')
        added = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'bar/article5.txt')]
        added.append(os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'bar/article2.txt'))

        self.site.remove_content('foo/article2.txt')
        removed = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'foo/article2.txt')]

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.files_changed(modified, added, removed)

        countfile = self.abs_category_count_file()
        self.assertTrue(os.path.exists(countfile))
        categorycounts = jsonpickle.decode(load_file(countfile))
        
        self.assertEquals(5, categorycounts.count)
        assert 'foo' in [c.category for c in categorycounts.children]
        assert 'bar' in [c.category for c in categorycounts.children]
        if categorycounts.children[0].category == 'foo':
            foocat = categorycounts.children[0]
            barcat = categorycounts.children[1]
        else:
            foocat = categorycounts.children[1]
            barcat = categorycounts.children[0]

        self.assertEquals(2, foocat.count)
        self.assertEquals(3, barcat.count)

    def abs_category_count_file(self):
        root = self.app.yawt_root_dir
        tagcountfile = self.app.config['YAWT_CATEGORY_COUNT_FILE']
        state_folder = self.app.config['YAWT_STATE_FOLDER']
        return os.path.join(root, state_folder, tagcountfile)

    def index_root(self):
        return self.app.config['WHOOSH_INDEX_ROOT']

    def _schema(self):
        fields = {}
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_INFO_FIELDS'])
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_FIELDS'])
        fields['article_info_json'] = STORED
        fields['fullname'] = ID
        return fields

    def tearDown(self):   
        self.site.remove()


def extension_info(plugin):
    from flask_whoosh import Whoosh
    whoosh = Whoosh()
    from yawtext.indexer import YawtWhoosh
    yawtwhoosh = YawtWhoosh()
    from yawtext.collections import YawtCollections
    yawtpaging = YawtCollections()

    return ({'flask_whoosh.Whoosh': whoosh, 
             'yawtext.indexer.YawtWhoosh': yawtwhoosh,
             'yawtext.collections.YawtCollections': yawtpaging,
             'yawtext.categories.YawtCategories':plugin},
            [whoosh, yawtwhoosh, yawtpaging, plugin])
