from flask import Flask
import re
import os
import sys
import jinja2

# default configuration
YAWT_BASE_URL = 'http://www.awesome.net/blog'
YAWT_CONTENT_FOLDER = 'content'
YAWT_DRAFT_FOLDER = 'drafts'
YAWT_TEMPLATE_FOLDER = 'templates'
YAWT_DEFAULT_FLAVOUR = 'html'
YAWT_INDEX_FILE = 'index'
YAWT_ARTICLE_TEMPLATE = 'article'
YAWT_ARTICLE_EXTENSIONS = ['txt']
YAWT_DEFAULT_EXTENSION = 'txt'
YAWT_CONTENT_TYPE_RSS = 'application/rss+xml'
YAWT_PLUGINS = []

def get_content_types(config):
    def extract_type(key):
        m = re.compile('YAWT_CONTENT_TYPE_(.*)').match(key)
        if m:
            return (m.group(1).lower(), config[m.group(0)])
        return None
    return dict(filter(None, map(extract_type, config.keys())))

def configure_app(app, config):
    app.config.from_object(__name__)
    if config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_object(config)
    app.content_types = get_content_types(app.config)

def create_app(root_dir, template_folder = 'templates', static_folder = 'static', 
               static_url_path = '/static', config = None):
    app = Flask(__name__, 
                static_folder = os.path.join(root_dir, static_folder),
                static_url_path = static_url_path, 
                instance_path = root_dir,
                instance_relative_config = True) 
    app.yawt_root_dir = root_dir
    app.yawt_template_folder = template_folder
    app.yawt_static_folder = static_folder
    app.yawt_static_url_path = static_url_path

    path_to_templates = os.path.join(root_dir, template_folder)
    app.jinja_loader = jinja2.FileSystemLoader(path_to_templates)

    with app.app_context():
        configure_app(app, config)
        PluginManager().load_plugins(app)

        from yawt.main import yawtbp
        app.register_blueprint(yawtbp)
    return app

        
class PluginManager(object):
    def __init__(self):
        self.plugins = None

    def load_plugins(self, app):
        """
        Plugins are configured like this:
        YAWT_PLUGINS = [('plugin_name1', 'module1.class'), 
                        ('plugin_name2', 'module2.class')]
        """
        plugins = []
        if 'YAWT_PLUGINS' in app.config:
            for plugin_pair in app.config['YAWT_PLUGINS']:
                plugin_name = plugin_pair[0]
                full_class_string = plugin_pair[1]
                class_obj = self.load_class(full_class_string)
                plugin_instance = class_obj()
                plugin_instance.init_app(app)
                plugins.append((plugin_name, plugin_instance))
        self.plugins = plugins
        app.plugin_manager = self

    def load_class(self, full_class_string):
        """dynamically load a class from a string"""
        mod_name, class_str = full_class_string.rsplit(".", 1)
        __import__(mod_name)
        module = sys.modules[mod_name]
        return getattr(module, class_str)
