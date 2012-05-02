import unittest
import yawt
import os

class FakeFileSystem(object):
    def __init__(self):
        self._answers = {}

    def when(self, method, params, retval):
        if method not in self._answers:
            self._answers[method] = {}
        self._answers[method][params] = retval

    def fs_open(self, filename, mode):
        return self._answers['fs_open'][(filename, mode)]
   
    def fs_exists(self, path):
        return self._answers['fs_exists'][(path)]

    def fs_isfile(self, path):
        return self._answers['fs_isfile'][(path)]

    def fs_isdir(self, path):
        return self._answers['fs_isdir'][(path)]

    def fs_stat(self, path):
        return self._answers['fs_stat'][(path)]

    def fs_walk(self, path):
        return self._answers['fs_walk'][(path)]

    def fs_abspath(self, path):
        return self._answers['fs_abspath'][(path)]

class FakeAnything(object):
    pass

class TestArticleStore(unittest.TestCase):     
    def setUp(self):
        self.root_dir = 'root_dir'
        self.ext = 'txt'
        self.meta_ext = 'meta'
        self.plugins = {}
        self.fs = FakeFileSystem()
        self.store = yawt.ArticleStore(self.fs, self.plugins, self.root_dir,
                                       self.ext, self.meta_ext)
    
    def test_fetch_non_existent_article_by_fullname(self):
        fullname = 'category01/category02/slug01'
        self.fs.when('fs_exists', self._make_filename(fullname), False)
        article = self.store.fetch_article_by_fullname(fullname)
        assert article is None
        
    def test_fetch_article_by_fullname_with_subcategory(self):
        fullname = 'category01/category02/slug01'
        mtime = 100
        self.fs.when('fs_exists', self._make_filename(fullname), True)
        self.fs.when('fs_stat', self._make_filename(fullname), self._make_stat_retval(mtime))
        self.fs.when('fs_isfile', self._make_meta_filename(fullname), False)
        
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, mtime, 'category01/category02', 'slug01')
        
    def test_fetch_article_by_fullname_with_category(self):
        fullname = 'category01/slug01'
        mtime = 100
        self.fs.when('fs_exists', self._make_filename(fullname), True)
        self.fs.when('fs_stat', self._make_filename(fullname), self._make_stat_retval(mtime))
        self.fs.when('fs_isfile', self._make_meta_filename(fullname), False)
        
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, mtime, 'category01', 'slug01')
        
    def test_fetch_article_by_fullname_at_root(self):
        fullname = 'slug01'
        mtime = 100
        self.fs.when('fs_exists', self._make_filename(fullname), True)
        self.fs.when('fs_stat', self._make_filename(fullname), self._make_stat_retval(mtime))
        self.fs.when('fs_isfile', self._make_meta_filename(fullname), False)
        
        article = self.store.fetch_article_by_fullname(fullname)
        self._assert_article(article, fullname, mtime, '', 'slug01')

    def test_article_exists(self):
        fullname = 'category01/category02/slug01'
        self.fs.when('fs_isfile', self._make_filename(fullname), True)
        assert self.store.article_exists(fullname)
        self.fs.when('fs_isfile', self._make_filename(fullname), False)
        assert not self.store.article_exists(fullname)

    def test_category_exists(self):
        fullname = 'category01/category02'
        self.fs.when('fs_isdir', self._make_cat_folder(fullname), True)
        assert self.store.category_exists(fullname)
        self.fs.when('fs_isdir', self._make_cat_folder(fullname), False)
        assert not self.store.category_exists(fullname)
        
    def _assert_article(self, article, fullname, mtime, category, slug):
        assert article.fullname == fullname
        assert article.mtime == mtime
        assert article.ctime == mtime
        assert article.category == category
        assert article.slug == slug
    
    def _make_filename(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.ext)

    def _make_cat_folder(self, fullname):
        return os.path.join(self.root_dir, fullname)

    def _make_meta_filename(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.meta_ext)

    def _make_stat_retval(self, mtime):
        stat_retval = FakeAnything()
        stat_retval.st_mtime = mtime
        return stat_retval
    
if __name__ == '__main__':
    unittest.main()
