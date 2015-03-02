from flask import current_app, g, Blueprint
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every
from yawtext.collections import CollectionView, yawtwhoosh
from yawt.utils import save_file, load_file
import re
import os
import jsonpickle

categoriesbp = Blueprint('categories', __name__)

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
    

def abs_category_count_file():
    root = current_app.yawt_root_dir
    countfile = current_app.config['YAWT_CATEGORY_COUNT_FILE']
    state_folder = current_app.config['YAWT_STATE_FOLDER']
    return os.path.join(root, state_folder, countfile)


@categoriesbp.app_context_processor
def categorycounts():
    catcountfile = abs_category_count_file()
    tvars = {}
    if os.path.isfile(catcountfile):
        countbase = current_app.config['YAWT_CATEGORY_BASE']
        if not countbase.endswith('/'):
            countbase += '/'

        counts = jsonpickle.decode(load_file(catcountfile))
        tvars = {'categorycounts': counts, 'categorycountbase': countbase }
    return tvars


class CategoryView(CollectionView):
    def query(self, category, *args, **kwargs):
        if category:
            qp = QueryParser('categories', schema=yawtwhoosh().schema())
            return qp.parse(unicode(category))
        else:
            return Every()

    def get_template_name(self):
        return current_app.config['YAWT_CATEGORY_TEMPLATE']


class YawtCategories(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.category_counts = CategoryCount()

    def init_app(self, app):
        app.config.setdefault('YAWT_CATEGORY_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_CATEGORY_BASE', '')
        app.config.setdefault('YAWT_CATEGORY_COUNT_FILE', 'categorycounts')
        app.register_blueprint(categoriesbp)

    def on_article_fetch(self, article):
        category = article.info.category
        categories = [category]
        while('/' in category):
            category = category.rsplit('/', 1)[0]
            categories.append(category)
        article.info.categories = categories
        return article

    def on_404(self, fullname, flavour):
        """auto generate the index page if one was requested"""
        index_file = current_app.config['YAWT_INDEX_FILE']
        if fullname != index_file and not fullname.endswith('/' + index_file):
            # this doesn't look like an index file fullname
            return False

        category = ''
        if fullname.endswith('/' + index_file):
            category = fullname.rsplit('/', 1)[0]

        view_func = CategoryView.as_view('category_path')
        return view_func(category, flavour)

    def on_pre_walk(self):
        self.category_counts = CategoryCount()
        countbase = current_app.config['YAWT_CATEGORY_BASE']
        self.category_counts.category = countbase

    def on_visit_article(self, article): 
        category = article.info.category
        countbase = current_app.config['YAWT_CATEGORY_BASE']
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
        save_file(abs_category_count_file(), pickled_counts)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_counts = load_file(abs_category_count_file())
        self.category_counts = jsonpickle.decode(pickled_counts)

        for f in files_removed + files_modified:
            name = fullname(f)
            countbase = current_app.config['YAWT_CATEGORY_BASE']
            category = unicode(os.path.dirname(name))
            category = self._adjust_category_for_base(category, countbase)   
            remove_category(self.category_counts, category)

        for f in files_modified + files_added: 
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.on_post_walk()
