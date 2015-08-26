"""YAWT extension for category management

This extension registers a Blueprint and provides - a template varable with the
article counts for all the categories (folders), on the system.
"""
from __future__ import absolute_import

import re
import os

import jsonpickle
from flask import current_app, g, Blueprint
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every

from yawtext.collections import CollectionView
from yawtext.indexer import schema
from yawt.utils import save_file, load_file, fullname, normalize_renames
from yawtext.hierarchy_counter import HierarchyCount
from yawtext.base import Plugin


categoriesbp = Blueprint('categories', __name__)


def _abs_category_count_file():
    root = current_app.yawt_root_dir
    countfile = current_app.config['YAWT_CATEGORY_COUNT_FILE']
    state_folder = current_app.config['YAWT_STATE_FOLDER']
    return os.path.join(root, state_folder, countfile)


def _slice_base_off_category(category, countbase):
    category = re.sub('^%s' % (countbase), '', category)
    if category.startswith('/'):
        category = category[1:]
    return category


# Feels very wrong
def _adjust_base_for_category():
    countbase = current_app.config['YAWT_CATEGORY_BASE']
    if countbase.startswith('/'):
        countbase = countbase[1:]
    return countbase


@categoriesbp.app_context_processor
def _categorycounts():
    """Context processor to provide a category counst to a template"""
    catcountfile = _abs_category_count_file()
    tvars = {}
    if os.path.isfile(catcountfile):
        countbase = current_app.config['YAWT_CATEGORY_BASE']
        if not countbase.endswith('/'):
            countbase += '/'

        counts = jsonpickle.decode(load_file(catcountfile))
        tvars = {'categorycounts': counts, 'categorycountbase': countbase}
    return tvars


class CategoryView(CollectionView):
    """YAWT Category view class"""
    def query(self, category, *args, **kwargs):
        """Return the Whoosh query to be used for fetching articles in a
        certain category.
        """
        if category:
            qparser = QueryParser('categories', schema=schema())
            return qparser.parse(unicode(category))
        else:
            return Every()

    def get_template_name(self):
        """Return the template to be used for category collections"""
        return current_app.config['YAWT_CATEGORY_TEMPLATE']

    def is_load_articles(self, flav):
        return flav in current_app.config['YAWT_CATEGORY_FULL_ARTICLE_FLAVOURS']


class YawtCategories(Plugin):
    """YAWT category extension class"""
    def __init__(self, app=None):
        super(YawtCategories, self).__init__(app)
        self.category_counts = HierarchyCount()

    def init_app(self, app):
        """Register the bluepriont and set some default config"""
        app.config.setdefault('YAWT_CATEGORY_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_CATEGORY_BASE', '')
        app.config.setdefault('YAWT_CATEGORY_COUNT_FILE', '_categorycounts')
        app.config.setdefault('YAWT_CATEGORY_FULL_ARTICLE_FLAVOURS', [])
        app.register_blueprint(categoriesbp)

    def on_article_fetch(self, article):
        """Take the article category and construct a list of progressively more
        general categories.
        """
        category = article.info.category
        categories = [category]
        while '/' in category:
            category = category.rsplit('/', 1)[0]
            categories.append(category)
        article.info.categories = categories
        return article

    def on_404(self, name, flavour):
        """auto generate the index page if one was requested.
        Name is fullname.
        """
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
        """Start tracking a new HierarchyCounts instance"""
        self.category_counts = HierarchyCount()
        self.category_counts.category = _adjust_base_for_category()

    def on_visit_article(self, article):
        """Register this article against the HierarchyCounts instance"""
        category = article.info.category
        countbase = _adjust_base_for_category()  # blech
        if category == countbase or category.startswith(countbase):
            category = _slice_base_off_category(category, countbase)
            self.category_counts.count_hierarchy(category)

    def on_post_walk(self):
        """Save HierarchyCounts to disk"""
        pickled_counts = jsonpickle.encode(self.category_counts)
        save_file(_abs_category_count_file(), pickled_counts)

    def on_files_changed(self, added, modified, deleted, renamed):
        """Register changed files against HierarchyCounts"""
        added, modified, deleted = \
            normalize_renames(added, modified, deleted, renamed)
        pickled_counts = load_file(_abs_category_count_file())
        self.category_counts = jsonpickle.decode(pickled_counts)

        for f in deleted + modified:
            name = fullname(f)
            if name:
                countbase = _adjust_base_for_category()  # blech
                category = unicode(os.path.dirname(name))
                category = _slice_base_off_category(category, countbase)
                self.category_counts.remove_hierarchy(category)

        for f in modified + added:
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.on_post_walk()
