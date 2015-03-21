"""The main Command Line Interface classes for YAWT"""

from __future__ import absolute_import

import os

from flask import g, current_app
from flask_script import Command, Manager, Server

import yawt


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
        g.site.new_site()


class Walk(Command):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def run(self):
        current_app.preprocess_request()
        g.site.walk()


def create_manager():
    """Create the command line manager"""

    manager = Manager(yawt.create_app)
    # root_dir will be passed to the create_app method
    manager.add_option('-r', '--root_dir', dest='root_dir',
                       default=os.getcwd(), required=False)

    server = Server(use_debugger=True, use_reloader=True)
    server.description = 'runs the yawt local server.'
    manager.add_command('runserver', server)
    manager.add_command('newsite', NewSite())
    manager.add_command('walk', Walk())
    return manager
