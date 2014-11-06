from flask_script import Command, Option, Manager, Server
from flask import current_app

class LifecyclePlugin(object):
    def __init__(self):
        self.manager = None

    def init_app(self, app):
        self.manager = Manager(app)
        server = Server(use_debugger=True, use_reloader=True)
        server.description = 'runs the yawt local server.'
        self.manager.add_command('runserver', server)
        
class NewSite(Command):
    """The newsite command takes a folder and creates a new site there

    newsite
    --> config.py
    --> content
    --> templates

    The content directory is where you put your blog entries

    """
    def run(self):
        root_dir = current_app.yawt_root_dir
        repo.initialize(repotype, {
            'config.yaml': yaml.dump(yawt.default_config),
            'templates/404.html': yawt.view.default_404_template,
            'templates/article.html': yawt.view.default_article_template,
            'templates/article_list.html': yawt.view.default_article_list_template,
            'content/': None,
            'drafts/': None,
        } )
