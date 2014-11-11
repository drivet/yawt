import os
import pygit2
from flask_git import Git
from flask import current_app

def _config(key):
    return current_app.config[key]

class GitMetaPlugin(object):
    def __init__(self):
        self.git = None

    def init_app(self, app):
        app.config['GIT_REPOPATH'] = app.yawt_root_dir 
        self.git = Git(app)

    def on_article_fetch(self, article):
        vc_info = self.fetch_vc_info(article.fullname, article.content_type)
        article.info.create_time = vc_info['create_time']
        article.info.modified_time = vc_info['modified_time'] 
        article.info.author = vc_info['author']
        return article

    def fetch_vc_info(self, fullname, ext):
        contentpath = current_app.yawt_root_dir + _config('YAWT_CONTENT_FOLDER')
        repofile = os.path.join(contentpath, fullname + '.' + ext)

        rev_commit_gen = self.git.commits_for_path(repofile, pygit2.GIT_SORT_REVERSE)
        first_commit = next(rev_commit_gen, None)
        if first_commit is None:
            return {}        
        sorted_commit_gen = self.git.commits_for_path(repofile, pygit2.GIT_SORT_TIME)
        last_commit = next(sorted_commit_gen)

        return { 'create_time': first_commit.commit_time, 
                 'modified_time': last_commit.commit_time, 
                 'author': first_commit.author }

