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
        self._call_plugins('on_pre_walk')
        for fullname in self.site_manager.walk():
            article = self.fetch_article(fullname)
            self._call_plugins('on_visit_article', article)
        self._call_plugins('on_post_walk')

    def files_changed(self, files_modified, files_added, files_removed):
        self._call_plugins('on_files_changed', 
                           files_modified, 
                           files_added, 
                           files_removed)
 
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
