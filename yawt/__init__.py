from flask import Flask
import re
import os
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

def load_extension_info():
    try:
        import ext
        return ext.extension_info
    except ImportError:
        return None

def load_extensions(app, extension_info):
    if extension_info is None:
        app.extension_info = load_extension_info()
    else:
        app.extension_info = extension_info

    if app.extension_info:
        init_app_fn = app.extension_info[2]
        init_app_fn(app)

def create_app(root_dir,
               template_folder = 'templates', 
               static_folder = 'static', 
               static_url_path = '/static', 
               config = None, 
               extension_info = None):
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
    
    configure_app(app, config)
    load_extensions(app, extension_info)

    from yawt.main import yawtbp
    app.register_blueprint(yawtbp)

    return app
