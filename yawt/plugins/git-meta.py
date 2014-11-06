import os
import git
from flask import current_app

def _config(key):
    return current_app.config[key]

class GitMetaPlugin(object):
    def init_app(self, app):
        app.config.setdefault('YAWT_GIT_META_REPOPATH', '')
        app.config.setdefault('YAWT_GIT_META_CONTENTPATH', '')
        app.config.setdefault('YAWT_GIT_META_USE_UNCOMMITTED', False)

    def on_article_fetch(self, article):
        store = GitStore(_config('YAWT_GIT_META_REPOPATH'),
                         _config('YAWT_GIT_META_CONTENT_PATH'), 
                         _config('YAWT_GIT_META_USE_UNCOMMITTED') )
        vc_info = store.fetch_vc_info(article.fullname, article.content_type)
        article.info.create_time = vc_info['create_time']
        article.info.modified_time = vc_info['modified_time'] 
        article.info.author = vc_info['author']
        return article


class GitStore(object):
    def __init__(self, repopath, contentpath, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.use_uncommitted = use_uncommitted

        self._git = None
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname, ext):
        self._init_repo()
        if self._repo is None or self._git is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + ext)
        hexshas = self._git.log('--pretty=%H','--follow','--', repofile).split('\n') 
        commits = [self._repo.rev_parse(c) for c in hexshas]

        changesetcount = len(commits)
        if changesetcount <= 0:
            return {}

        # at least one changeset
        first_commit = commits[changesetcount-1]
        ctime = first_commit.committed_date
        author = first_commit.author

        last_commit = commits[0]
        mtime = last_commit.committed_date

        return {'create_time': ctime, 'modified_time': mtime, 'author': author}

    def _init_repo(self):
        if not self._repo_initialized:
            self._git = git.Git(self.repopath) 
            self._repo = git.Repo(self.repopath)
            self._repo_initialized = True
