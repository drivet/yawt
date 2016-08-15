"""The YAWT Git plugin which will dig into the repo to provide create_time,
modified_time and author information
"""
import os

from flask import current_app

from yawt.utils import save_file, cfg
from yawtext import Plugin


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
