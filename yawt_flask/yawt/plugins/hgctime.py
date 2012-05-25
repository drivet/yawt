from flask import g
from mercurial import hg, ui, cmdutil

class HgCtimeStore(object):
    def __init__(self, repopath, contentpath, ext):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        
        self._revision_id = None # uncommitted stuff
        self._repo_init = False
        self._revision = None
        self._repo = None
        
    def _init_repo(self):
        if self._repo_init == False:
            self.repopath = cmdutil.findrepo(self.repopath)
            if self.repopath is not None:
                self._repo = hg.repository(ui.ui(), self.repopath)
                # whole working directory I guess, since revision_id is None?
                self._revision = self._repo[self._revision_id]
            self._repo_init = True

    def _fetch_hg_info(self, fullname):
        self._init_repo()
        if self._repo is None:
            return None

        repofile = self.contentpath + '/' + fullname + '.' + self.ext
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesets = list(filelog)
        
        ctime = None
        author = None
        if len(changesets) > 0:
            # at least one changeset
            first_changeset = self._repo[filelog.linkrev(0)]
            ctime = int(first_changeset.date()[0])
            author = first_changeset.user()

        return (ctime, author)

    def get_ctime(self, fullname):
       ctime = None
       hg = self._fetch_hg_info(fullname)
       if hg is not None and hg[0] is not None:
           ctime = hg[0]
       return ctime

class HgCtimeArticle(object):
    """
    Article class decorator which override _ctime to be taken from
    the mercurial repository.
    """
    def __init__(self, article, hgstore):
        self._article = article
        self._hgstore = hgstore

    @property
    def _ctime(self):
        ct = self._hgstore.get_ctime(self._article.fullname)
        return ct or self._article._ctime
    
    def __getattr__(self, attrname):
        return getattr(self._article, attrname)
    
def init(app):
    global hgstore
    hgstore = HgCtimeStore(app.config['repopath'],
                           app.config['contentpath'],
                           app.config['ext'])

def on_article_fetch(article):
    global hgstore
    return HgCtimeArticle(article, hgstore)
