from flask import current_app, g, Blueprint
import jsonpickle
from yawt.utils import save_file, load_file
import os
import re

categorycountsbp = Blueprint('categorycounts', __name__)

def _config(key):
    return current_app.config[key]

def fullname(repofile):
    content_root = _config('YAWT_CONTENT_FOLDER')
    if not repofile.startswith(content_root):
        return None
    rel_filename = re.sub('^%s/' % (content_root), '', repofile) 
    name, ext = os.path.splitext(rel_filename)
    ext = ext[1:]
    if ext not in _config('YAWT_ARTICLE_EXTENSIONS'):
        return None 
    return name

class CategoryCount(object):
    def __init__(self):
        self.category = ''
        self.count = 0
        self.children = []

def _split_category(category):
    (head, rest) = category, ''
    if '/' in category:
        (head, rest) = category.split('/',1)
    return (head, rest)

def count_category(root_node, category):
    root_node.count += 1
    if category:
        (head, rest) = _split_category(category)
        next_node = None
        for c in root_node.children:
            if c.category == head:
                next_node = c
        if next_node is None:
            next_node = CategoryCount()
            next_node.category = head
            root_node.children.append(next_node)
        count_category(next_node, rest)
    
def remove_category(root_node, category):
    root_node.count -= 1
    if category:
        (head, rest) = _split_category(category)
        for c in root_node.children:
            if c.category == head:
                remove_category(c, rest)
                break
        root_node.children = [c for c in root_node.children if c.count > 0]
    

@categorycountsbp.app_context_processor
def categorycounts():
    catcountfile = current_app.config['YAWT_CATEGORYCOUNT_FILE']
    tvars = {}
    if os.path.isfile(catcountfile):
        countbase = current_app.config['YAWT_CATEGORYCOUNT_BASE']
        if not countbase.endswith('/'):
            countbase += '/'
        counts = jsonpickle.decode(load_file(catcountfile))
        tvars = {'categorycounts': counts, 'categorycountbase': countbase }
    return tvars


class YawtCategoryCount(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.category_counts = CategoryCount()

    def init_app(self, app):
        app.config.setdefault('YAWT_CATEGORYCOUNT_BASE', '')
        app.config.setdefault('YAWT_CATEGORYCOUNT_FILE', '/tmp/categorycounts')
        app.register_blueprint(categorycountsbp)

    def on_pre_walk(self):
        self.category_counts = CategoryCount()
        countbase = current_app.config['YAWT_CATEGORYCOUNT_BASE']
        self.category_counts.category = countbase

    def on_visit_article(self, article):
        category = article.info.category
        countbase = current_app.config['YAWT_CATEGORYCOUNT_BASE']
        if category == countbase or category.startswith(countbase):
            category = self._adjust_category_for_base(category, countbase)
            count_category(self.category_counts, category)

    def _adjust_category_for_base(self, category, countbase):
        category = re.sub('^%s' % (countbase), '', category)
        if category.startswith('/'):
            category = category[1:]
        return category

    def on_post_walk(self): 
        pickled_counts = jsonpickle.encode(self.category_counts)
        save_file(current_app.config['YAWT_CATEGORYCOUNT_FILE'], pickled_counts)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_counts = load_file(current_app.config['YAWT_CATEGORYCOUNT_FILE'])
        self.category_counts = jsonpickle.decode(pickled_counts)

        for f in files_removed + files_modified: 
            name = fullname(f)
            countbase = current_app.config['YAWT_CATEGORYCOUNT_BASE']
            category = unicode(os.path.dirname(name))
            category = self._adjust_category_for_base(category, countbase)
            remove_category(self.category_counts, category)

        for f in files_modified + files_added:
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.on_post_walk()

