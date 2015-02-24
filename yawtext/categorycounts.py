from flask import current_app, g, Blueprint
import jsonpickle
from yawt.utils import save_file, load_file
import os

categorycountsbp = Blueprint('categorycounts', __name__)

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

def count_category(node, category):
    node.count += 1
    (head, rest) = _split_category(category)
    node.category = head
    if rest:
        child_category = rest.split('/',1)[0]
        next_node = None
        for c in node.children:
            if c.category == child_category:
                next_node = c
        if next_node is None:
            next_node = CategoryCount()
            node.children.append(next_node)
        count_category(next_node, rest)
    
def remove_category(node, category):
    node.count -= 1
    if category:
        (head, rest) = _split_category(category)
        for c in node.children:
            if c.category == head:
                remove_category(c, rest)
                break
        node.children = [c for c in node.children if c.count > 0]
    

@categorycountsbp.app_context_processor
def categorycounts():
    catcountfile = current_app.config['YAWT_CATEGORYCOUNT_FILE']
    tvars = {}
    if os.path.isfile(catcountfile):
        countbase = current_app.config['YAWT_CATEGORYCOUNT_BASE']
        if not countbase.endswith('/'):
            countbase += '/'
        counts = jsonpickle.decode(load_file(catcountfile))
        tvars = {'categorycounts': counts,
                 'categorycountbase': countbase }
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

    def on_visit_article(self, article):
        count_category(self.category_counts, article.info.category)

    def on_post_walk(self): 
        pickled_counts = jsonpickle.encode(self.category_counts)
        save_file(current_app.config['YAWT_CATEGORYCOUNT_FILE'], pickled_counts)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_counts = load_file(current_app.config['YAWT_CATEGORYCOUNT_FILE'])
        self.category_counts = jsonpickle.decode(pickled_counts)

        for f in files_removed + files_modified: 
            article = g.store.fetch_article_by_repofile(f)
            remove_category(self.category_counts, article.info.category)

        for f in files_modified + files_added:
            article = g.store.fetch_article_by_repofile(f)
            self.on_visit_article(article)

        self.on_post_walk()

