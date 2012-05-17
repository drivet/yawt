import unittest
import yawt
import os.path
from yawt.article import ArticleStore
from yawt.test import fake_filesystem

class FakeFS(object):
    def __init__(self):
        self._fs = fake_filesystem.FakeFilesystem()
        self._os = fake_filesystem.FakeOsModule(self._fs)
        
    def open(self, filename, mode):
        return fake_filesystem.FakeFileOpen(self._fs)(filename, mode)
    
    def exists(self, path):
        return self._os.path.exists(path)

    def isfile(self, path):
        return self._os.path.isfile(path)
    
    def isdir(self, path):
        return self._os.path.isdir(path)
    
    def stat(self, path):
        return self._os.stat(path)
    
    def walk(self, path):
        return self._os.walk(path)
    
    def abspath(self, path):
        return self._os.path.abspath(path)


class TestArticleStore(unittest.TestCase):     
    def setUp(self):
        self.root_dir = '/root_dir'
        self.ext = 'txt'
        self.meta_ext = 'meta'
        self.plugins = yawt.util.Plugins({})
        self.fs = FakeFS()
        self.store = ArticleStore(self.fs, self.plugins, self.root_dir,
                                  self.ext, self.meta_ext)

    def test_fetch_articles_by_category_no_results(self):
        articles = self.store.fetch_articles_by_category('category01')
        assert len(articles) == 0
     
    def test_fetch_articles_two_level_category(self):
        self._create_entry_file('entry01', mtime=0)
        self._create_entry_file('entry02', mtime=50)
        self._create_entry_file('cat01/entry03', mtime=30)
        self._create_entry_file('cat01/entry04', mtime=20)
        self._create_entry_file('cat01/entry05', mtime=90)
        self._create_entry_file('cat01/cat02/entry06', mtime=10)
        self._create_entry_file('cat01/cat02/entry07', mtime=100)
        self._create_entry_file('cat01/cat02/entry08', mtime=40)
        self._create_entry_file('cat03/entry09', mtime=70)
        self._create_entry_file('cat03/entry10', mtime=80)
        self._create_entry_file('cat03/entry11', mtime=60)
        
        articles = self.store.fetch_articles_by_category('')
        assert len(articles) == 11
        # entries are ordered by mtime
        self._assert_article(articles[0], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[1], 'cat01/entry05', 'cat01', 'entry05')
        self._assert_article(articles[2], 'cat03/entry10', 'cat03', 'entry10')
        self._assert_article(articles[3], 'cat03/entry09', 'cat03', 'entry09')
        self._assert_article(articles[4], 'cat03/entry11', 'cat03', 'entry11')
        self._assert_article(articles[5], 'entry02', '', 'entry02')
        self._assert_article(articles[6], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[7], 'cat01/entry03', 'cat01', 'entry03')
        self._assert_article(articles[8], 'cat01/entry04', 'cat01', 'entry04')
        self._assert_article(articles[9], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')
        self._assert_article(articles[10], 'entry01', '', 'entry01')
        
        articles = self.store.fetch_articles_by_category('cat01')
        assert len(articles) == 6
        self._assert_article(articles[0], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[1], 'cat01/entry05', 'cat01', 'entry05')
        self._assert_article(articles[2], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[3], 'cat01/entry03', 'cat01', 'entry03')
        self._assert_article(articles[4], 'cat01/entry04', 'cat01', 'entry04')
        self._assert_article(articles[5], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')
       
        articles = self.store.fetch_articles_by_category('cat01/cat02')
        assert len(articles) == 3
        self._assert_article(articles[0], 'cat01/cat02/entry07', 'cat01/cat02', 'entry07')
        self._assert_article(articles[1], 'cat01/cat02/entry08', 'cat01/cat02', 'entry08')
        self._assert_article(articles[2], 'cat01/cat02/entry06', 'cat01/cat02', 'entry06')

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
        self.fs._fs.CreateFile('stupid01.png')
        self.fs._fs.CreateFile('cat01/stupid02.png')
        self.fs._fs.CreateFile('cat03/stupid03.png')

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
        self._create_entry_file('entry01', contents='  awesome title  \n\nline 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        article_content = self.store.load_article(article)
        self.assertEqual(article_content.title, 'awesome title')
        self.assertEqual(article_content.content, 'line 1\nline2\nstuff\n')

    def test_load_empty_article(self):
        self._create_entry_file('entry01', contents='')
        article = self.store.fetch_article_by_fullname('entry01')
        article_content = self.store.load_article(article)
        assert article_content.title == ''
        assert article_content.content == ''

    def test_load_article_no_title(self):
        self._create_entry_file('entry01', contents='line 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        article_content = self.store.load_article(article)
        assert article_content.title == ''
        assert article_content.content == 'line 1\nline2\nstuff\n'

    def test_load_article_empty_title(self):
        self._create_entry_file('entry01', contents='\n\nline 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        article_content = self.store.load_article(article)
        assert article_content.title == ''
        assert article_content.content == 'line 1\nline2\nstuff\n'

    def test_load_article_empty_content(self):
        self._create_entry_file('entry01', contents='awesome title\n\n')
        article = self.store.fetch_article_by_fullname('entry01')
        article_content = self.store.load_article(article)
        assert article_content.title == 'awesome title'
        assert article_content.content == ''
        
    def test_load_metadata(self):
        self._create_entry_file('entry01')
        self.fs._fs.CreateFile(self._make_meta_filename('entry01'),
                               contents='prop1: stuff1\nprop2: stuff2')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertTrue(article.get_metadata('blah') is None)
        self.assertEquals(article.get_metadata('prop1'), 'stuff1')
        self.assertEquals(article.get_metadata('prop2'), 'stuff2')

    def test_mtime_is_ctime(self):
        self._create_entry_file('entry01', mtime=1000)
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEquals(article.ctime, 1000)
        self.assertEquals(article.mtime, 1000)
    
    def test_metadata_times_override_disk_times(self):
        self._create_entry_file('entry01', mtime=1000)
        self.fs._fs.CreateFile(self._make_meta_filename('entry01'),
                               contents='ctime: 300\nmtime: 500')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEquals(article.ctime, 300)
        self.assertEquals(article.mtime, 500)
               
    def _create_entry_file(self, fullname, mtime=None, contents=None):
        filename = self._make_filename(fullname)
        self.fs._fs.CreateFile(filename, contents=contents)
        if mtime is not None:
            self.fs._os.utime(filename, (mtime, mtime))

    def _assert_article(self, article, fullname, category, slug):
        assert article.fullname == fullname
        assert article.category == category
        assert article.slug == slug
    
    def _make_filename(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.ext)

    def _make_cat_folder(self, fullname):
        return os.path.join(self.root_dir, fullname)

    def _make_meta_filename(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.meta_ext)
    
if __name__ == '__main__':
    unittest.main()
