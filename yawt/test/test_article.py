import unittest
#from mock import patch, Mock
from yawt.article2 import FileBasedArticleStore
import os.path
from yawt.test.utils import FakeOs

class TestFileBasedArticleStore(unittest.TestCase):
    def setUp(self):
        self.root_dir = '/root_dir'
        self.extensions = ['html']
        self.store = FileBasedArticleStore( root_dir = self.root_dir, 
                                            extensions = self.extensions)
        self.fake_os = FakeOs('yawt.article')
        self.fake_os.start()
   
    def test_fetch_article_by_category_and_slug(self):
        self._create_entry_file('cat01/entry03')
        article = self.store.fetch_by_category_and_slug('cat01', 'entry03')
        self._assert_article(article, 'cat01/entry03', 'cat01', 'entry03')
        
    def test_fetch_article_by_non_existent_category_and_slug(self):
        article = self.store.fetch_by_category_and_slug('cat01', 'entry03')
        assert article is None

    def test_fetch_non_existent_article_by_fullname(self):
        fullname = 'category01/category02/slug01'
        article = self.store.fetch_by_fullname(fullname)
        assert article is None
        
    def test_fetch_article_by_fullname_with_subcategory(self):
        fullname = 'category01/category02/slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01/category02', 'slug01')
        
    def test_fetch_article_by_fullname_with_category(self):
        fullname = 'category01/slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01', 'slug01')
        
    def test_fetch_article_by_fullname_at_root(self):
        fullname = 'slug01'
        self._create_entry_file(fullname)
        article = self.store.fetch_by_fullname(fullname)
        self._assert_article(article, fullname, '', 'slug01')

    def test_article_exists(self):
        fullname = 'category01/category02/slug01'
        self._create_entry_file(fullname)
        assert self.store.exists(fullname)

    def test_article_does_not_exist(self):
        assert not self.store.exists('category01/category02/slug01')

    def test_loaded_article_has_content_and_info(self):
        self._create_entry_file('entry01', mtime=1000, contents='line 1\nline2\nstuff\n')
        article = self.store.fetch_by_fullname('entry01')
        self.assertEqual(article.info.fullname, 'entry01')
        self.assertEqual(article.info.category, '')
        self.assertEqual(article.info.slug, 'entry01')
        self.assertEqual(article.info.extension, 'html')
        self.assertEqual(article.info.create_time, 1000)
        self.assertEqual(article.info.modified_time, 1000)
        self.assertEqual(article.content, 'line 1\nline2\nstuff\n')

    def test_loaded_empty_article_has_no_content(self):
        self._create_entry_file('entry01', contents='')
        article = self.store.fetch_by_fullname('entry01')
        self.assertEqual(article.content, '')

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
        self.fake_os.fs.CreateFile('stupid01.png')
        self.fake_os.fs.CreateFile('cat01/stupid02.png')
        self.fake_os.fs.CreateFile('cat03/stupid03.png')

        names = [a for a in self.store.walk()]
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

    def tearDown(self):
        self.fake_os.stop()
   
    def _create_entry_file(self, fullname, mtime=None, contents='blah', ext=None):
        if ext is None:
            ext = self.extensions[0]
        filename = self._make_filename(fullname, ext)
        self.fake_os.fs.CreateFile(filename, contents=contents)
        if mtime is not None:
            self.fake_os.os.utime(filename, (mtime, mtime))

    def _assert_article(self, article, fullname, category, slug):
        self.assertEquals(article.info.fullname, fullname)
        self.assertEquals(article.info.category, category)
        self.assertEquals(article.info.slug, slug)
    
    def _make_filename(self, fullname, ext):
        return os.path.join(self.root_dir, fullname + "." + ext)

    def _make_cat_folder(self, fullname):
        return os.path.join(self.root_dir, fullname)
        
if __name__ == '__main__':
    unittest.main()
