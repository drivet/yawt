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


# small comprimise for unit testing, this will be monkeypatched
def _now():
    return datetime.datetime.utcnow()


def _fix_dates_for_article(repofile):
    abs_article_file = os.path.join(current_app.yawt_root_dir, repofile)
    post = frontmatter.load(abs_article_file)
    now = _now()
    if 'create_time' not in post.metadata:
        post['create_time'] = now
    post['modified_time'] = now
    save_file(abs_article_file, frontmatter.dumps(post, Dumper=ExplicitDumper))


def _fix_dates(changed):
    """Add timestamps to files mentioned in the index"""
    changed = changed.content_changes()
    for changed_file in changed.added + changed.modified:
        _fix_dates_for_article(changed_file)


class YawtAutodates(Plugin):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        super(YawtAutodates, self).__init__(app)

    def init_app(self, app):
        pass

    def on_pre_sync(self, changed):
        """add create amd modifed dates to new files about to be synced"""
        _fix_dates(changed)
