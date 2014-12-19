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
        pass

    def on_new_site(self, files):
        save_repo_file('.gitignore', '_state')

    def on_article_fetch(self, article):
        vc_info = self.fetch_vc_info(article.info.fullname, article.info.extension)
        article.info.create_time = vc_info['create_time']
        article.info.modified_time = vc_info['modified_time'] 
        article.info.author = vc_info['author']
        return article

    def fetch_vc_info(self, fullname, ext):
        repofile = os.path.join(_config('YAWT_CONTENT_FOLDER'), fullname + '.' + ext)
        git_manager = current_app.extension_info[0]['git']
        rev_commit_gen = git_manager.commits_for_path_recent_last(repofile)
        first_commit = next(rev_commit_gen, None)
        if first_commit is None:
            return {}      
        sorted_commit_gen = git_manager.commits_for_path_recent_first(repofile)
        last_commit = next(sorted_commit_gen)

        return { 'create_time': first_commit.commit_time, 
                 'modified_time': last_commit.commit_time, 
                 'author': first_commit.author.name }

def save_repo_file(repofile, contents):
    path = os.path.join(current_app.yawt_root_dir, repofile)
    with open(path, 'w') as f:
        f.write(contents)
