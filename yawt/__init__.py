import os
import re
import sys
import time
import yaml
import copy

from flask import Flask, g, request, url_for
from jinja2.loaders import ChoiceLoader
from yawt.view import create_article_view, create_category_view, YawtLoader
from yawt.util import get_abs_path, Plugins, load_yaml
from yawt.article import ArticleStore, create_store

YAWT_LANG = 'YAWT_LANG'
YAWT_BASE_URL = 'YAWT_BASE_URL'
YAWT_PAGE_SIZE = 'YAWT_PAGE_SIZE'
YAWT_PATH_TO_TEMPLATES = 'YAWT_PATH_TO_TEMPLATE'
YAWT_PATH_TO_ARTICLES = 'YAWT_PATH_TO_ARTICLES'
YAWT_PATH_TO_STATIC = 'YAWT_PATH_TO_STATIC'
YAWT_STATIC_URL = 'YAWT_STATIC_URL'
YAWT_EXT = 'YAWT_EXT' 
YAWT_META_EXT = 'YAWT_META_EXT'
YAWT_USE_UNCOMMITTED = 'YAWT_USE_UNCOMMITTED'
YAWT_REPO_TYPE = 'YAWT_REPO_TYPE'
YAWT_BLOGPATH = 'YAWT_BLOGPATH'
YAWT_CONTENT_TYPES_RSS = 'application/rss+xml'
YAWT_PLUGINS = 'YAWT_PLUGINS'
YAWT_LOCATIONS = 'YAWT_LOCATIONS'

default_config = {
    YAWT_LANG: 'en',
    YAWT_BASE_URL: 'http://www.awesome.net/blog',
    YAWT_PAGE_SIZE: '10',
    YAWT_PATH_TO_TEMPLATES: 'templates',
    YAWT_PATH_TO_ARTICLES: 'entries',
    YAWT_PATH_TO_STATIC: 'static',
    YAWT_STATIC_URL: 'static',
    YAWT_EXT: 'txt',
    YAWT_META_EXT: 'meta',
    YAWT_USE_UNCOMMITTED: 'true',
    YAWT_REPO_TYPE: 'auto',
    YAWT_CONTENT_TYPES_RSS: 'application/rss+xml',
}

def _get_page_from_request():
    page = 1
    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        page = 1
    return page

def _extract_article_info(path):
    p = re.compile(r'^(.*?)(/([^./]+)(\.([^/.]+))?)?$')

    # path never starts with a slash, but the regex 
    # is easier to use if it does
    m = p.match('/' + path)
    category = re.sub('^/', '', m.group(1)) # strip leading slash
    slug = m.group(3)
    flavour = m.group(5)
    return (category, slug, flavour);

def _handle_path(path):
    (category, slug, flav) = _extract_article_info(path)
    if slug is None or slug == 'index':
        page = _get_page_from_request()
        return create_category_view().dispatch_request(flav, category, page,
                                                       int(g.config[YAWT_PAGE_SIZE]),
                                                       request.base_url)
    else:
        return create_article_view().dispatch_request(flav, category, slug)

def _load_config(path):
    config_file = os.path.join(path, 'config.yaml')
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
    template_folder = get_abs_path(blogpath, config[YAWT_PATH_TO_TEMPLATES])
    static_folder = get_abs_path(blogpath, config[YAWT_PATH_TO_STATIC])
    static_url = config[YAWT_STATIC_URL]
    app = Flask(__name__, template_folder=template_folder,
                static_url_path=static_url,
                static_folder=static_folder)
    app.debug = True
    app.config[YAWT_BLOGPATH] = blogpath
    app.config.update(config)
 
    old_loader = app.jinja_loader
    app.jinja_loader = ChoiceLoader([YawtLoader(template_folder), old_loader])

    plugins = {}
    if YAWT_PLUGINS in app.config:
        for plugin_name in app.config[YAWT_PLUGINS]:
            mod_name = app.config[YAWT_PLUGINS][plugin_name]
            __import__(mod_name)
            plugins[plugin_name] = sys.modules[mod_name]
           
            p = plugins[plugin_name].create_plugin()
            app.config[plugin_name] = _mod_config(app, p, plugin_name)
            p.init(app, plugin_name)
            plugins[plugin_name] = p
                
    app.plugins = Plugins(plugins)

#    for rule in app.url_map.iter_rules():
#        print rule

    @app.route('/')
    def home():
        return _handle_path('')
    
    @app.route('/<path:path>')
    def generic_path(path):
        return _handle_path(path) 

    # filter for date and time formatting
    @app.template_filter('dateformat')
    def date_format(value, format='%H:%M / %d-%m-%Y'):
        return time.strftime(format, value)

    # filter to extract a part of an article
    @app.template_filter('excerpt')
    def excerpt(article, word_count=50):
        words = article.content.split()[0:word_count]
        words.append("[...]")
        return " ".join(words)
 
    # filter to test for multi page 
    @app.template_filter('is_multi_page')
    def is_multi_page(total_pages):
        return total_pages != 1
  
    # make a usable url out of a site relative one
    @app.template_filter('url')
    def url(relative_url):
        base_url = app.config[YAWT_BASE_URL] or request.url_root
        url = base_url.rstrip('/') + '/' + relative_url.lstrip('/')
        return url

    @app.template_filter('static')
    def static(filename):
        return url_for('static', filename=filename)

    @app.before_request
    def before_request():
        g.config = copy.deepcopy(app.config)

        locations = app.config[YAWT_LOCATIONS]
        for regex, config in locations.items():
            p = re.compile(regex)
            m = p.match(request.path)
            if m:
                g.config.update(config)

        g.plugins = app.plugins
        g.store = create_store()
    return app
