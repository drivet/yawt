from __future__ import absolute_import

import datetime
import os

from flask import g, current_app
from flask_script import Command, Option
import frontmatter


from yawtext.git import git_latest_changes, git_push, git_commit, \
    git_add_all, git_status

from yawt.git_hook_utils import extract_changed_files
from yawt.utils import call_plugins, save_file


GIT = '/usr/bin/git'


def _cfg(key):
    return current_app.config[key]


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _fix_dates_for_article(abs_article_file):
    post = frontmatter.load(abs_article_file)
    now = datetime.datetime.now()
    if 'md_create_time' not in post.metadata:
        post['md_create_time'] = now.isoformat()
    post['md_modified_time'] = now.isoformat()
    save_file(abs_article_file, frontmatter.dumps(post))


def _fix_dates(root_dir):
    out = git_status(root_dir)
    added_files, modified_files, deleted_files = extract_changed_files(out)
    for added in added_files:
        if added.startswith(_content_folder()):
            _fix_dates_for_article(os.path.join(root_dir, added))
    for modified in modified_files:
        if modified.startswith(_content_folder()):
            _fix_dates_for_article(os.path.join(modified))


def _sync(message, strict, nopush):
    root_dir = g.site.root_dir
    if not strict:
        git_add_all(root_dir)
        _fix_dates(root_dir)
        git_add_all(root_dir)
    git_commit(root_dir, message)
    if not nopush:
        git_push(root_dir)


class Sync(Command):
    """Sync command"""
    def __init__(self):
        super(Sync, self).__init__()

    def get_options(self):
        return [Option('--strict', '-s', action='store_true'),
                Option('--nopush', '-np', action='store_true'),
                Option('--message', '-m')]

    def run(self, strict, nopush, message):
        current_app.preprocess_request()

        if not message:
            message = 'synced changes'

        _sync(message, strict, nopush)
        added_files, modified_files, deleted_files = git_latest_changes()
        call_plugins('on_sync', added_files, modified_files, deleted_files)


class YawtSync(object):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pass

    def on_cli_init(self, manager):
        """add the command to the CLI manager"""
        manager.add_command('sync', Sync())
