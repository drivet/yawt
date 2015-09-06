from __future__ import absolute_import

from flask import g, current_app
from flask_script import Command, Option

from yawtext.vc import vc_push, vc_commit, vc_add_tracked,\
    vc_add_tracked_and_new, vc_status
from yawt.utils import call_plugins
from yawtext import Plugin


def _sync(strict, addnew, push, message):
    root_dir = g.site.root_dir
    if not strict:
        # if addnew is True, this means we need to add all untracked files
        # to the index.  The -A will do that.  Otheriwse we just do a -u,
        # which will only update the tracked files.
        if addnew:
            vc_add_tracked_and_new()
        else:
            vc_add_tracked()

        # at this point we should have an almost snapshot of what we want
        # to commit in the index.  It's "almost" because we now may want
        # to fix up or add the timestamps.
        call_plugins('on_pre_sync', root_dir, vc_status())

        # readjust the index with whatever changes were made by
        # the pre_sync plugins
        vc_add_tracked()
    vc_commit(message)
    if push:
        vc_push()


class Sync(Command):
    """Sync command"""
    def __init__(self):
        super(Sync, self).__init__()

    def get_options(self):
        return [Option('--strict', '-s', action='store_true'),
                Option('--addnew', '-a', action='store_true'),
                Option('--push', '-p', action='store_true'),
                Option('--message', '-m')]

    def run(self, strict, addnew, push, message):
        current_app.preprocess_request()
        if not message:
            message = 'synced changes'
        _sync(strict, addnew, push, message)


class YawtSync(Plugin):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        super(YawtSync, self).__init__(app)

    def init_app(self, app):
        pass

    def on_cli_init(self, manager):
        """add the command to the CLI manager"""
        manager.add_command('sync', Sync())
