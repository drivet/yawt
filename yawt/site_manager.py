
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
 
    def save_draft(self, name, extension, content):
        self.site_manager.save_draft(name, extension, content)
        self._call_plugins('on_save_draft', name, extension, content)
 
    def save_article(self, fullname, extension, content):
        self.site_manager.save_article(fullname, extension, content)
        self._call_plugins('on_save_article', fullname, extension, content)
 
    def publish(self, draftname, fullname):
        self.site_manager.publish(draftname, fullname)
        self._call_plugins('on_publish', draftname, fullname)

    def move_draft(self, oldname, newname):
        self.site_manager.move_draft(oldname, newname)
        self._call_plugins('on_move_draft', oldname, newname)

    def move_article(self, oldname, newname):
        self.site_manager.move_article(oldname, newname)
        self._call_plugins('on_move_article', oldname, newname)

    def delete_draft(self, name):
        self.site_manager.delete_draft(name)
        self._call_plugins('on_delete_draft', name)

    def delete_article(self, name):
        self.site_manager.delete_article(name)
        self._call_plugins('on_delete_article', name)

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
