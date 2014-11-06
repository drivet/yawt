import os
from mercurial import hg, ui, cmdutil
from flask import current_app

def _config(key):
    return current_app.config[key]

class HgMetaPlugin(object):
    def init_app(self, app):
        app.config.setdefault('YAWT_HG_META_REPOPATH', '')
        app.config.setdefault('YAWT_HG_META_CONTENTPATH', '')
        app.config.setdefault('YAWT_HG_META_USE_UNCOMMITTED', False)

    def on_article_fetch(self, article):
        store = HgStore(_config('YAWT_HG_META_REPOPATH'),
                        _config('YAWT_HG_META_CONTENT_PATH'), 
                        _config('YAWT_HG_META_USE_UNCOMMITTED') )
        vc_info = store.fetch_vc_info(article.fullname, article.content_type)
        article.info.create_time = vc_info['create_time']
        article.info.modified_time = vc_info['modified_time']
        article.info.author = vc_info['author']
        return article


class HgStore(object):
    def __init__(self, repopath, contentpath, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.use_uncommitted = use_uncommitted
 
        self._revision_id = None
        self._revision = None # revision of an entire working directory, aka change ctx
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname, ext):
        self._init_repo()
        if self._repo is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + ext)
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesetcount = len(list(filelog))
        if changesetcount <= 0:
            return {}
        
        # at least one changeset
        first_changeset = self._repo[filelog.linkrev(0)]
        ctime = int(first_changeset.date()[0])
        author = first_changeset.user()
        
        last_changeset = self._repo[filelog.linkrev(changesetcount-1)]
        mtime = int(last_changeset.date()[0])
        return {'create_time': ctime, 'modified_time': mtime, 'author': author}

    def _init_repo(self):
        if not self._repo_initialized:
            self.repopath = cmdutil.findrepo(self.repopath)
            if self.repopath is not None:
                self._repo = hg.repository(ui.ui(), self.repopath)
                self._revision_id = self._get_revision_id()
                self._revision = self._repo[self._revision_id]
            self._repo_initialized = True
            
    def _get_revision_id(self):
        revision_id = None
        if not self.use_uncommitted:
            try:
                revision_id = self._repo.branchtags()['default']
            except KeyError:
                revision_id = None
        return revision_id
