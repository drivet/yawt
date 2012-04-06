from flaskext.script import Manager, Server, Command
from yawt import ArticleStore, create_app
import yawt.util
import sys
import yaml

manager = Manager(create_app)
server = Server(use_debugger=True, use_reloader=True)
server.description = 'runs the yawt local server.'
manager.add_command('runserver', server)

class Walk(Command):
    def handle(self, app):
        store = ArticleStore.get(app.yawtconfig, app.yawtplugins)
        walkers = filter(lambda walker: walker,
                         map(lambda plugin: yawt.util.has_method(plugin, 'walker') and plugin.walker(store),
                             app.yawtplugins.values()))
        map(lambda walker: walker.pre_walk(), walkers)
        for fullname in store.walk_articles():
            map(lambda walker: walker.visit_article(fullname), walkers)
        map(lambda walker: walker.post_walk(), walkers)

manager.add_command('walk', Walk())

if __name__ == '__main__':
    manager.run()
