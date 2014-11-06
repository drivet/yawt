import unittest
#from mock import patch, Mock
from yawt.article import FileBasedSiteManager, ArticleExistsError, SiteExistsError
import os.path
from yawt.test.utils import FakeOs

class TestFileBasedArticleStore(unittest.TestCase):
    def setUp(self):
        self.root_dir = '/root_dir'
        self.draft_folder = 'drafts'
        self.template_folder = 'templates'
        self.content_folder = 'content'
        self.extensions = ['html']
        self.store = FileBasedSiteManager( root_dir = self.root_dir, 
                                           draft_folder = self.draft_folder,
                                           content_folder = self.content_folder, 
                                           template_folder = self.template_folder,
                                           file_extensions = self.extensions)
        self.fake_os = FakeOs('yawt.article')
        self.fake_os.start()
   
    def test_initialize_fails_if_root_folder_exists(self):
        self.fake_os.fs.CreateDirectory(self.root_dir)
        self.assertRaises(SiteExistsError, self.store.initialize)

    def test_initialize_sets_up_site(self):
        self.store.initialize()
        assert self.fake_os.fs.Exists(self.root_dir)
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, self.template_folder))
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, self.draft_folder))
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, self.content_folder))
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, 'config.py'))
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, self.template_folder, 'article.html'))
        assert self.fake_os.fs.Exists(os.path.join(self.root_dir, self.template_folder, '404.html'))

    def test_fetch_draft_by_name(self):
        name = 'slug01'
        self._create_draft_file(name)
        article = self.store.fetch_draft_by_name(name)
        self._assert_article(article, name, '', 'slug01')

    def test_fetch_article_by_category_and_slug(self):
        self._create_content_file('cat01/entry03')
        article = self.store.fetch_article_by_category_and_slug('cat01', 'entry03')
        self._assert_article(article, 'cat01/entry03', 'cat01', 'entry03')
        
    def test_fetch_article_by_non_existent_category_and_slug(self):
        article = self.store.fetch_article_by_category_and_slug('cat01', 'entry03')
        assert article is None

    def test_fetch_non_existent_article_by_fullname(self):
        fullname = 'category01/category02/slug01'
        article = self.store.fetch_article_by_fullname(fullname)
        assert article is None
        
    def test_fetch_article_by_fullname_with_subcategory(self):
        fullname = 'category01/category02/slug01'
        self._create_content_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01/category02', 'slug01')
        
    def test_fetch_article_by_fullname_with_category(self):
        fullname = 'category01/slug01'
        self._create_content_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, 'category01', 'slug01')
        
    def test_fetch_article_by_fullname_at_root(self):
        fullname = 'slug01'
        self._create_content_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, '', 'slug01')

    def test_article_exists(self):
        fullname = 'category01/category02/slug01'
        self._create_content_file(fullname)
        assert self.store.exists(fullname)

    def test_article_does_not_exist(self):
        assert not self.store.exists('category01/category02/slug01')

    def test_loaded_article_has_content_and_info(self):
        self._create_content_file('entry01', mtime=1000, contents='line 1\nline2\nstuff\n')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.info.fullname, 'entry01')
        self.assertEqual(article.info.category, '')
        self.assertEqual(article.info.slug, 'entry01')
        self.assertEqual(article.info.extension, 'html')
        self.assertEqual(article.info.create_time, 1000)
        self.assertEqual(article.info.modified_time, 1000)
        self.assertEqual(article.content, 'line 1\nline2\nstuff\n')

    def test_loaded_empty_article_has_no_content(self):
        self._create_content_file('entry01', contents='')
        article = self.store.fetch_article_by_fullname('entry01')
        self.assertEqual(article.content, '')

    def test_save_template(self):
        self._create_site_folder('templates')
        self.store.save_template('article', 'html', 'hello')
        assert 'hello' in self._read_site_file('templates/article.html')
 
    def test_save_draft(self):
        self._create_site_folder('drafts')
        self.store.save_draft('stuff', 'txt', 'blah')
        assert 'blah' in self._read_site_file('drafts/stuff.txt')

    def test_save_article(self):
        self._create_site_folder('content')
        self.store.save_article('stuff', 'txt', 'blah')
        assert 'blah' in self._read_site_file('content/stuff.txt')

    def test_move_article_fails_when_destination_exists(self):
        self._create_content_file('entry01')
        self._create_content_file('entry02')
        self.assertRaises(ArticleExistsError, self.store.move_article, 'entry01','entry02')

    def test_move_article(self):
        self._create_content_file('entry01', contents='stuff', ext='html')
        self.store.move_article('entry01','entry02')
        assert 'stuff' in self._read_site_file('content/entry02.html')
 
    def test_publish_fails_when_destination_exists(self):
        self._create_draft_file('entry01')
        self._create_content_file('entry02')
        self.assertRaises(ArticleExistsError, self.store.publish, 'entry01','entry02')

    def test_publish_article(self):
        self._create_site_folder('content')
        self._create_draft_file('entry01', contents='stuff', ext='html')
        self.store.publish('entry01', 'entry02')
        assert 'stuff' in self._read_site_file('content/entry02.html')

    def test_walk_articles(self):
        self._create_content_file('entry01')
        self._create_content_file('entry02')
        self._create_content_file('cat01/entry03')
        self._create_content_file('cat01/entry04')
        self._create_content_file('cat01/entry05')
        self._create_content_file('cat01/cat02/entry06')
        self._create_content_file('cat01/cat02/entry07')
        self._create_content_file('cat01/cat02/entry08')
        self._create_content_file('cat03/entry09')
        self._create_content_file('cat03/entry10')
        self._create_content_file('cat03/entry11')
     
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
   
    def _create_content_file(self, fullname, mtime=None, contents='blah', ext=None):
        if ext is None:
            ext = self.extensions[0]
        filename = self._make_content_filename(fullname, ext)
        self.fake_os.fs.CreateFile(filename, contents=contents)
        if mtime is not None:
            self.fake_os.os.utime(filename, (mtime, mtime))
  
    def _create_draft_file(self, fullname, mtime=None, contents='blah', ext=None):
        if ext is None:
            ext = self.extensions[0]
        filename = self._make_draft_filename(fullname, ext)
        self.fake_os.fs.CreateFile(filename, contents=contents)
        if mtime is not None:
            self.fake_os.os.utime(filename, (mtime, mtime))

    def _assert_article(self, article, fullname, category, slug):
        self.assertEquals(article.info.fullname, fullname)
        self.assertEquals(article.info.category, category)
        self.assertEquals(article.info.slug, slug)
    
    def _make_content_filename(self, fullname, ext):
        return os.path.join(self.root_dir, self.content_folder, fullname + "." + ext)

    def _make_draft_filename(self, name, ext):
        return os.path.join(self.root_dir, self.draft_folder, name + "." + ext)

    def _create_site_folder(self, path):
        return self.fake_os.fs.CreateDirectory(os.path.join(self.root_dir, path))
    
    def _read_site_file(self, path):
        with open(os.path.join(self.root_dir, path), 'r') as f:
            return f.read()
        
if __name__ == '__main__':
    unittest.main()
