"""Initialization code for YAWT"""

from __future__ import absolute_import

import re
import os
import importlib
import logging

from flask import Flask
import jinja2


# default configuration
YAWT_BASE_URL = 'http://www.awesome.net/blog'
YAWT_LOG_LEVEL = logging.INFO
YAWT_CONTENT_FOLDER = 'content'
YAWT_DRAFT_FOLDER = 'drafts'
YAWT_TEMPLATE_FOLDER = 'templates'
YAWT_STATE_FOLDER = '_state'
YAWT_DEFAULT_FLAVOUR = 'html'
YAWT_INDEX_FILE = 'index'
YAWT_ARTICLE_TEMPLATE = 'article'
YAWT_ARTICLE_EXTENSIONS = ['txt']
YAWT_EXTENSIONS = []
YAWT_META_TYPES = {}


def _get_content_types(config):
    def _extract_type(key):
        match = re.compile('YAWT_CONTENT_TYPE_(.*)').match(key)
        if match:
            return (match.group(1).lower(), config[match.group(0)])
        return None
    return dict(filter(None, map(_extract_type, config.keys())))


def _configure_app(app, config):
    app.config.from_object(__name__)
    if config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_object(config)
    app.content_types = _get_content_types(app.config)


def _init_extensions(app, extensions):
    for ext in extensions:
        ext.init_app(app)


def _load_class(full_class_string):
    """
    dynamically load a class from a string
    """

    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, class_str)


def _load_extension_info(extension_class_names):
    extension_info = [{}, []]
    for class_name in extension_class_names:
        cls = _load_class(class_name)
        cls_instance = cls()
        extension_info[0][class_name] = cls_instance
        extension_info[1].append(cls_instance)
    return extension_info


def _load_extensions(app, extension_info):
    if extension_info is None:
        app.extension_info = _load_extension_info(app.config['YAWT_EXTENSIONS'])
    else:
        app.extension_info = extension_info

    if app.extension_info:
        _init_extensions(app, app.extension_info[1])


def _configure(root_dir, app, config, extension_info):
    import sys
    old_path = sys.path
    sys.path.append(root_dir)
    _configure_app(app, config)
    _load_extensions(app, extension_info)
    sys.path = old_path


def _setup_templates(root_dir, app):
    template_folder = app.config['YAWT_TEMPLATE_FOLDER']
    path_to_templates = os.path.join(root_dir, template_folder)
    app.jinja_loader = jinja2.FileSystemLoader(path_to_templates)


def create_app(root_dir,
               static_folder='static',
               static_url_path='/static',
               config=None,
               extension_info=None):
    """The main YAWT Flask app factory"""
    app = Flask(__name__,
                static_folder=os.path.join(root_dir, static_folder),
                static_url_path=static_url_path,
                instance_path=root_dir,
                instance_relative_config=True)

    app.yawt_root_dir = root_dir
    app.yawt_static_folder = static_folder

    _configure(root_dir, app, config, extension_info)
    app.logger.setLevel(app.config['YAWT_LOG_LEVEL'])
    _setup_templates(root_dir, app)

    from yawt.main import yawtbp
    app.register_blueprint(yawtbp)

    return app
