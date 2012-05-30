import os.path
from flask import g
from mercurial import hg, ui, cmdutil

flask_app = None

default_config = {
    'use_uncommitted': True
}

class HgStore(object):
    def __init__(self, repopath, contentpath, ext):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        
        self._revision_id = None
        self._repo_init = False
        self._revision = None # particular revision of a working directory
        self._repo = None

    def _get_revision_id(self):
        revision_id = None
        if _plugin_config()['use_uncommitted']:
            try:
                revision_id = self._repo.branchtags()['default']
            except KeyError:
                revision_id = None
    
    def _init_repo(self):
        if self._repo_init == False:
            self.repopath = cmdutil.findrepo(self.repopath)
            if self.repopath is not None:
                self._repo = hg.repository(ui.ui(), self.repopath)
                self._revision_id = self._get_revision_id()
                self._revision = self._repo[self._revision_id]
            self._repo_init = True

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
    
def init(app):
    global hgstore
    hgstore = HgStore(app.config['blogpath'],
                      app.config['path_to_articles'],
                      app.config['ext'])
    global flask_app
    flask_app = app

    _load_config()
    
def on_article_fetch(article):
    global hgstore
    (ctime, mtime, author) = hgstore.fetch_hg_info(article.fullname)
    article._ctime = ctime or article._ctime
    article._mtime = mtime or article._mtime
    return article

def _plugin_config():
    return flask_app.config[__name__]

def _load_config():
    if __name__ not in flask_app.config:
        flask_app.config[__name__] = {}
    flask_app.config[__name__].update(default_config)
