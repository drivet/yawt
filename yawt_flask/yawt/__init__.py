import sys
import time

import yaml
from flask import Flask, g, request

from yawt.article import ArticleStore
from yawt.view import create_article_view, create_category_view
from yawt.util import Plugins

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

    app.plugins = Plugins(plugins)

    # Article URLs
    # I believe this is the only semi-ambiguous URL.  Really, it means article,
    # but it can also mean category if there is no such article.
    @app.route('/<path:category>/<slug>')
    def post(category, slug):
        return create_article_view().dispatch_request(None, category, slug)

    @app.route('/<path:category>/<slug>.<flav>')
    def post_flav(category, slug, flav):
        return create_article_view().dispatch_request(flav, category, slug)

    # Category URLs
    @app.route('/')
    def home():
        return _handle_category_url(None, '')

    @app.route('/index')
    def home_index():
        return _handle_category_url(None, '')

    @app.route('/index.<flav>')
    def home_index_flav(flav):
        return _handle_category_url(flav, '')
    
    @app.route('/<path:category>/')
    def category_canonical(category):
        return _handle_category_url(None, category)
   
    @app.route('/<path:category>/index')
    def category_index(category):
        return _handle_category_url(None, category)
    
    @app.route('/<path:category>/index.<flav>')
    def category_index_flav(category, flav):
        return _handle_category_url(flav, category)

    def _handle_category_url(flav, category):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        cv = create_category_view()
        return cv.dispatch_request(flav, category, page,
                                   g.config['page_size'], request.base_url)
        
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
        g.store = ArticleStore.get(app.config, g.plugins)

    return app
