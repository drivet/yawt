import os
from flask import current_app

def _config(key):
    return current_app.config[key]

class YawtGit(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_GIT_FOLLOW_RENAMES', False)

    def on_new_site(self, files):
        save_repo_file('.gitignore', '_state')

    def on_article_fetch(self, article):
        vc_info = self.fetch_vc_info(article.info.fullname, article.info.extension)
        if 'create_time' in vc_info:
            article.info.git_create_time = vc_info['create_time']
        if 'modified_time' in vc_info:
            article.info.git_modified_time = vc_info['modified_time'] 
        if 'author' in vc_info:
            article.info.git_author = vc_info['author']
        return article

    def fetch_vc_info(self, fullname, ext):
        repofile = os.path.join(_config('YAWT_CONTENT_FOLDER'), fullname + '.' + ext)
        git_manager = current_app.extension_info[0]['flask_git.Git']

        follow = _config('YAWT_GIT_FOLLOW_RENAMES')
        sorted_commits = list(git_manager.commits_for_path_recent_first(repofile, follow=follow))
        if len(sorted_commits) == 0:
            return {}
            
        last_commit = sorted_commits[0]
        first_commit = sorted_commits[-1]
        return { 'create_time': first_commit.commit_time, 
                 'modified_time': last_commit.commit_time, 
                 'author': first_commit.author.name }

def save_repo_file(repofile, contents):
    path = os.path.join(current_app.yawt_root_dir, repofile)
    with open(path, 'w') as f:
        f.write(contents)
