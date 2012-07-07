import os
import sys
import time
import yaml
import copy

from flask import Flask, g, request
from jinja2.loaders import ChoiceLoader
from yawt.view import create_article_view, create_category_view, YawtLoader
from yawt.util import get_abs_path, Plugins, load_yaml
from yawt.article import ArticleStore

default_config = {
    'blogtitle': 'Awesome Blog Title',
    'blogdescription': 'Awesome Blog Description',
    'bloglang': 'en',
    'blogurl': 'http://www.awesome.net/blog',
    'page_size': '10',
    'path_to_templates': 'templates',
    'path_to_articles': 'entries',
    'path_to_static': 'static',
    'ext': 'txt',
    'meta_ext': 'meta',
    
    'content_types': {
        'rss': 'application/rss+xml'
    },
}

def _load_config(blogpath):
    try:
        return load_yaml(os.path.join(blogpath, 'config.yaml'))
    except IOError as e:
        print 'Exception thrown loading config: ' + str(e)
        return {}

def _mod_config(app, mod, plugin_name):
    mod_config = {}
    if hasattr(mod, 'default_config'):
        mod_config = copy.deepcopy(mod.default_config)
        if plugin_name in app.config:
            mod_config.update(app.config[plugin_name])
    return mod_config
    
def create_app(blogpath=None):
    config = copy.deepcopy(default_config)
    config.update(_load_config(blogpath))
    template_folder = get_abs_path(blogpath, config['path_to_templates'])
    static_folder = get_abs_path(blogpath, config['path_to_static'])
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config['blogpath'] = blogpath
    app.config.update(config)
 
    plugins = {}
    if 'plugins' in app.config:
        for plugin_name in app.config['plugins']:
            mod_name = app.config['plugins'][plugin_name]
            __import__(mod_name)
            plugins[plugin_name] = sys.modules[mod_name]
            app.config[plugin_name] = _mod_config(app, plugins[plugin_name], plugin_name)
            plugins[plugin_name].init(app, plugin_name)
    app.plugins = Plugins(plugins)

    old_loader = app.jinja_loader
    app.jinja_loader = ChoiceLoader([YawtLoader(template_folder), old_loader])
    
    # Article URLs
    # I believe this is the only semi-ambiguous URL.  Really, it means article,
    # but it can also mean category if there is no such article.
    @app.route('/<path:category>/<slug>')
    def post(category, slug):
        return create_article_view().dispatch_request(None, category, slug)

    @app.route('/<path:category>/<slug>.<flav>')
    def post_flav(category, slug, flav):
        return create_article_view().dispatch_request(flav, category, slug)

    @app.route('/<slug>.<flav>')
    def post_flav_no_cat(slug, flav):
        return create_article_view().dispatch_request(flav, '', slug)

    @app.route('/<slug>')
    def post_slug(slug):
        return create_article_view().dispatch_request(None, '', slug)

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

        category_view = create_category_view()
        return category_view.dispatch_request(flav, category, page,
                                              int(g.config['page_size']),
                                              request.base_url)
        
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

    # make a usable url out of a site relative one
    @app.template_filter('url')
    def url(relative_url):
        base_url = app.config['blogurl'] or request.url_root
        url = base_url.rstrip('/') + '/' + relative_url.lstrip('/')
        return url

    @app.before_request
    def before_request():
        g.config = app.config
        g.plugins = app.plugins
        g.store = ArticleStore.get(app.config, g.plugins)

    return app
