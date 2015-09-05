"""The YAWT Git plugin which will dig into the repo to provide create_time,
modified_time and author information
"""
from __future__ import absolute_import

import os
import subprocess
import sys

from flask import current_app, g
from yawt.utils import content_folder, is_content_file, run_in_context,\
    call_plugins, EqMixin
from yawtext import Plugin

GIT = '/usr/bin/git'


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


def _abs_filename(fullname, ext):
    root_dir = g.site.root_dir
    abs_path = os.path.join(root_dir, content_folder(), fullname + '.' + ext)
    return abs_path


def _save_repo_file(repofile, contents):
    path = os.path.join(current_app.yawt_root_dir, repofile)
    with open(path, 'w') as f:
        f.write(contents)


def _git_cmd(root_dir, args):
    git_dir = root_dir + '/.git'
    return [GIT, '--git-dir='+git_dir,
            '--work-tree='+root_dir] + args


def post_merge(repo_path):
    """Entry point for a vc merge operation"""
    diff_tree_out = git_diff_tree(GIT, repo_path, 'ORIG_HEAD', 'HEAD')
    changed = extract_diff_tree_files(diff_tree_out)
    run_in_context(repo_path, call_plugins, 'on_files_changed', changed)


def post_commit(repo_path):
    """Entry point for a vc commit operation"""
    diff_tree_out = git_diff_tree(GIT, repo_path, 'HEAD')
    changed = extract_diff_tree_files(diff_tree_out)
    run_in_context(repo_path, call_plugins, 'on_files_changed', changed)


def extract_diff_tree_files(diff_tree_out):
    """Given git diff tree output, return the list of added, modied and
    removed files."""
    added_files = []
    modified_files = []
    deleted_files = []
    renamed_files = {}
    for line in diff_tree_out.split('\n'):
        if not line:
            break
        (status, rest) = line.split(None, 1)
        if status == 'A':
            added_files.append(rest)
        elif status == 'M':
            modified_files.append(rest)
        elif status == 'D':
            deleted_files.append(rest)
        elif status.startswith('R'):
            (old, new) = rest.split()
            renamed_files[old] = new
        else:
            print "unknown git status: " + status
    changed = ChangedFiles(added=added_files,
                           modified=modified_files,
                           deleted=deleted_files,
                           renamed=renamed_files)
    return changed


def extract_indexed_status_files(status_out):
    """Given git status output, return the list of added, modified and removed
    files.  Note that files MUST have been added to the index.
    """
    added_files = []
    modified_files = []
    deleted_files = []
    renamed_files = {}
    for line in status_out.split('\n'):
        if not line:
            break
        (status, rest) = line.split(None, 1)
        if status == 'A':
            added_files.append(rest)
        elif status == 'M':
            modified_files.append(rest)
        elif status == 'D':
            deleted_files.append(rest)
        elif status == 'R':
            (old, new) = rest.split(' -> ')
            renamed_files[old] = new
        else:
            print "Skipping unknown status: "+status
    changed = ChangedFiles(added=added_files,
                           modified=modified_files,
                           deleted=deleted_files,
                           renamed=renamed_files)
    return changed


def git_diff_tree(git, repo_path, tree1, tree2=None):
    """Execute a git diff-tree and return the output"""
    try:
        cmd = ['sudo', '-u', 'www-data', '-H',
               git, '--git-dir=' + repo_path + '/.git',
               '--work-tree=' + repo_path,
               'diff-tree', '-r', '--name-status', '--no-commit-id',
               '--find-renames', tree1]

        if tree2:
            cmd.append(tree2)

        diff_tree_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return diff_tree_out
    except subprocess.CalledProcessError as excep:
        print str(cmd) + ' failed: ' + str(excep.returncode) + '\n' + excep.output
        sys.exit(excep.returncode)


def git_status(root_dir):
    """run got status -s which tells you the status of your repo at root_dir"""
    args = ['status', '-s']
#    print _git_cmd(root_dir, args)
    status_out = subprocess.check_output(_git_cmd(root_dir, args),
                                         stderr=subprocess.STDOUT)
    return status_out


def git_add(root_dir, *args):
    """run git add on the path provided, in the repo at root_dir"""
    cmd_args = ['add']
    if args:
        cmd_args += args
#    print _git_cmd(root_dir, args)
    subprocess.check_call(_git_cmd(root_dir, cmd_args))


def git_commit(root_dir, message):
    """run git commit on the repo at root_dir, with the message provided"""
    args = ['commit', '-m', message]
#    print _git_cmd(root_dir, args)
    subprocess.check_call(_git_cmd(root_dir, args))


def git_push(root_dir):
    """run git push on the repo at root_dir"""
    args = ['push']
#    print _git_cmd(root_dir, args)
    subprocess.check_call(_git_cmd(root_dir, args))


class YawtGit(Plugin):
    """The YAWT Git plugin class"""

    def __init__(self, app=None):
        super(YawtGit, self).__init__(app)
        self.meta = {}

    def init_app(self, app):
        app.config.setdefault('YAWT_GIT_REPOPATH', False)
        app.config.setdefault('YAWT_GIT_SEARCH_PATH', False)

    def on_new_site(self, files):
        """When a new site is created, we'll save a gitignore file so we can
        ignore the _state directory
        """
        _save_repo_file('.gitignore', '_state')
