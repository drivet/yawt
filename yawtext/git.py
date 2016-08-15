"""The YAWT Git plugin"""
import subprocess

from flask import current_app

from yawt.utils import run_in_context, call_plugins, ChangedFiles


def _git_cmd(args):
    git_exe = current_app.config['YAWT_VERSION_CONTROL_GIT_EXE']
    git_dir = current_app.yawt_root_dir + '/.git'
    return [git_exe, '--git-dir='+git_dir,
            '--work-tree='+current_app.yawt_root_dir] + args


def _git_files_changed(tree1, tree2):
    changed = _extract_diff_tree_files(tree1, tree2)
    call_plugins('on_files_changed', changed)


def _handle_changed_files(repo_path, app, tree1, tree2=None):
    if not app:
        run_in_context(repo_path, _git_files_changed, tree1, tree2)
    else:
        _git_files_changed(tree1, tree2)


def post_merge(repo_path, app=None):
    """Entry point for a vc merge operation"""
    _handle_changed_files(repo_path, app, 'ORIG_HEAD', 'HEAD')


def post_commit(repo_path, app=None):
    """Entry point for a vc commit operation"""
    _handle_changed_files(repo_path, app, 'HEAD')


def _extract_diff_tree_files(tree1, tree2=None):
    """Given git diff tree output, return the list of added, modied and
    removed files."""
    args = ['diff-tree', '-r', '--name-status', '--no-commit-id',
            '--find-renames', tree1]
    cmd = _git_cmd(args)

    if tree2:
        cmd.append(tree2)

    diff_tree_out_b = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    diff_tree_out = diff_tree_out_b.decode("utf-8")

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
    changed = ChangedFiles(added=added_files,
                           modified=modified_files,
                           deleted=deleted_files,
                           renamed=renamed_files)
    return changed


def vc_ignore_file():
    """Return the name of the git ignore file"""
    return '.gitignore'


def vc_status():
    """Given git status output, return the list of added, modified and removed
    files.  Note that files MUST have been added to the index.
    """
    cmd_args = ['status', '-s']
#    print _git_cmd(root_dir, args)
    git_cmd = _git_cmd(cmd_args)
    status_out_b = subprocess.check_output(git_cmd, stderr=subprocess.STDOUT)
    status_out = status_out_b.decode("utf-8")
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
    changed = ChangedFiles(added=added_files,
                           modified=modified_files,
                           deleted=deleted_files,
                           renamed=renamed_files)
    return changed


def vc_add_tracked():
    """run git add on the path provided, in the repo at root_dir"""
    cmd_args = ['add', '-u']
    subprocess.check_call(_git_cmd(cmd_args))


def vc_add_tracked_and_new():
    """run git add on the path provided, in the repo at root_dir"""
    cmd_args = ['add', '-A']
    subprocess.check_call(_git_cmd(cmd_args))


def vc_commit(message):
    """run git commit on the repo at root_dir, with the message provided"""
    cmd_args = ['commit', '-q', '-m', message]
#    print _git_cmd(root_dir, args)
    subprocess.check_call(_git_cmd(cmd_args))


def vc_push():
    """run git push on the repo at root_dir"""
    cmd_args = ['push']
#    print _git_cmd(root_dir, cmd_args)
    subprocess.check_call(_git_cmd(cmd_args))
