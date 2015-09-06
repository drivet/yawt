"""The YAWT Git plugin which will dig into the repo to provide create_time,
modified_time and author information
"""
from __future__ import absolute_import

import os

from flask import current_app
from yawt.utils import is_content_file, save_file, cfg, EqMixin
from yawtext import Plugin


class ChangedFiles(EqMixin):
    """Structure to represent a summary of changed files in a git changeset"""
    def __init__(self, **kwargs):
        self.added = kwargs.get('added', [])
        self.modified = kwargs.get('modified', [])
        self.deleted = kwargs.get('deleted', [])
        self.renamed = kwargs.get('renamed', {})
        self._content_folder = kwargs.get('content_folder', None)

    def normalize(self):
        """Return a new ChangedFiles instance with the rename attribute merged
        into the added and deleted attributes"""
        added = list(self.added)
        modified = list(self.modified)
        deleted = list(self.deleted)
        for old, new in self.renamed.items():
            deleted.append(old)
            added.append(new)
        return ChangedFiles(added=added,
                            modified=modified,
                            deleted=deleted)

    def content_changes(self, content_folder=None):
        """Return a new ChangedFiles instance such that the non-content files
        are removed from the adde, modified and deleted attributes.  For the
        renamed attribute, we do the following:
        - remove all renames that are entirely non-content related
        - remove all renames with a non-content source and a content
          destination, and add the destinatuon to the added attribute.
        - keep the renames that are entire within the content folder.
        """
        added = [a for a in self.added if is_content_file(a, content_folder)]
        modified = [m for m in self.modified if is_content_file(m, content_folder)]
        deleted = [d for d in self.deleted if is_content_file(d, content_folder)]

        renamed = {}
        for old, new in self.renamed.items():
            old_is_content = is_content_file(old, content_folder)
            new_is_content = is_content_file(new, content_folder)
            if old_is_content and new_is_content:
                renamed[old] = new
            elif not old_is_content and new_is_content:
                added.append(new)
        return ChangedFiles(added=added,
                            modified=modified,
                            deleted=deleted,
                            renamed=renamed)


class YawtVersionControl(Plugin):
    """The YAWT version control plugin class"""

    def __init__(self, app=None):
        super(YawtVersionControl, self).__init__(app)
        self.meta = {}

    def init_app(self, app):
        app.config.setdefault('YAWT_VERSION_CONTROL_IFC', 'yawtext.git')
        app.config.setdefault('YAWT_VERSION_CONTROL_GIT_EXE', '/usr/bin/git')

    def on_new_site(self, files):
        """When a new site is created, we'll save a gitignore file so we can
        ignore the _state directory
        """
        filename = os.path.join(current_app.yawt_root_dir, vc_ignore_file())
        save_file(filename, '_state')


# VC API STARTS HERE

def post_merge(repo_path, app=None):
    """Run this as your post merge vc hook"""
    return _run_vc_func('post_merge', repo_path, app)


def post_commit(repo_path, app=None):
    """Run this as your post commit vc hook"""
    return _run_vc_func('post_commit', repo_path, app)


def vc_ignore_file():
    """Return ignore file for your vc"""
    return _run_vc_func('vc_ignore_file')


def vc_add_tracked():
    """add files to your repo"""
    return _run_vc_func('vc_add_tracked')


def vc_add_tracked_and_new():
    """add files to your repo"""
    return _run_vc_func('vc_add_tracked_and_new')


def vc_status():
    """get status of repo"""
    return _run_vc_func('vc_status')


def vc_commit(message):
    """Commit your repo"""
    return _run_vc_func('vc_commit', message)


def vc_push():
    """Push changesets to remote repo"""
    return _run_vc_func('vc_push')


def _run_vc_func(funcname, *args, **kwargs):
    temp = __import__(cfg('YAWT_VERSION_CONTROL_IFC'),
                      globals(), locals(), [funcname])
    return getattr(temp, funcname)(*args, **kwargs)
