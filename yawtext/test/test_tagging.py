import unittest
from yawtext.tagging import YawtTagging, TagInfo
from whoosh.fields import DATETIME, STORED, ID, KEYWORD, Schema
from whoosh.index import create_in
from yawt import create_app
from flask import g
import os
from datetime import datetime
from yawt.utils import load_file
from yawt.article import ArticleInfo, Article
import jsonpickle
from yawt.test.siteutils import TempSite
from yawtext.test.utils import generate_collection_template

class TestConfig(object):
    def __init__(self, site):
        self.WHOOSH_INDEX_ROOT = os.path.join(site.abs_state_root(), 'whoosh')
        self.YAWT_WHOOSH_ARTICLE_INFO_FIELDS = \
            {'create_time': DATETIME, 'tags': KEYWORD(commas=True)}
        self.YAWT_ARTICLE_EXTENSIONS = ['md']

class TestYawtTagging(unittest.TestCase):
    def setUp(self):
        self.site = TempSite()
        self.site.initialize()

        self.plugin = YawtTagging()

        self.app = create_app(self.site.site_root, 
                              config = TestConfig(self.site),
                              extension_info = extension_info(self.plugin))
        self.app.testing = True

        os.makedirs(self.app.config['WHOOSH_INDEX_ROOT'])

    def test_default_tagging_template(self):
        self.assertEqual('article_list', self.app.config['YAWT_TAGGING_TEMPLATE'])

    def test_on_article_fetch_sets_taglist(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.tags = 'tag1,tag2'
            article = Article()
            article.info = info
            article = g.site._on_article_fetch(article)
            self.assertEqual(['tag1', 'tag2'], article.info.taglist)
            
    def test_on_article_fetch_ignores_whitespace(self):
        with self.app.test_request_context():
            self.app.preprocess_request()
            info = ArticleInfo()
            info.tags = '   tag1, tag2  '
            article = Article()
            article.info = info
            article = g.site._on_article_fetch(article)
        self.assertEqual(['tag1', 'tag2'], article.info.taglist)

    def test_walking_produces_readable_tagcount_file(self):
        self.site.save_content('article1.md', u'tags: tag1,tag2\n\nstuff1')
        self.site.save_content('article2.md', u'tags: tag3,tag4\n\nstuff2')
        self.site.save_content('article3.md', u'tags: tag3,tag1\n\nstuff3')
        self.site.save_content('article4.md', u'tags: tag2,tag4\n\nstuff4')

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.walk()

        tagcountfile = self.abs_tagcount_file()
        self.assertTrue(os.path.exists(tagcountfile))
        taginfo = jsonpickle.decode(load_file(tagcountfile))
        tagcounts = taginfo.tagcounts
        self.assertEquals(2, tagcounts['tag1'])
        self.assertEquals(2, tagcounts['tag2'])
        self.assertEquals(2, tagcounts['tag3'])
        self.assertEquals(2, tagcounts['tag4'])

    def test_tag_urls_render_templates(self):
        template = generate_collection_template('info', 'article_infos', ['fullname'])
        self.site.save_template('article_list.html', template)
        self.site.save_content('article1.md', u'tags: tag1,tag2\n\nstuff1')
        self.site.save_content('article2.md', u'tags: tag3,tag4\n\nstuff2')
        self.site.save_content('article3.md', u'tags: tag3,tag1\n\nstuff3')
        self.site.save_content('article4.md', u'tags: tag2,tag4\n\nstuff4')

        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('article1', '', 'article1', 'md', datetime(2004, 11, 03) )
        info1.tags = 'tag1,tag2'
        info1.taglist = ['tag1','tag2']
        writer.add_document(fullname=u'article1', create_time=datetime(2004, 11, 04),
                            tags=u'tag1,tag2',
                            content=u'tags: tag1,tag2\n\nstuff1',
                            article_info_json=jsonpickle.encode(info1))

        info2 = ArticleInfo('article2', '', 'article2', 'md', datetime(2004, 11, 05))
        info2.tags = 'tag3,tag4'
        info2.taglist = ['tag3','tag4']
        writer.add_document(fullname=u'article2', create_time=datetime(2004, 11, 05), 
                            tags=u'tag3,tag4',
                            content=u'tags: tag3,tag4\n\nstuff2',
                            article_info_json=jsonpickle.encode(info2))

        info3 = ArticleInfo('article3', '', 'article3', 'md', datetime(2004, 11, 04))
        info3.tags = 'tag3,tag1'
        info3.taglist = ['tag3','tag1']
        writer.add_document(fullname=u'article3', create_time=datetime(2004, 11, 04), 
                            content=u'tags: tag3,tag1\n\nstuff3', 
                            tags=u'tag3,tag1',
                            article_info_json=jsonpickle.encode(info3))

        info4 = ArticleInfo('article4', '', 'article4', 'md', datetime(2004, 11, 02))
        info4.tags = 'tag2,tag4'
        info4.taglist = ['tag2','tag4']
        writer.add_document(fullname=u'article4', create_time=datetime(2004, 11, 02), 
                            tags=u'tag2,tag4',
                            content=u'tags: tag2,tag4\n\nstuff4',
                            article_info_json=jsonpickle.encode(info4))
        writer.commit()
        with self.app.test_client() as c: 
            rv = c.get('/tags/tag1/')
            assert 'article3' in rv.data
            assert 'article1' in rv.data
            assert 'article2' not in rv.data
            assert 'article4' not in rv.data

    def test_changed_files_adjust_tags(self):
        template = generate_collection_template('info', 'article_infos', ['fullname'])
        self.site.save_template('article_list.html', template)
        self.site.save_content('article1.md', u'tags: tag1,tag2\n\nstuff1')
        self.site.save_content('article2.md', u'tags: tag3,tag4\n\nstuff2')
        self.site.save_content('article3.md', u'tags: tag3,tag1\n\nstuff3')
        self.site.save_content('article4.md', u'tags: tag2,tag4\n\nstuff4')

        fields = self._schema()
        schema = Schema(**fields)
        idx = create_in(self.index_root(), schema = schema)
        writer = idx.writer()

        info1 = ArticleInfo('article1', '', 'article1', 'md', datetime(2004, 11, 03) )
        info1.tags = 'tag1,tag2'
        info1.taglist = ['tag1','tag2']
        writer.add_document(fullname=u'article1', create_time=datetime(2004, 11, 04),
                            tags=u'tag1,tag2',
                            content=u'tags: tag1,tag2\n\nstuff1',
                            article_info_json=jsonpickle.encode(info1))

        info2 = ArticleInfo('article2', '', 'article2', 'md', datetime(2004, 11, 05))
        info2.tags = 'tag3,tag4'
        info2.taglist = ['tag3','tag4']
        writer.add_document(fullname=u'article2', create_time=datetime(2004, 11, 05), 
                            tags=u'tag3,tag4',
                            content=u'tags: tag3,tag4\n\nstuff2',
                            article_info_json=jsonpickle.encode(info2))

        info3 = ArticleInfo('article3', '', 'article3', 'md', datetime(2004, 11, 04))
        info3.tags = 'tag3,tag1'
        info3.taglist = ['tag3','tag1']
        writer.add_document(fullname=u'article3', create_time=datetime(2004, 11, 04), 
                            content=u'tags: tag3,tag1\n\nstuff3', 
                            tags=u'tag3,tag1',
                            article_info_json=jsonpickle.encode(info3))

        info4 = ArticleInfo('article4', '', 'article4', 'md', datetime(2004, 11, 02))
        info4.tags = 'tag2,tag4'
        info4.taglist = ['tag2','tag4']
        writer.add_document(fullname=u'article4', create_time=datetime(2004, 11, 02), 
                            tags=u'tag2,tag4',
                            content=u'tags: tag2,tag4\n\nstuff4',
                            article_info_json=jsonpickle.encode(info4))
        writer.commit()

        # set up tag info file
        taginfo = TagInfo()
        taginfo.tagcounts = {'tag1': 2, 'tag2': 2, 'tag3': 2, 'tag4': 2}
        taginfo.name2tags = {'article1': ['tag1', 'tag2'], 
                             'article2': ['tag3', 'tag4'], 
                             'article3': ['tag3', 'tag1'], 
                             'article4': ['tag2', 'tag4'] }
        self.site.save_state_file(self.abs_tagcount_file(), jsonpickle.encode(taginfo))

        self.site.save_content('article1.md', u'tags: tag5\n\nstuff1')
        modified = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'article1.md')]
        
        self.site.save_content('article5.md', u'tags: tag2\n\nstuff5')
        added = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'article5.md')]

        self.site.remove_content('article3.md')
        removed = [os.path.join(self.app.config['YAWT_CONTENT_FOLDER'],'article3.md')]

        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.files_changed(modified, added, removed)

        tagcountfile = self.abs_tagcount_file()
        self.assertTrue(os.path.exists(tagcountfile))
        taginfo = jsonpickle.decode(load_file(tagcountfile))
        tagcounts = taginfo.tagcounts
        self.assertFalse('tag1' in tagcounts)
        self.assertEquals(2, tagcounts['tag2'])
        self.assertEquals(1, tagcounts['tag3'])
        self.assertEquals(2, tagcounts['tag4'])
        self.assertEquals(1, tagcounts['tag5'])

    def index_root(self):
        return self.app.config['WHOOSH_INDEX_ROOT']

    def _schema(self):
        fields = {}
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_INFO_FIELDS'])
        fields.update(self.app.config['YAWT_WHOOSH_ARTICLE_FIELDS'])
        fields['article_info_json'] = STORED
        fields['fullname'] = ID
        return fields

    def abs_tagcount_file(self):
        root = self.app.yawt_root_dir
        tagcountfile = self.app.config['YAWT_TAGGING_COUNT_FILE']
        state_folder = self.app.config['YAWT_STATE_FOLDER']
        return os.path.join(root, state_folder, tagcountfile)

    def tearDown(self):
        self.site.remove()
#        print self.site.site_root

def extension_info(plugin):
    from flask_whoosh import Whoosh
    whoosh = Whoosh()
    from yawtext.indexer import YawtWhoosh
    yawtwhoosh = YawtWhoosh()
    from yawtext.multimarkdown import YawtMarkdown
    yawtmarkdown = YawtMarkdown()
    from yawtext.collections import YawtPaging
    yawtpaging = YawtPaging()

    return ({'whoosh': whoosh,
             'yawtwhoosh': yawtwhoosh,
             'yawtpaging': yawtpaging,
             'yawttagging':plugin,
             'yawtmarkdown': yawtmarkdown},
            [whoosh, yawtwhoosh, yawtmarkdown, plugin],
            mk_init_app(whoosh, yawtwhoosh, yawtpaging, yawtmarkdown, plugin))

def mk_init_app(whoosh, yawtwhoosh, yawtpaging, yawtmarkdown, plugin):
    def init_app(app):
        whoosh.init_app(app)
        yawtwhoosh.init_app(app)
        yawtpaging.init_app(app)
        yawtmarkdown.init_app(app)
        plugin.init_app(app)
    return init_app
