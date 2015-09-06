"""The main Command Line Interface classes for YAWT"""

from __future__ import absolute_import

import os
import argparse

from flask import g, current_app
from flask_script import Command, Manager, Server

import yawt
from yawt.utils import call_plugins


class NewSite(Command):
    """The newsite command will create take a directory and create a new site
    there

    newsite
    --> config.yaml
    --> content
    --> templates

    The content directory is where you put your blog entries

    """
    def run(self):
        current_app.preprocess_request()
        g.site.initialize()


class Walk(Command):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def run(self):
        current_app.preprocess_request()
        g.site.walk()


def _root_dir():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--root_dir", default=os.getcwd())
    args_and_rest = parser.parse_known_args()
    return args_and_rest[0].root_dir


def create_manager(app=None):
    """Create the command line manager"""
    app_supplied = True
    if not app:
        app = yawt.create_app(_root_dir())
        app_supplied = False
    manager = Manager(app)

    # specify root_dir which will be consumed but ignored since we have an app
    # instance not a function
    manager.add_option('-r', '--root_dir', dest='root_dir',
                       default=os.getcwd(), required=False)

    server = Server(use_debugger=True, use_reloader=True)
    server.description = 'runs the yawt local server.'
    manager.add_command('runserver', server)
    manager.add_command('newsite', NewSite())
    manager.add_command('walk', Walk())

    if app_supplied:
        _handle_cli_init(manager)
    else:
        with app.test_request_context():
            _handle_cli_init(manager)

    return manager


def _handle_cli_init(manager):
    current_app.preprocess_request()
    call_plugins('on_cli_init', manager)
