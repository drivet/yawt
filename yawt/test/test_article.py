#pylint: skip-file

import unittest
from yawt.article import FileBasedSiteManager, SiteExistsError
import os.path
import shutil
from yawt.test.siteutils import TempSite

class TestFileBasedArticleStoreInitialization(unittest.TestCase):
    def setUp(self):
        self.root_dir = '/tmp/root_dir'
        self.draft_folder = 'drafts'
        self.template_folder = 'templates'
        self.content_folder = 'content'
        self.extensions = ['html'] 
        self.meta_types = {}
        self.store = FileBasedSiteManager( root_dir = self.root_dir, 
                                           draft_folder = self.draft_folder,
                                           content_folder = self.content_folder, 
                                           template_folder = self.template_folder,
                                           file_extensions = self.extensions,
                                           meta_types = self.meta_types)

    def test_initialize_fails_if_root_folder_exists(self):
        os.mkdir(self.root_dir)
        self.assertRaises(SiteExistsError, self.store.initialize)

    def test_initialize_sets_up_site(self):
        self.store.initialize()
        assert os.path.exists(self.root_dir)
        assert os.path.exists(os.path.join(self.root_dir, self.template_folder))
        assert os.path.exists(os.path.join(self.root_dir, self.content_folder))
        assert os.path.exists(os.path.join(self.root_dir, 'config.py'))
        assert os.path.exists(os.path.join(self.root_dir, self.template_folder, 'article.html'))
        assert os.path.exists(os.path.join(self.root_dir, self.template_folder, '404.html'))

    def tearDown(self):
        assert self.root_dir.startswith('/tmp/')
        if os.path.exists(self.root_dir):
            shutil.rmtree(self.root_dir)


class TestFileBasedArticleStore(unittest.TestCase):
    def setUp(self):
        self.site = TempSite()
        self.site.initialize()

        self.extensions = ['html']
        self.meta_types = {}
        self.store = FileBasedSiteManager( root_dir = self.site.site_root, 
                                           draft_folder = self.site.draft_root,
                                           content_folder = self.site.content_root,
                                           template_folder = self.site.template_root,
                                           file_extensions = self.extensions,
                                           meta_types = self.meta_types)

    def test_fetch_article_by_fullname_loads_metadata(self):
        fullname = 'category01/slug01'
        self._create_content_file(fullname)
        article = self.store.fetch_article_by_fullname(fullname)
        self.assertEquals(article.info.stuff, 'foo')

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
        os.makedirs(os.path.join(self.site.site_root, 'cat01'))
        os.makedirs(os.path.join(self.site.site_root, 'cat03'))
        self.site.save_file('stupid01.png', 'blah')
        self.site.save_file('stupid01.png', 'blah')
        self.site.save_file('cat01/stupid02.png', 'blah')
        self.site.save_file('cat03/stupid03.png', 'blah')

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
        self.site.remove()

    def _create_content_file(self, fullname, mtime=None,
                             contents='---\nstuff: foo\n---\n\nblah',
                             ext=None):
        if ext is None:
            ext = self.extensions[0]
        self.site.mk_content_category(os.path.dirname(fullname))
        rel_filename = fullname + "." + ext
        self.site.save_content(rel_filename, content=contents)
        filename = os.path.join(self.site.abs_content_root(), rel_filename)
        if mtime is not None:
            os.utime(filename, (mtime, mtime))

    def _assert_article(self, article, fullname, category, slug):
        self.assertEquals(article.info.fullname, fullname)
        self.assertEquals(article.info.category, category)
        self.assertEquals(article.info.slug, slug)


if __name__ == '__main__':
    unittest.main()
