from flask import current_app, g, Blueprint
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every
from yawtext.collections import CollectionView, yawtwhoosh
from yawt.utils import save_file, load_file, fullname
import re
import os
import jsonpickle
from yawtext.hierarchy_counter import HierarchyCount

categoriesbp = Blueprint('categories', __name__)

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
        self.category_counts = HierarchyCount()

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

    def on_404(self, name, flavour):
        """auto generate the index page if one was requested.  Name is fullname."""
        index_file = current_app.config['YAWT_INDEX_FILE']
        if name != index_file and not name.endswith('/' + index_file):
            # this doesn't look like an index file name
            return False

        category = ''
        if name.endswith('/' + index_file):
            category = name.rsplit('/', 1)[0]

        view_func = CategoryView.as_view('category_path')
        return view_func(category, flavour)

    def on_pre_walk(self):
        self.category_counts = HierarchyCount()
        self.category_counts.category = self._adjust_base_for_category()

    def on_visit_article(self, article): 
        category = article.info.category
        countbase = self._adjust_base_for_category() #blech
        if category == countbase or category.startswith(countbase):
            category = self.slice_base_off_category(category, countbase)
            self.category_counts.count_hierarchy(category)
   
    def slice_base_off_category(self, category, countbase):
        category = re.sub('^%s' % (countbase), '', category)
        if category.startswith('/'):
            category = category[1:]
        return category

    # Feels very wrong
    def _adjust_base_for_category(self):
        countbase = current_app.config['YAWT_CATEGORY_BASE']
        if countbase.startswith('/'):
            countbase = countbase[1:]
        return countbase

    def on_post_walk(self): 
        pickled_counts = jsonpickle.encode(self.category_counts)
        save_file(abs_category_count_file(), pickled_counts)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_counts = load_file(abs_category_count_file())
        self.category_counts = jsonpickle.decode(pickled_counts)

        for f in files_removed + files_modified:
            name = fullname(f)
            if name:
                countbase = current_app.config['YAWT_CATEGORY_BASE']
                category = unicode(os.path.dirname(name))
                category = self.slice_base_off_category(category, countbase)   
                self.category_counts.remove_hierarchy(category)

        for f in files_modified + files_added: 
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.on_post_walk()
