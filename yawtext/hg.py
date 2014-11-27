import os
from flask import current_app

def _config(key):
    return current_app.config[key]

class YawtHg(object):
    def __init__(self, app):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pass

    def on_article_fetch(self, article):
        vc_info = self.fetch_vc_info(article.fullname, article.content_type)
        article.info.create_time = vc_info['create_time']
        article.info.modified_time = vc_info['modified_time']
        article.info.author = vc_info['author']
        return article

    def fetch_vc_info(self, fullname, ext): 
        contentpath = current_app.yawt_root_dir + _config('YAWT_CONTENT_FOLDER')
        repofile = os.path.join(contentpath, fullname + '.' + ext)

        commits = current_app.hg.commits_for_path(repofile)
        if len(commits) == 0:
            return {}
        first_commit = commits[-1]
        last_commit = commits[0]
        return { 'create_time': first_commit.date,
                 'modified_time': last_commit.date,
                 'author': first_commit.author}
