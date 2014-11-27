from flask import current_app

class YawtSiteManager(object):
    """Wrapper around the file based site manager that knows about the plugins
    """
    def __init__(self, site_manager):
        self.site_manager = site_manager

    def new_site(self):
        files = self.site_manager.initialize()
        self._on_new_site(files)

    def fetch_article(self, fullname):
        article = self.site_manager.fetch_article_by_fullname(fullname)
        if article is None:
            return None
        return self._on_article_fetch(article)

    def walk(self):
        self._call_plugins('pre_walk')
        for fullname in self.site_manager.walk():
            article = self.fetch_article(fullname)
            self._call_plugins('visit_article', article)
        self._call_plugins('post_walk')

    def files_added(self, files):
        for f in files:
            self._call_plugins('on_file_add', f)
            if self.site_manager.is_article(f):
                article = self.site_manager.fetch_article_by_repofile(f)
                self._call_plugins('on_article_add', article)

    def files_modified(self, files):
        for f in files:
            self._call_plugins('on_file_modify', f)
            if self.site_manager.is_article(f):
                article = self.site_manager.fetch_article_by_repofile(f)
                self._call_plugins('on_article_modify', article)
 
    def files_deleted(self, files):
        for f in files:
            self._call_plugins('on_file_delete', f)
            if self.site_manager.is_article(f):
                article = self.site_manager.fetch_article_by_repofile(f)
                self._call_plugins('on_article_delete', article)
 
    def _on_article_fetch(self, article):
        for ext in self._extensions():
            if has_method(ext, 'on_article_fetch'):
                article = ext.on_article_fetch(article)
        return article

    def _on_new_site(self, files):
        for ext in self._extensions():
            if has_method(ext, 'on_new_site'):
                files = ext.on_new_site(files)
        return files
        
    def _call_plugins(self, method, *args, **kw):
        for ext in self._extensions():
            if has_method(ext, method):
                getattr(ext, method)(*args, **kw)

    def _extensions(self):
        if current_app.extension_info:
            return current_app.extension_info[1]
        else:
            return []


def has_method(obj, method):
    return hasattr(obj, method) and callable(getattr(obj, method))
