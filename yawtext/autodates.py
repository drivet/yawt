from __future__ import absolute_import

import datetime
import os

import yaml
from flask import current_app
import frontmatter
from yawt.utils import save_file, find_new_renames
from yawtext.base import Plugin


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
    if 'md_create_time' not in post.metadata:
        post['md_create_time'] = now
    post['md_modified_time'] = now
    save_file(abs_article_file, frontmatter.dumps(post, Dumper=ExplicitDumper))


def _fix_dates(root_dir, changed):
    """Add timestamps to files mentioned in the index"""
    files = changed.added + changed.modified + find_new_renames(changed.renamed)
    for changed_file in files:
        if changed_file.startswith(_content_folder()):
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
