import os
import sys
import time
import yaml
import copy

from flask import Flask, g, request, url_for
from jinja2.loaders import ChoiceLoader
from yawt.view import create_article_view, create_category_view, YawtLoader
from yawt.util import get_abs_path, Plugins, load_yaml
from yawt.article import ArticleStore

default_config = {
    'YAWT_LANG': 'en',
    'YAWT_BASE_URL': 'http://www.awesome.net/blog',
    'YAWT_PAGE_SIZE': '10',
    'YAWT_PATH_TO_TEMPLATES': 'templates',
    'YAWT_PATH_TO_ARTICLES': 'entries',
    'YAWT_PATH_TO_STATIC': 'static',
    'YAWT_STATIC_URL': 'static',
    'YAWT_EXT': 'txt',
    'YAWT_META_EXT': 'meta',
    'YAWT_CONTENT_TYPES_RSS': 'application/rss+xml',
}

def _load_config(blogpath):
    config_file = os.path.join(blogpath, 'config.yaml')
    try:
        return load_yaml(config_file)
    except IOError as e:
        print 'Warning: could not load configuration at ' + config_file
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
    template_folder = get_abs_path(blogpath, config['YAWT_PATH_TO_TEMPLATES'])
    static_folder = get_abs_path(blogpath, config['YAWT_PATH_TO_STATIC'])
    static_url = config['YAWT_STATIC_URL']
    app = Flask(__name__, template_folder=template_folder,
                static_url_path=static_url,
                static_folder=static_folder)
    app.config['YAWT_BLOGPATH'] = blogpath
    app.config.update(config)
 
    plugins = {}
    if 'YAWT_PLUGINS' in app.config:
        for plugin_name in app.config['YAWT_PLUGINS']:
            mod_name = app.config['YAWT_PLUGINS'][plugin_name]
            __import__(mod_name)
            plugins[plugin_name] = sys.modules[mod_name]
           
            p = plugins[plugin_name].create_plugin()
            app.config[plugin_name] = _mod_config(app, p, plugin_name)
            p.init(app, plugin_name)
            plugins[plugin_name] = p
                
    app.plugins = Plugins(plugins)

    old_loader = app.jinja_loader
    app.jinja_loader = ChoiceLoader([YawtLoader(template_folder), old_loader])
    
    @app.route('/')
    def home():
        return _handle_category_url(None, '')
    
    @app.route('/<path:category>/')
    def category_canonical(category):
        return _handle_category_url(None, category)

    @app.route('/<path:category>/<slug>')
    def post(category, slug):
        return _handle_categorized_url(None, category, slug)

    @app.route('/<path:category>/<slug>.<flav>')
    def post_flav(category, slug, flav):
        return _handle_categorized_url(flav, category, slug)

    @app.route('/<slug>.<flav>')
    def post_flav_no_cat(slug, flav):
        return _handle_categorized_url(flav, '', slug)

    @app.route('/<slug>')
    def post_slug(slug):
        return _handle_categorized_url(None, '', slug)

    def _handle_categorized_url(flav, category, slug):
        if slug == 'index':
            return _handle_category_url(flav, category)
        else:
            return create_article_view().dispatch_request(flav, category, slug)
        
    def _handle_category_url(flav, category):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        category_view = create_category_view()
        return category_view.dispatch_request(flav, category, page,
                                              int(g.config['YAWT_PAGE_SIZE']),
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
        base_url = app.config['YAWT_BASE_URL'] or request.url_root
        url = base_url.rstrip('/') + '/' + relative_url.lstrip('/')
        return url

    @app.template_filter('static')
    def static(filename):
        return url_for('static', filename=filename)

    @app.before_request
    def before_request():
        g.config = app.config
        g.plugins = app.plugins
        g.store = ArticleStore.get(app.config, g.plugins)
    return app
