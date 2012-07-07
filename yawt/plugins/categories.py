import yawt.util

import os
import yaml
import re

flask_app = None
name = None

_category_dir = '_categories'
_category_file = _category_dir + '/categories.yaml'

default_config = {
    'category_dir': _category_dir,
    'category_file': _category_file,
    'base': ''
}

class CategoryNode(object):
    def __init__(self):
        self.count = 0
        self.category = ''
        self.url = ''
        self.subcategories = {}


class CategoryTree(object):
    def __init__(self, base=''):
        self.root = CategoryNode()
        self.base = base
      
    @staticmethod
    def from_dict(d):
        tree = CategoryTree()
        tree.root = CategoryTree._from_dict_r(d)
        return tree
    
    @staticmethod
    def _from_dict_r(d):
        node = CategoryNode()
        node.count = d['count']
        node.category = d['category']
        node.url = d['url']
        for cat in d['subcategories']:
            node.subcategories[cat] = CategoryTree._from_dict_r(d['subcategories'][cat])
        return node
        
    def add_item(self, path):
        self.root.count += 1
        
        pathelems = path.split('/')
        node = self.root
        url = self._get_base_url()
        for pe in pathelems:
            url += pe + '/'
            if pe not in node.subcategories:
                new_node = CategoryNode()
                new_node.category = pe
                new_node.url = url
                node.subcategories[pe] = new_node
            node = node.subcategories[pe]
            node.count += 1

    def del_item(self, path):
        self.root.count -= 1
        
        pathelems = path.split('/')
        node = self.root
        for pe in pathelems:
          
            if pe not in node.subcategories:
                break
           
            node.subcategories[pe].count -= 1
            if node.subcategories[pe].count == 0:
                del node.subcategories[pe]
                break
            else:
                node = node.subcategories[pe]    
            
    def get_dict(self):
        return self._get_dict_r(self.root)

    def _get_dict_r(self, root):
        node = {'count': root.count, 'category': root.category,
                'url': root.url, 'subcategories': {}}
        for category in root.subcategories:
            node['subcategories'][category] = \
                self._get_dict_r(root.subcategories[category])
        return node

    def _get_base_url(self):
        if self.base:
            return '/' + self.base + '/'
        else:
            return '/'
   

class CategoryCounter(object):
    def __init__(self):
        self._category_tree = None
       
    def pre_walk(self):
        self._category_tree = CategoryTree(_get_category_base())
    
    def visit_article(self, fullname):
        base = _get_category_base()
        if not fullname.startswith(base):
            return

        category = self._get_category(fullname)
        self._category_tree.add_item(category)
        
    def post_walk(self):
        self._save_info(_get_category_file(), self._category_tree.get_dict())
       
    def update(self, statuses):
        self._category_tree = CategoryTree.from_dict(_load_categories())
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','R']:
                continue
            
            category = self._get_category(fullname)
            if status == 'R':
                self._category_tree.del_item(category)
            elif status == 'A':
                self._category_tree.add_item(category)
                
        self.post_walk()

    def _get_category(self, fullname):
        base = _get_category_base()
        relname = re.sub('^%s/' % (base), '', fullname)
        return os.path.dirname(relname)
    
    def _save_info(self, filename, info):
        cat_dir = _get_category_dir()
        if not os.path.exists(cat_dir):
            os.mkdir(cat_dir)
        stream = file(filename, 'w')
        yaml.dump(info, stream)
        stream.close()

def init(app, plugin_name):
    global flask_app
    flask_app = app
    
    global name
    name = plugin_name
    
def template_vars():
    return {'categories':_load_categories()}

def walker(store):
    return CategoryCounter()

def updater(store):
    return CategoryCounter()

def _plugin_config():
    return flask_app.config[name]

def _get_category_dir():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['category_dir'])

def _get_category_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['category_file'])

def _get_category_base():
    base = _plugin_config()['base'].strip()
    return base.rstrip('/')

def _load_categories():
    return yawt.util.load_yaml(_get_category_file())
