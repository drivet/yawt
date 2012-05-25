from flaskext.script import Manager, Server, Command, Option
from yawt import ArticleStore, create_app
import yawt.util
import sys
import subprocess
import yaml
import os

def _is_hg_repo_root():
    return os.path.isdir('.hg') and subprocess.call(['hg', 'status']) == 0

def _hg_init(directory):
    subprocess.call(['hg', 'init', directory])
   
def _save_add_str(filename, contents):
    yawt.util.save_string(filename, contents)
    _hg_add(filename)

def _save_add_yaml(filename, yaml):
    yawt.util.save_yaml(filename, yaml)
    _hg_add(filename)

def _hg_add(filename):
    subprocess.call(['hg', 'add', filename])

def _hg_commit(message):
    subprocess.call(['hg', 'ci', '-m', message])

class YawtCommand(Command):
    def handle(self, app, *args, **kwargs):
        self.app = app
        super(YawtCommand, self).handle(app, *args, **kwargs)
    
class Walk(YawtCommand):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def run(self):
        store = ArticleStore.get(self.app.config, self.app.plugins)
        walkers = self.app.plugins.walkers(store)
        
        map(lambda w: w.pre_walk(), walkers)
        for fullname in store.walk_articles():
            map(lambda w: w.visit_article(fullname), walkers)
        map(lambda w: w.post_walk(), walkers)
        

class Update(YawtCommand):
    """
    The update command will take input like this

    A file1
    M file2
    R file3

    and interpret it as file statuses.  A means added,
    M means modified, R means removed.
    """
    option_list = (
        Option('statuses'),
    )
    
    def run(self, statuses): 
        store = ArticleStore.get(self.app.config, self.app.plugins)
        updaters = self.app.plugins.updaters(store) 
        status_map = self._file_statuses(statuses)
        map(lambda u: u.update(status_map), updaters)
     
    def _file_statuses(self, status_output):
        status_tokens = status_output.split() if status_output is not None else ''
        file_statuses = {}
        for i in xrange(0, len(status_tokens), 2):
            s = status_tokens[i]
            if s in ['A','M','R']:   
                f = status_tokens[i+1]
                file_statuses[f] = s
        return file_statuses


class NewBlog(YawtCommand):
    """
    The newblog command will create take a directory and create a new hg
    repository there.  In addition to the hg repository, you'll get a
    couple of directories and files:

    newblog
    --> config.yaml
    --> entries
    --> templates

    The entries directory is where you put your blog entries.  Alongside
    the blog entries, you can put yaml metadata.  The yaml metadata file
    extensions are defined in the config.yaml file.  The template directory
    contains your templates.

    All this will be checked into the repository.
    """
    option_list = (
        Option('directory'),
    )
    
    def run(self, directory):
        _hg_init(directory)
        os.chdir(directory)
        _save_add_yaml('config.yaml', yawt.default_config)
  
        os.makedirs('templates')
        _save_add_str('templates/404.html', yawt.view.default_404_template)
        _save_add_str('templates/article.html', yawt.view.default_article_template)
        _save_add_str('templates/article_list.html', yawt.view.default_article_list_template)
 
        os.makedirs('entries')
        _hg_commit('initial commit')


class NewArticle(YawtCommand):
    option_list = (
        Option('article'),
    )
    
    def run(self, article):
        if _is_hg_repo_root():
            ext = self.app.config['ext']
            article_file = os.path.join(self.app.config['path_to_articles'], article + '.' + ext)
            _save_add_str(article_file,'')
        else:
            print "error: not at hg repository root"
        

manager = Manager(create_app)
server = Server(use_debugger=True, use_reloader=True)
server.description = 'runs the yawt local server.'
manager.add_command('runserver', server)
manager.add_command('newblog', NewBlog())
manager.add_command('newarticle', NewArticle())
manager.add_command('walk', Walk())
manager.add_command('update', Update())

if __name__ == '__main__':
    manager.run()
