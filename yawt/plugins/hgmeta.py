import os.path
from flask import g
from mercurial import hg, ui, cmdutil

class HgStore(object):
    def __init__(self, repopath, contentpath, ext, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        self.use_uncommitted = use_uncommitted
        
        self._revision_id = None
        self._revision = None # particular revision of a working directory
        self._repo = None

    def _get_revision_id(self):
        revision_id = None
        if self.use_uncommitted:
            try:
                revision_id = self._repo.branchtags()['default']
            except KeyError:
                revision_id = None
    
    def _init_repo(self):
        self.repopath = cmdutil.findrepo(self.repopath)
        if self.repopath is not None:
            self._repo = hg.repository(ui.ui(), self.repopath)
            self._revision_id = self._get_revision_id()
            self._revision = self._repo[self._revision_id]
            
    def fetch_hg_info(self, fullname):
        self._init_repo()
        if self._repo is None:
            return None

        repofile = os.path.join(self.contentpath, fullname + '.' + self.ext)
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesets = list(filelog)
        
        ctime = None
        author = None
        mtime = None
        if len(changesets) > 0:
            # at least one changeset
            first_changeset = self._repo[filelog.linkrev(0)]
            ctime = int(first_changeset.date()[0])
            author = first_changeset.user()
            
            last_changeset = self._repo[filelog.linkrev(len(changesets)-1)]
            mtime = int(last_changeset.date()[0])
            
        return (ctime, mtime, author)

class HgMetaPlugin(object):
    def __init__(self):
        self.default_config = {
            'use_uncommitted': True
        }
        
    def init(self, app, modname):
        self.app = app
        self.name = modname
        self.hgstore = HgStore(app.config['blogpath'],
                               app.config['path_to_articles'],
                               app.config['ext'],
                               app.config[self.name]['use_uncommitted'])

        self._load_config()
    
    def on_article_fetch(self, article):
        (ctime, mtime, author) = self.hgstore.fetch_hg_info(article.fullname)
        article._ctime = ctime or article._ctime
        article._mtime = mtime or article._mtime
        return article

    def _plugin_config(self):
        return self.app.config[__name__]
        
    def _load_config(self):
        if __name__ not in self.app.config:
            self.app.config[__name__] = {}
        self.app.config[__name__].update(self.default_config)
 
def create_plugin():
    return HgMetaPlugin()
