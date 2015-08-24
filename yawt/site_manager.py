"""Code to wrap around an article store, to provide hooks for plugins"""

from __future__ import absolute_import


from yawt.utils import has_method, extensions, call_plugins


class YawtSiteManager(object):
    """Wrapper around the file based site manager that knows about the plugins
    """
    def __init__(self, site_manager):
        self.site_manager = site_manager

    @property
    def root_dir(self):
        """Return the root directory of the website"""
        return self.site_manager.root_dir

    def new_site(self):
        """Creates a new site, calling all the plugins"""
        files = self.site_manager.initialize()
        self._on_new_site(files)

    def fetch_article(self, fullname):
        """Fetches an article, calling all the plugins"""
        article = self.site_manager.fetch_article_by_fullname(fullname)
        if article is None:
            return None
        return self._on_article_fetch(article)

    def fetch_article_by_info(self, article_info):
        """Fetches an article, calling all the plugins"""
        article = self.site_manager.fetch_article_by_fullname(article_info.fullname)
        if article is None:
            return None
        article.info = article_info
        return self._on_article_fetch(article)

    def fetch_article_by_repofile(self, repofile):
        """Fetches an article, calling all the plugins"""
        article = self.site_manager.fetch_article_by_repofile(repofile)
        if article is None:
            return None
        return self._on_article_fetch(article)

    def walk(self):
        """Perform a walk (i.e. visit each article in the store) and run the
        plugins to process the articles.
        """
        call_plugins('on_pre_walk')
        for fullname in self.site_manager.walk():
            article = self.fetch_article(fullname)
            call_plugins('on_visit_article', article)
        call_plugins('on_post_walk')

    def _on_article_fetch(self, article):
        for ext in extensions():
            if has_method(ext, 'on_article_fetch'):
                article = ext.on_article_fetch(article)
        return article

    def _on_new_site(self, files):
        for ext in extensions():
            if has_method(ext, 'on_new_site'):
                files = ext.on_new_site(files)
        return files
