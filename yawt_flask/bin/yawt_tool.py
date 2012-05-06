from flaskext.script import Manager, Server, Command, Option
from yawt import ArticleStore, create_app
import yawt.util
import sys
import yaml

manager = Manager(create_app)
server = Server(use_debugger=True, use_reloader=True)
server.description = 'runs the yawt local server.'
manager.add_command('runserver', server)

class Walk(Command):
    """
    The walk command will visit every article in the repo and let each
    plugin do something with it.
    """
    def handle(self, app):
        store = ArticleStore.get(app.config, app.plugins)
        walkers = filter(lambda w: w,
                         map(lambda p: yawt.util.has_method(p, 'walker') and p.walker(store),
                             app.plugins.values()))
        map(lambda w: w.pre_walk(), walkers)
        for fullname in store.walk_articles():
            map(lambda w: w.visit_article(fullname), walkers)
        map(lambda w: w.post_walk(), walkers)
        
class Update(Command):
    """
    The update command will take input like this

    A file1
    M file2
    R file3

    and interpret it as file statuses.  A means added,
    M means modified, R means removed.
    """
    option_list = (
        Option('--statuses', '-s', dest='statuses'),
    )
    
    def handle(self, app, statuses): 
        store = ArticleStore.get(app.config, app.plugins)
        updaters = filter(lambda w: w,
                          map(lambda p: yawt.util.has_method(p, 'updater') and p.updater(store),
                              app.plugins.values()))
        
        status_map = self._file_statuses(statuses)
        map(lambda u: u.update(status_map), updaters)
     
    def _file_statuses(self, status_output):
        status_tokens = status_output.split()
        file_statuses = {}
        for i in xrange(0, len(status_tokens), 2):
            s = status_tokens[i]
            if s in ['A','M','R']:   
                f = status_tokens[i+1]
                file_statuses[f] = s
        return file_statuses
    
manager.add_command('walk', Walk())
manager.add_command('update', Update())

if __name__ == '__main__':
    manager.run()
