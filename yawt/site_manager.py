
class YawtSiteManager(object):
    """Wrapper around the file based site manager that knows about the plugins
    """
    def __init__(self, site_manager, plugin_manager):
        self.site_manager = site_manager
        self.plugin_manager = plugin_manager

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
        for plugin_pair in self._plugins():
            p = plugin_pair[1]
            if has_method(p, 'on_article_fetch'):
                article = p.on_article_fetch(article)
        return article

    def _on_new_site(self, files):
        for plugin_pair in self._plugins():
            p = plugin_pair[1]
            if has_method(p, 'on_new_site'):
                files = p.on_new_site(files)
        return files
        
    def _call_plugins(self, method, *args, **kw):
        for plugin_pair in self._plugins():
            p = plugin_pair[1]
            if has_method(p, method):
                getattr(p, method)(*args, **kw)

    def _plugins(self):
        return self.plugin_manager.plugins


def has_method(obj, method):
    return hasattr(obj, method) and callable(getattr(obj, method))
