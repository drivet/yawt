from flask_script import Command, Option, Manager, Server, InvalidCommand
from flask import current_app, g
import os
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


class CreateOrUpdateDraft(Command):
    """
    Creates empty new article in the draft folder, optionally with content
    """
    option_list = (
        Option('name'),
        Option('--extension', '-e', dest='extension'),
        Option('--content', '-c', dest='content'),
        Option('--filename', '-f', dest='filename'),
    )
    
    def run(self, name, extension=None, content=None, filename=None):
        if extension is None:
            extension = current_app.config['YAWT_DEFAULT_EXTENSION']

        if content and filename:
            raise InvalidCommand('Options content and filename are incompatible')
        
        if content is None:
            if filename:
                content = load_file(filename)
            else:
                content = 'put content here'
            
        g.site.save_draft(name, extension, content)


class CreateOrUpdateArticle(Command):
    """
    Creates new article in the content folder, optionally with content
    """
    option_list = (
        Option('name'),
        Option('--extension', '-e', dest='extension'),
        Option('--content', '-c', dest='content'),
        Option('--filename', '-f', dest='filename'),
    )
    
    def run(self, name,  extension=None, content=None, filename=None):
        if extension is None:
            extension = current_app.config['YAWT_DEFAULT_EXTENSION'] 

        if content and filename:
            raise InvalidCommand('Options content and filename are incompatible')
        
        if content is None:
            if filename:
                content = load_file(filename)
            else:
                content = 'put content here'

        g.site.save_article(name, extension, content)


class Publish(Command):
    """
    Moves an article from the draft folder to the contents folder.
    """
    option_list = (
        Option('draftname'),
        Option('articlename'),
    )
    
    def run(self, draftname, articlename):
        g.site.publish(draftname, articlename)


class Move(Command):
    """
    Moves an article from the one location to another
    """
    option_list = (
        Option('oldname'),
        Option('newname'),
        Option('--draft', '-d', dest='draft'),
    )
    
    def run(self, oldname, newname, draft=False): 
        if draft:
            g.site.move_draft(oldname, newname)
        else:
            g.site.move_article(oldname, newname)


class Delete(Command):
    """
    Deletes an article
    """
    option_list = (
        Option('name'),
        Option('--draft', '-d', dest='draft'),
    )
    
    def run(self, name, draft=False):
        if draft:
            g.site.delete_draft(name)
        else:
            g.site.delete_article(name)


def create_manager():
    manager = Manager(yawt.create_app)
    # root_dir will be passed to the create_app method
    manager.add_option('-r', '--root_dir', dest='root_dir',
                       default=os.getcwd(), required=False)

    server = Server(use_debugger=True, use_reloader=True)
    server.description = 'runs the yawt local server.'
    manager.add_command('runserver', server)

    manager.add_command('newsite', NewSite())
    manager.add_command('draft', CreateOrUpdateDraft())
    manager.add_command('article', CreateOrUpdateArticle())
    manager.add_command('move', Move())
    manager.add_command('delete', Delete())
    manager.add_command('publish', Publish())     
    return manager


def load_file(filename):
    with open(filename, 'r') as f:
        file_contents = f.read()
    return file_contents
