from flask import g
import yaml
import os
import re

class Plugins(object):
    def __init__(self, plugins):
        self._plugins = plugins
        
    def template_vars(self, template_vars):
        for p in self._plugins.keys():
            if has_method(self._plugins[p], 'template_vars'):
                template_vars[p] = self._plugins[p].template_vars()
        return template_vars

    def on_article_fetch(self, article):
        for p in self._plugins.values():
            if has_method(p, 'on_article_fetch'):
                article = p.on_article_fetch(article)
        return article

    def walkers(self, store):
        return filter(lambda w: w,
                      map(lambda p: has_method(p, 'walker') and p.walker(store),
                          self._plugins.values()))

    def updaters(self, store):     
        return filter(lambda w: w,
                       map(lambda p: has_method(p, 'updater') and p.updater(store),
                           self._plugins.values()))
   
    
class Date(object):
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
        
    def __str__(self):
        dl = ["%04d" % (self.year)]
        if self.month is not None:
            dl.append("%02d" % (self.month))
        if self.day is not None:
            dl.append("%02d" % (self.day))
        return ' / '.join(dl)
    
def has_method(obj, method):
    return hasattr(obj, method) and callable(getattr(obj, method))
    
def load_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.load(f)

def save_yaml(filename, obj):
    _ensure_path(os.path.dirname(filename))
    with open(filename, 'w') as f:
        yaml.dump(obj, f)

def save_string(filename, str):
    _ensure_path(os.path.dirname(filename))
    with open(filename, 'w') as f:
        f.write(str)

def get_abs_path(blogpath, path):
    if os.path.isabs(path):
        return path
    else:
        return os.path.join(blogpath, path)

def get_abs_path_app(app, path):
    return get_abs_path(app.config['YAWT_BLOGPATH'], path)

def get_base_url(app):
    return app.config['YAWT_BASE_URL'] or request.url_root
        
def _ensure_path(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_content_types():
    def _extract_type(key):
        m = re.compile('YAWT_CONTENT_TYPES_(.*)').match(key)
        if m:
            return (m.group(1).lower(), g.config[m.group(0)])
        return None
    return dict(filter(None, map(_extract_type, g.config.keys())))
