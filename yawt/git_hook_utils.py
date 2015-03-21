"""Some common code for managing git hooks"""
from __future__ import absolute_import

import sys
import subprocess
from flask import g, current_app
import yawt


def yawt_changed_files(repo_path, added_files, modified_files, deleted_files):
    """Inform the system that the supplied files have changed"""
    app = yawt.create_app(repo_path)
    with app.test_request_context():
        current_app.preprocess_request()
        g.site.files_changed(modified_files, added_files, deleted_files)


def extract_changed_files(diff_tree_out):
    """Given git diff tree output, return the list of added, modied and
    removed files."""
    added_files = []
    modified_files = []
    deleted_files = []
    for line in diff_tree_out.split('\n'):
        if not line:
            break

        (status, f) = line.split()
        if status == 'A':
            added_files.append(f)
        elif status == 'M':
            modified_files.append(f)
        elif status == 'D':
            deleted_files.append(f)
        else:
            print "unknown git status: " + status
            sys.exit(1)
    return added_files, modified_files, deleted_files


def git_diff_tree(git, repo_path, tree1, tree2=None):
    """Execute a git diff-tree and return the output of that command"""
    try:
        cmd = ['sudo', '-u', 'www-data', '-H',
               git, '--git-dir=' + repo_path + '/.git',
               '--work-tree=' + repo_path,
               'diff-tree', '-r', '--name-status', '--no-commit-id', tree1]

        if tree2:
            cmd.append(tree2)

        diff_tree_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print str(cmd) + ' failed: ' + str(e.returncode) + '\n' + e.output
        sys.exit(e.returncode)
    return diff_tree_out
