import os.path
import socket

from yawt.utils import fullname, cfg, content_folder
from yawtext import Plugin
from yawtext.micropost import post_social


def _notify_message(file_added):
    base_url = cfg('YAWT_NOTIFY_BASE_URL')
    name = fullname(file_added)
    link = os.path.join(base_url, name)
    return (link, link)


def _post_notification(added):
    (msg, link) = _notify_message(added)
    post_social(msg, cfg('YAWT_NOTIFY_NETWORKS'), link)
#    print "notify with msg = '"+msg + "' and file = "+added


def notify_new_files(changed):
    """Sends out a notification about new blog files to social networks"""

    if cfg('YAWT_NOTIFY_HOSTS') and \
       socket.gethostname() not in cfg('YAWT_NOTIFY_HOSTS'):
        return

    cat_paths = []
    for cat in cfg('YAWT_NOTIFY_CATEGORIES'):
        cat_paths.append(os.path.join(content_folder(), cat))

    for added in changed.content_changes().added:
        for cpath in cat_paths:
            if added.startswith(cpath):
                _post_notification(added)


class YawtNotify(Plugin):
    """Notify extension, allowing you to post updates on social networks"""
    def __init__(self, app=None):
        super(YawtNotify, self).__init__(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_NOTIFY_CATEGORIES', [''])
        app.config.setdefault('YAWT_NOTIFY_BASE_URL', '')
        app.config.setdefault('YAWT_NOTIFY_NETWORKS', ['facebook'])
        app.config.setdefault('YAWT_NOTIFY_HOSTS', [])
        app.config.setdefault('YAWT_NOTIFY_FB_ACCESS_TOKEN_FILE',
                              '~/.fbaccesstoken')

    def on_files_changed(self, changed):
        notify_new_files(changed)
