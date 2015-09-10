from __future__ import absolute_import

import os

import datetime
import frontmatter
import yaml
from flask import current_app

from yawt.utils import save_file
from yawtext import Plugin


class ExplicitDumper(yaml.SafeDumper):
    """
    A dumper that will never emit aliases.
    """
    def ignore_aliases(self, data):
        return True


def _cfg(key):
    return current_app.config[key]


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _fix_dates_for_article(abs_article_file):
    post = frontmatter.load(abs_article_file)
    now = datetime.datetime.utcnow()
    if 'create_time' not in post.metadata:
        post['create_time'] = now
    post['modified_time'] = now
    save_file(abs_article_file, frontmatter.dumps(post, Dumper=ExplicitDumper))


def _fix_dates(root_dir, changed):
    """Add timestamps to files mentioned in the index"""
    changed = changed.content_changes()
    for changed_file in changed.added + changed.modified:
        _fix_dates_for_article(os.path.join(root_dir, changed_file))


class YawtAutodates(Plugin):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        super(YawtAutodates, self).__init__(app)

    def init_app(self, app):
        pass

    def on_pre_sync(self, root_dir, changed):
        """add create amd modifed dates to new files about to be synced"""
        _fix_dates(root_dir, changed)
