from __future__ import absolute_import

import os.path
import socket
from flask import current_app
from yawtext.micropost import post_social
from yawt.utils import fullname, find_new_renames


def _cfg(key):
    return current_app.config[key]


def _draft_folder():
    return _cfg('YAWT_DRAFT_FOLDER')


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _notify_message(file_added):
    base_url = _cfg('YAWT_NOTIFY_BASE_URL')
    name = fullname(file_added)
    link = os.path.join(base_url, name)
    return link


def _post_notification(added):
    msg = _notify_message(added)
    post_social(msg, _cfg('YAWT_NOTIFY_NETWORKS'))
#    print "notify with msg = '"+msg + "' and file = "+added


def notify_new_files(added, renamed):
    """Sends out a notification about new blog files to social networks"""

    if _cfg('YAWT_NOTIFY_HOSTS') and \
       socket.gethostname() not in _cfg('YAWT_NOTIFY_HOSTS'):
        return

    cat_paths = []
    for cat in _cfg('YAWT_NOTIFY_CATEGORIES'):
        cat_paths.append(os.path.join(_content_folder(), cat))

    for added in added + find_new_renames(renamed):
        for cpath in cat_paths:
            if added.startswith(cpath):
                _post_notification(added)


class YawtNotify(object):
    """Notify extension, allowing you to post updates on social networks"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_NOTIFY_CATEGORIES', [''])
        app.config.setdefault('YAWT_NOTIFY_BASE_URL', '')
        app.config.setdefault('YAWT_NOTIFY_NETWORKS', ['facebook'])
        app.config.setdefault('YAWT_NOTIFY_HOSTS', [])
        app.config.setdefault('YAWT_NOTIFY_FB_ACCESS_TOKEN_FILE',
                              '~/.fbaccesstoken')

    def on_files_changed(self, added, modified, deleted, renamed):
        notify_new_files(added, renamed)
