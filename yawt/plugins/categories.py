import yawt.util

import os
import yaml
import re
 
def dict2tree(dict):
    tree = CategoryTree()
    tree.root = _dict2tree_r(dict)
    return tree

def _dict2tree_r(d):
    node = CategoryNode()
    node.count = d['count']
    node.category = d['category']
    node.url = d['url']
    for cat in d['subcategories']:
        node.subcategories[cat] = _dict2tree_r(d['subcategories'][cat])
    return node

def tree2dict(root):
    node = {'count': root.count, 'category': root.category,
            'url': root.url, 'subcategories': {}}
    for category in root.subcategories:
        node['subcategories'][category] = \
            tree2dict(root.subcategories[category])
    return node
    
class CategoryNode(object):
    def __init__(self):
        self.count = 0
        self.category = ''
        self.url = ''
        self.subcategories = {}


class CategoryTree(object):
    def __init__(self):
        self.root = CategoryNode()
            
    def add_item(self, categorypath):
        self.root.count += 1
        node = self.root
        url = ''
        for pathelem in categorypath.split('/'):
            url += pathelem + '/'
            if pathelem not in node.subcategories:
                new_node = CategoryNode()
                new_node.category = pathelem
                new_node.url = url
                new_node.count = 0
                node.subcategories[pathelem] = new_node
            node = node.subcategories[pathelem]
            node.count += 1

    def del_item(self, categorypath):
        self.root.count -= 1
        node = self.root
        for pathelem in categorypath.split('/'):
            if pathelem not in node.subcategories:
                break
            node.subcategories[pathelem].count -= 1
            if node.subcategories[pathelem].count == 0:
                del node.subcategories[pathelem]
                break
            else:
                node = node.subcategories[pathelem]
           
   
class CategoryCounter(object):
    def __init__(self, base, category_file):
        self._category_tree = None
        self._base = base
        self._category_file = category_file

    def pre_walk(self):
        self._category_tree = CategoryTree()
    
    def visit_article(self, fullname):
        if not fullname.startswith(self._base):
            return

        category = self._get_category(fullname)
        self._category_tree.add_item(category)
        
    def update(self, statuses):
        category_counts = yawt.util.load_yaml(self._category_file)
        self._category_tree = dict2tree(category_counts)
        
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
        
    def post_walk(self):
        yawt.util.save_yaml(self._category_file, tree2dict(self._category_tree.root))
          
    def _get_category(self, fullname):
        relname = re.sub('^%s/' % (self._base), '', fullname)
        return os.path.dirname(relname)
    
class CategoriesPlugin(object):
    def __init__(self):
        self.default_config = {
            'CATEGORY_DIR':  '_categories',
            'CATEGORY_FILE': '_categories/categories.yaml',
            'BASE': ''
        }
        
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

    def template_vars(self):
        def _prepend_base(dict, base):
            dict['url'] = base + "/" + dict['url']
            for subcat in dict['subcategories']:
                 _prepend_base(dict['subcategories'][subcat], base)
            
        categories = yawt.util.load_yaml(self._get_category_file())
        _prepend_base(categories, self._get_category_base())
        return {'categories': categories}

    def walker(self, store):
        return CategoryCounter(self._get_category_base(), self._get_category_file())

    def updater(self, store):
        return CategoryCounter(self._get_category_base(), self._get_category_file())

    def _plugin_config(self):
        return self.app.config[self.name]

    def _get_category_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['CATEGORY_DIR'])

    def _get_category_file(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['CATEGORY_FILE'])

    def _get_category_base(self):
        base = self._plugin_config()['BASE'].strip()
        return base.rstrip('/')

def create_plugin():
    return CategoriesPlugin()
