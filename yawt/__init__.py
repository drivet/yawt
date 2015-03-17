from flask import Flask
import re
import os
import jinja2
import importlib

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
YAWT_STATE_FOLDER = '_state'
YAWT_EXTENSIONS = []

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

def init_extensions(app, extensions):
    for ext in extensions:
        ext.init_app(app)

def load_class(full_class_string):
    """
    dynamically load a class from a string
    """

    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, class_str)

def load_extension_info(extension_class_names):
    extension_info = [{},[]]
    for class_name in extension_class_names:
        cls = load_class(class_name)
        cls_instance = cls()
        extension_info[0][class_name] = cls_instance 
        extension_info[1].append(cls_instance)
    return extension_info

def load_extensions(app, extension_info):
    if extension_info is None:
        app.extension_info = load_extension_info(app.config['YAWT_EXTENSIONS'])
    else:
        app.extension_info = extension_info

    if app.extension_info:
        init_extensions(app, app.extension_info[1])

def configure(root_dir, app, config, extension_info):
    import sys
    old_path = sys.path
    sys.path.append(root_dir)
    configure_app(app, config)
    load_extensions(app, extension_info)
    sys.path = old_path

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
    
    configure(root_dir, app, config, extension_info)

    from yawt.main import yawtbp
    app.register_blueprint(yawtbp)

    return app
