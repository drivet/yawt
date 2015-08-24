from __future__ import absolute_import

import datetime
import os

from flask import g, current_app
from flask_script import Command, Option
import frontmatter


from yawtext.git import git_push, git_commit, \
    git_add, git_status, extract_indexed_status_files

from yawt.utils import save_file


GIT = '/usr/bin/git'


def _cfg(key):
    return current_app.config[key]


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _fix_dates_for_article(abs_article_file):
    post = frontmatter.load(abs_article_file)
    now = datetime.datetime.now()
    if 'md_create_time' not in post.metadata:
        post['md_create_time'] = now
    post['md_modified_time'] = now
    save_file(abs_article_file, frontmatter.dumps(post))


def _fix_dates(root_dir):
    """Add timestamps to files mentioned in the index"""
    changed = extract_indexed_status_files(git_status(root_dir))

    new_renames = []
    for old, new in changed.renamed.iteritems():
        old_not_content = not old.startswith(_content_folder())
        new_is_content = new.startswith(_content_folder())
        if old_not_content and new_is_content:
            new_renames.append(new)

    for changed_file in changed.added + changed.modified + new_renames:
        if changed_file.startswith(_content_folder()):
            _fix_dates_for_article(os.path.join(root_dir, changed_file))


def _sync(strict, addnew, push, message):
    root_dir = g.site.root_dir
    if not strict:
        # if addnew is True, this means we need to add all untracked files
        # to the index.  The -A will do that.  Otheriwse we just do a -u,
        # which will only update the tracked files.
        if addnew:
            git_add(root_dir, '-A')
        else:
            git_add(root_dir, '-u')

        # at this point we should have an almost snapshot of what we want
        # to commit in the index.  It's "almost" because we now may want
        # to fix up or add the timestamps.
        _fix_dates(root_dir)

        # readjust the index with the new timestamp changes
        git_add(root_dir, '-u')
    git_commit(root_dir, message)
    if push:
        git_push(root_dir)


class Sync(Command):
    """Sync command"""
    def __init__(self):
        super(Sync, self).__init__()

    def get_options(self):
        return [Option('--strict', '-s', action='store_true'),
                Option('--addnew', '-a', action='store_true'),
                Option('--push', '-p', action='store_true'),
                Option('--message', '-m')]

    def run(self, strict, addnew, push, message):
        current_app.preprocess_request()
        if not message:
            message = 'synced changes'
        _sync(strict, addnew, push, message)


class YawtSync(object):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_SYNC_DELAY', 2)

    def on_cli_init(self, manager):
        """add the command to the CLI manager"""
        manager.add_command('sync', Sync())
