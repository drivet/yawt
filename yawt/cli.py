import os

from flask import g
from flask_script import Command, Option, Manager, Server

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
        g.site.new_site()


class Walk(Command):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def run(self):
        g.site.walk()

class FilesAdded(Command):
    """
    Inform YAWT that new files have been added to the repository
    """
    option_list = (
        Option('files'),
    )

    def run(self, files):
        g.site.files_added(files)


class FilesModified(Command):
    """
    Inform YAWT that new files have been modified in the repository
    """
    option_list = (
        Option('files'),
    )

    def run(self, files):
        g.site.files_modified(files)


class FilesDeleted(Command):
    """
    Inform YAWT that new files have been deleted in the repository
    """
    option_list = (
        Option('files'),
    )

    def run(self, files):
        g.site.files_deleted(files)


def create_manager():
    manager = Manager(yawt.create_app)
    # root_dir will be passed to the create_app method
    manager.add_option('-r', '--root_dir', dest='root_dir',
                       default=os.getcwd(), required=False)

    server = Server(use_debugger=True, use_reloader=True)
    server.description = 'runs the yawt local server.'
    manager.add_command('runserver', server)
    manager.add_command('newsite', NewSite())
    manager.add_command('walk', Walk())
    manager.add_command('added', FilesAdded())
    manager.add_command('modified', FilesModified())
    manager.add_command('deleted', FilesDeleted())
    return manager

