import unittest
from mock import patch, Mock
import yawt
import os.path
from collections import namedtuple
from yawt.article import ArticleStore, MarkdownArticle
from yawt.test import fake_filesystem

from flask import Markup

class TestMarkdownArticleMetadata(unittest.TestCase):
    def _create_loader(self, meta, content):
        LoadedArticle = namedtuple('LoadedArticle', 'meta, content')
        loader = Mock()
        loader.load_article.return_value = LoadedArticle(meta, content)
        return loader

    def test_local_metadata_alone(self):
        article = MarkdownArticle(self._create_loader({'property1': ['bar']}, ""))
        self.assertEquals(article.get_metadata('property1'), 'bar')
        
    def test_external_metadata(self):
        article = MarkdownArticle(self._create_loader({}, ""), 
                                  external_meta = {'property1': 'bar'})
        self.assertEquals(article.get_metadata('property1'), 'bar')

    def test_vc_metadata(self):
        article = MarkdownArticle(self._create_loader({}, ""), 
                                  vc_meta = {'property1': 'bar'})
        self.assertEquals(article.get_metadata('property1'), 'bar')
      

    def test_file_metadata(self):
        article = MarkdownArticle(self._create_loader({}, ""), 
                                  file_meta = {'property1': 'bar'})
        self.assertEquals(article.get_metadata('property1'), 'bar')
        
    def test_local_metadata_overrides_external_metadata(self):
        article = MarkdownArticle(self._create_loader({'property1': ['foo'],
                                                       'property2':['hehe']}, ""),
                                  external_meta = {'property1': 'bar',
                                                   'property3': 'stuff'})
        self.assertEquals(article.get_metadata('property1'), 'foo')
        self.assertEquals(article.get_metadata('property2'), 'hehe')
        self.assertEquals(article.get_metadata('property3'), 'stuff')
        
    def test_external_metadata_overrides_vc_metadata(self):
        article = MarkdownArticle(self._create_loader({}, ""), 
                                  external_meta = {'property1': 'foo',
                                                     'property2':'hehe'},                  
                                  vc_meta = {'property1': 'bar',
                                             'property3': 'stuff'})
        self.assertEquals(article.get_metadata('property1'), 'foo')
        self.assertEquals(article.get_metadata('property2'), 'hehe')
        self.assertEquals(article.get_metadata('property3'), 'stuff')
        
    def test_vc_metadata_overrides_file_metadata(self):
        article = MarkdownArticle(self._create_loader({}, ""), 
                                  vc_meta = {'property1': 'foo',
                                             'property2':'hehe'},                  
                                  file_meta = {'property1': 'bar',
                                               'property3': 'stuff'})
        self.assertEquals(article.get_metadata('property1'), 'foo')
        self.assertEquals(article.get_metadata('property2'), 'hehe')
        self.assertEquals(article.get_metadata('property3'), 'stuff')
        
        
class TestArticleStore(unittest.TestCase):     
    def setUp(self):
        self.root_dir = '/root_dir'
        self.exts = ['txt','jpg']
        self.meta_ext = 'meta'
        self.vcstore = Mock()
        self.vcstore.fetch_vc_info.return_value = {'ctime': 0, 'mtime':0, 'author': 'dude'}
        self.store = ArticleStore( self.root_dir, self.exts, self.meta_ext, vcstore=self.vcstore)
        self._patch_os()
        
    def test_fetch_articles_by_category_no_results(self):
        articles = self.store.fetch_articles_by_category('category01')
        self.assertEquals(len(articles), 0)
     
    def test_fetch_articles_two_level_category(self):
        self._create_entry_file('entry01', mtime=0, contents='')
        self._create_entry_file('entry02', mtime=50, contents='')
        self._create_entry_file('cat01/entry03', mtime=30, contents='')
        self._create_entry_file('cat01/entry04', mtime=20, contents='')
        self._create_entry_file('cat01/entry05', mtime=90, contents='')
        self._create_entry_file('cat01/cat02/entry06', mtime=10, contents='')
        self._create_entry_file('cat01/cat02/entry07', mtime=100, contents='')
        self._create_entry_file('cat01/cat02/entry08', mtime=40, contents='')
        self._create_entry_file('cat03/entry09', mtime=70, contents='')
        self._create_entry_file('cat03/entry10', mtime=80, contents='')
        self._create_entry_file('cat03/entry11', mtime=60, contents='')

        vc_data = {'entry01': {'ctime': 0, 'mtime': 0, 'author': 'dude'},
                   'entry02': {'ctime':5, 'mtime':0, 'author': 'dude'},
                   'cat01/entry03': {'ctime':4, 'mtime':0, 'author': 'dude'},
                   'cat01/entry04': {'ctime':6, 'mtime': 0, 'author': 'dude'},
                   'cat01/entry05': {'ctime':10, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry06': {'ctime':3, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry07': {'ctime':8, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry08': {'ctime':7, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry09': {'ctime':2, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry10': {'ctime':9, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry11': {'ctime':1, 'mtime': 00, 'author': 'dude'}}           
        self._setup_vc_store(vc_data)
        
        articles = self.store.fetch_articles_by_category('')
        assert len(articles) == 11
        # entries are ordered by ctime, latest one first
        self._assert_article(articles[0], 'cat01/entry05', 'cat01', 'entry05')
        self._assert_article(articles[1], 'cat03/entry10', 'cat03', 'entry10')
        self._assert_article(articles[2], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[3], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[4], 'cat01/entry04', 'cat01', 'entry04')
        self._assert_article(articles[5], 'entry02', '', 'entry02')
        self._assert_article(articles[6], 'cat01/entry03', 'cat01', 'entry03')
        self._assert_article(articles[7], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')
        self._assert_article(articles[8], 'cat03/entry09', 'cat03', 'entry09')
        self._assert_article(articles[9], 'cat03/entry11', 'cat03', 'entry11')
        self._assert_article(articles[10], 'entry01', '', 'entry01')
        
        articles = self.store.fetch_articles_by_category('cat01') 
        assert len(articles) == 6
        self._assert_article(articles[0], 'cat01/entry05', 'cat01', 'entry05')
        self._assert_article(articles[1], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[2], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[3], 'cat01/entry04', 'cat01', 'entry04')
        self._assert_article(articles[4], 'cat01/entry03', 'cat01', 'entry03')
        self._assert_article(articles[5], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')
       
        articles = self.store.fetch_articles_by_category('cat01/cat02') 
        assert len(articles) == 3
        self._assert_article(articles[0], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[1], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[2], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')

    def test_fetch_articles_two_extensions(self):
        self._create_entry_file('entry01', mtime=0, contents='', ext='txt')
        self._create_entry_file('entry02', mtime=50, contents='', ext='txt')
        self._create_entry_file('cat01/entry03', mtime=30, contents='', ext='jpg')
        self._create_entry_file('cat01/entry04', mtime=20, contents='', ext='txt')
        self._create_entry_file('cat01/entry05', mtime=90, contents='', ext='jpg')
        self._create_entry_file('cat01/cat02/entry06', mtime=10, contents='', ext='jpg')
        self._create_entry_file('cat01/cat02/entry07', mtime=100, contents='', ext='jpg')
        self._create_entry_file('cat01/cat02/entry08', mtime=40, contents='', ext='txt')
        self._create_entry_file('cat03/entry09', mtime=70, contents='', ext='jpg')
        self._create_entry_file('cat03/entry10', mtime=80, contents='', ext='txt')
        self._create_entry_file('cat03/entry11', mtime=60, contents='', ext='txt')

        vc_data = {'entry01': {'ctime': 0, 'mtime': 0, 'author': 'dude'},
                   'entry02': {'ctime':5, 'mtime':0, 'author': 'dude'},
                   'cat01/entry03': {'ctime':4, 'mtime':0, 'author': 'dude'},
                   'cat01/entry04': {'ctime':6, 'mtime': 0, 'author': 'dude'},
                   'cat01/entry05': {'ctime':10, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry06': {'ctime':3, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry07': {'ctime':8, 'mtime': 00, 'author': 'dude'},
                   'cat01/cat02/entry08': {'ctime':7, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry09': {'ctime':2, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry10': {'ctime':9, 'mtime': 00, 'author': 'dude'},
                   'cat03/entry11': {'ctime':1, 'mtime': 00, 'author': 'dude'}}           
        self._setup_vc_store(vc_data)
        results = self.store.fetch_article_map_by_category('')
        self.assertEquals(2, len(results.keys()))

        articles = results['txt']
        self.assertEquals(6, len(articles))
        # entries are ordered by ctime, latest one first
        self._assert_article(articles[0], 'cat03/entry10', 'cat03', 'entry10')
        self._assert_article(articles[1], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[2], 'cat01/entry04', 'cat01', 'entry04')
        self._assert_article(articles[3], 'entry02', '', 'entry02')
        self._assert_article(articles[4], 'cat03/entry11', 'cat03', 'entry11')
        self._assert_article(articles[5], 'entry01', '', 'entry01')

        articles = results['jpg']
        self.assertEquals(5, len(articles))
        # entries are ordered by ctime, latest one first
        self._assert_article(articles[0], 'cat01/entry05', 'cat01', 'entry05')
        self._assert_article(articles[1], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[2], 'cat01/entry03', 'cat01', 'entry03')
        self._assert_article(articles[3], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')
        self._assert_article(articles[4], 'cat03/entry09', 'cat03', 'entry09')

    def test_fetch_article_by_category_and_slug(self):
        self._create_entry_file('cat01/entry03')
        article = self.store.fetch_article_by_category_slug('cat01', 'entry03')
        self._assert_article(article, 'cat01/entry03', 'cat01', 'entry03')
        
    def test_fetch_article_by_non_existent_category_and_slug(self):
        article = self.store.fetch_article_by_category_slug('cat01', 'entry03')
        assert article is None
                      
    def test_walk_articles(self):
        self._create_entry_file('entry01')
        self._create_entry_file('entry02')
        self._create_entry_file('cat01/entry03')
        self._create_entry_file('cat01/entry04')
        self._create_entry_file('cat01/entry05')
        self._create_entry_file('cat01/cat02/entry06')
        self._create_entry_file('cat01/cat02/entry07')
        self._create_entry_file('cat01/cat02/entry08')
        self._create_entry_file('cat03/entry09')
        self._create_entry_file('cat03/entry10')
        self._create_entry_file('cat03/entry11')
     
        # extraneous files that should be ignored
        self._fs.CreateFile('stupid01.png')
        self._fs.CreateFile('cat01/stupid02.png')
        self._fs.CreateFile('cat03/stupid03.png')

        names = [a for a in self.store.walk_articles()]
        # articles aren't guaranteed to be in any particular order
        assert 'cat01/cat02/entry06' in names
        assert 'cat01/cat02/entry07' in names
        assert 'cat01/cat02/entry08' in names
        assert 'entry01' in names
        assert 'entry02' in names
        assert 'cat01/entry03' in names
        assert 'cat01/entry04' in names
        assert 'cat01/entry05' in names
        assert 'cat03/entry09' in names
        assert 'cat03/entry10' in names
        assert 'cat03/entry11' in names
        # these should be ignored
        assert 'stupid01.png' not in names
        assert 'cat01/stupid02.png' not in names
        assert 'cat03/stupid03.png' not in names
        
    def test_fetch_non_existent_article_by_fullname(self):
        fullname = 'category01/category02/slug01'
        article = self.store.fetch_article_by_fullname(fullname)
        assert article is None
        
    def test_fetch_article_by_fullname_with_subcategory(self):
        fullname = 'category01/category02/slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01/category02', 'slug01')
        
    def test_fetch_article_by_fullname_with_category(self):
        fullname = 'category01/slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01', 'slug01')
        
    def test_fetch_article_by_fullname_at_root(self):
        fullname = 'slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, '', 'slug01')

    def test_article_exists(self):
        fullname = 'category01/category02/slug01'
        self._create_entry_file(fullname)
        assert self.store.article_exists(fullname)

    def test_article_does_not_exist(self):
        assert not self.store.article_exists('category01/category02/slug01')
                        
    def test_category_exists(self):
        fullname = 'category01/category02/slug01'
        self._create_entry_file(fullname)
        self.assertTrue(self.store.category_exists('category01/category02'))

    def test_category_does_not_exist(self):
        self.assertFalse(self.store.category_exists('category01/category02'))

    def test_load_article(self):
        self._create_entry_file('entry01', contents='Title: awesome title\n\nline 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.title, 'awesome title')
        self.assertEqual(article.content, Markup(u'<p>line 1\nline2\nstuff</p>'))

    def test_load_empty_article(self):
        self._create_entry_file('entry01', contents='')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.title, '')
        self.assertEqual(article.content, '')

    def test_load_article_no_title(self):
        self._create_entry_file('entry01', contents='line 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.title, '')
        self.assertEqual(article.content, Markup(u'<p>line 1\nline2\nstuff</p>'))

    def test_load_article_empty_title(self):
        self._create_entry_file('entry01', contents='\n\nline 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.title, '')
        self.assertEqual(article.content, Markup(u'<p>line 1\nline2\nstuff</p>'))

    def test_load_article_empty_content(self):
        self._create_entry_file('entry01', contents='Title: awesome title\n\n')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEquals(article.title, 'awesome title')
        self.assertEquals(article.content, '')
        
    def test_load_metadata(self):
        self._create_entry_file('entry01', contents='')
        self._fs.CreateFile(self._make_meta_filename('entry01'),
                               contents='prop1: stuff1\nprop2: stuff2')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertTrue(article.get_metadata('blah') is None)
        self.assertEquals(article.get_metadata('prop1'), 'stuff1')
        self.assertEquals(article.get_metadata('prop2'), 'stuff2')

    def test_metadata_times_override_disk_times(self):
        self._create_entry_file('entry01', mtime=1000, contents='')
        self._fs.CreateFile(self._make_meta_filename('entry01'),
                               contents='ctime: 300\nmtime: 500')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEquals(article.ctime, 300)
        self.assertEquals(article.mtime, 500)
    
    def tearDown(self):
        self._unpatch_os()
    
    def _setup_vc_store(self, vc_data):
        def vc_fetcher(fullname):
            return vc_data[fullname]
        self.vcstore.fetch_vc_info.side_effect = vc_fetcher
         
    def _patch_os(self):
        self._fs = fake_filesystem.FakeFilesystem()
        self._os = fake_filesystem.FakeOsModule(self._fs)
        self._os_patcher = patch('yawt.article.os', self._os)
        self._os_path_patcher = patch('yawt.article.os.path',self._os.path)
        self._open_patcher = patch('__builtin__.open', fake_filesystem.FakeFileOpen(self._fs))
        self._os_patcher.start() 
        self._os_path_patcher.start()
        self._open_patcher.start()

    def _unpatch_os(self):
        self._os_patcher.stop()
        self._os_path_patcher.stop()
        self._open_patcher.stop()
 
    def _create_entry_file(self, fullname, mtime=None, contents=None, ext=None):
        if ext is None:
            ext = self.exts[0]
        filename = self._make_filename(fullname, ext)
        self._fs.CreateFile(filename, contents=contents)
        if mtime is not None:
            self._os.utime(filename, (mtime, mtime))

    def _assert_article(self, article, fullname, category, slug):
        self.assertEquals(article.fullname, fullname)
        self.assertEquals(article.category, category)
        self.assertEquals(article.slug, slug)
    
    def _make_filename(self, fullname, ext):
        return os.path.join(self.root_dir, fullname + "." + ext)

    def _make_cat_folder(self, fullname):
        return os.path.join(self.root_dir, fullname)

    def _make_meta_filename(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.meta_ext)
    
if __name__ == '__main__':
    unittest.main()
