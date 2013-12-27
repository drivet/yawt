from flask_script import Command, Option, Manager, Server

import os
import yawt
import yaml
import time

from yawt.repository import Repository

class YawtCommand(Command):
    """
    Exactly the same as Command, except it saves the app object
    when handle() is called.
    """
    def __init__(self):
        self.app = None

    def handle(self, app, *args, **kwargs):
        self.app = app
        super(YawtCommand, self).handle(app, *args, **kwargs)

        
class NewBlog(YawtCommand):
    """
    The newblog command will create take a directory and create a new
    repository there.  In addition to the repository, you'll get a
    couple of directories and files:

    newblog
    --> config.yaml
    --> content
    --> templates

    The content directory is where you put your blog entries.  Alongside
    the blog entries, you can put yaml metadata.  The yaml metadata file
    extensions are defined in the config.yaml file.  The template directory
    contains your templates.

    All this will be checked into the repository.
    """
    option_list = (
        Option('--repotype', '-r', dest='repotype', default='hg'),
    )
    
    def run(self, repotype="hg"):
        blogroot = self.app.config[yawt.YAWT_BLOGPATH]
        repo = Repository(blogroot)
        repo.initialize(repotype, {
            'config.yaml': yaml.dump(yawt.default_config),
            'templates/404.html': yawt.view.default_404_template,
            'templates/article.html': yawt.view.default_article_template,
            'templates/article_list.html': yawt.view.default_article_list_template,
            'content/': None,
            'drafts/': None,
        } )


class NewPost(YawtCommand):
    """
    Creates empty new post in the draft folder and commits it.
    """
    option_list = (
        Option('postname'),
    )
    
    def run(self, postname): 
        blogroot = self.app.config[yawt.YAWT_BLOGPATH]
        repo = Repository(blogroot)
        ext = self.app.config[yawt.YAWT_EXT]
        drafts = self.app.config[yawt.YAWT_PATH_TO_DRAFTS]
        fullpostname = drafts + "/" + postname + "." + ext
        repo.commit_contents({fullpostname: ""})

class Save(YawtCommand):
    """
    Commits changes in the blog repository.
    """
    option_list = (
        Option('--message', '-m', dest='message'),
    )
    
    def run(self, message = None):
        blogroot = self.app.config[yawt.YAWT_BLOGPATH]
        repo = Repository(blogroot)
        message = message or "saved on " + time.strftime("%d/%m/%Y %H:%M:%S")
        repo.save(message)

class Publish(YawtCommand):
    """
    Moves a post from the draft folder to the contents folder.
    """
    option_list = (
        Option('draftname'),
        Option('postname'),
    )
    
    def run(self, draftname, postname):
        blogroot = self.app.config[yawt.YAWT_BLOGPATH]
        repo = Repository(blogroot)
        ext = self.app.config[yawt.YAWT_EXT]
        drafts = self.app.config[yawt.YAWT_PATH_TO_DRAFTS]
        contents = self.app.config[yawt.YAWT_PATH_TO_ARTICLES]
        draftfile = drafts + "/" + draftname + "." + ext
        postfile = contents + "/" + postname + "." + ext
        repo.move(draftfile, postfile, "published " + postname)

class Walk(YawtCommand):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def run(self):
        store = yawt.article.create_store(self.app.config, self.app.plugins)
        walkers = self.app.plugins.walkers(store)
        
        map(lambda w: w.pre_walk(), walkers)
        for fullname in store.walk_articles():
            map(lambda w: w.visit_article(fullname), walkers)
        map(lambda w: w.post_walk(), walkers)


class Update(YawtCommand):
    """
    The update command will take input like this

    A fullname1
    M fullname2
    R fullname3

    and interpret it as article statuses.  A means added,
    M means modified, R means removed.
    """
    option_list = (
        Option('statuses'),
    )
    
    def run(self, statuses):
        store = yawt.article.create_store(self.app.config, self.app.plugins)
        updaters = self.app.plugins.updaters(store)
        status_map = self._file_statuses(store, statuses)
        map(lambda u: u.update(status_map), updaters)
     
    def _file_statuses(self, store, status_output):
        status_tokens = status_output.split() if status_output is not None else ''
        file_statuses = {}
        for i in xrange(0, len(status_tokens), 2):
            s = status_tokens[i]
            f = status_tokens[i+1]
            if s in ['A','M','R']:
                file_statuses[f] = s
        return file_statuses

class Info(YawtCommand):
    """
    Query configuration items
    """
    option_list = (
        Option('item'),
    )
    
    def run(self, item):
        if item in self.app.config:
            print self.app.config[item]
        else:
            print 'no configuration item found at ' + item

def create_manager():
    manager = Manager(yawt.create_app)
    # blogpath will be passed to the create_app method
    manager.add_option('-b', '--blogpath', dest='blogpath',
                       default=os.getcwd(), required=False)
    server = Server(use_debugger=True, use_reloader=True)
    server.description = 'runs the yawt local server.'
    manager.add_command('runserver', server)
    manager.add_command('walk', Walk())
    manager.add_command('update', Update())
    manager.add_command('newblog', NewBlog())
    manager.add_command('newpost', NewPost())
    manager.add_command('publish', Publish())
    manager.add_command('save', Save())
    manager.add_command('info', Info())
     
    return manager

if __name__ == '__main__':
    create_manager().run()
