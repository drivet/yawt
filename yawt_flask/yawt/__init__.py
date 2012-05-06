import sys
import time

import yaml
from flask import Flask, g

from yawt.article import ArticleStore
from yawt.view import CategoryView, ArticleView

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.load(f)
    
def create_app(config=None): 
    if config is None:
        config = load_config()
        
    if 'path_to_templates' in config and config['path_to_templates']:
        app = Flask(__name__, template_folder=config['path_to_templates'])
    else:
        app = Flask(__name__)
    app.config.update(config)

    plugins = {}
    if 'plugins' in app.config:
        for name in app.config['plugins']:
            modname = app.config['plugins'][name]
            mod = __import__(modname)
            plugins[name] = sys.modules[modname]
            plugins[name].init(app)

    app.plugins = plugins

    # Article URLs
    # I believe this is the only semi-ambiguous URL.  Really, it means article,
    # but it can also mean category if there is no such article.
    @app.route('/<path:category>/<slug>')
    def post(category, slug):
        return ArticleView(g.store).dispatch_request(None, category, slug)

    @app.route('/<path:category>/<slug>.<flav>')
    def post_flav(category, slug, flav):
        return ArticleView(g.store).dispatch_request(flav, category, slug)

    # Category URLs
    @app.route('/')
    def home():
        return CategoryView(g.store).dispatch_request(None, '')

    @app.route('/index')
    def home_index():
        return CategoryView(g.store).dispatch_request(None, '')

    @app.route('/index.<flav>')
    def home_index_flav(flav):
        return CategoryView(g.store).dispatch_request(flav, '')
    
    @app.route('/<path:category>/')
    def category_canonical(category):
        return CategoryView(g.store).dispatch_request(None, category)
   
    @app.route('/<path:category>/index')
    def category_index(category):
        return CategoryView(g.store).dispatch_request(None, category)
    
    @app.route('/<path:category>/index.<flav>')
    def category_index_flav(category, flav):
        return CategoryView(g.store).dispatch_request(flav, category)
 
    # filter for date and time formatting
    @app.template_filter('dateformat')
    def date_format(value, format='%H:%M / %d-%m-%Y'):
        return time.strftime(format, value)

    # filter for date and time formatting
    @app.template_filter('excerpt')
    def excerpt(article, word_count=50):
        words = article.content.split()[0:word_count]
        words.append("[...]")
        return " ".join(words)

    @app.before_request
    def before_request():
        g.config = app.config
        g.plugins = app.plugins
        g.store = ArticleStore.get(app.config, app.plugins)

    return app
