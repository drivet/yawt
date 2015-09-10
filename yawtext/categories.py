"""YAWT extension for category management

This extension registers a Blueprint and provides - a template varable with the
article counts for all the categories (folders), on the system.
"""
from __future__ import absolute_import

import os
import re

import jsonpickle
from flask import current_app, g, Blueprint

from yawt.utils import load_file, fullname, cfg, abs_state_folder
from yawtext import HierarchyCount, Plugin, StateFiles, state_context_processor
from yawtext.collections import CollectionView


categoriesbp = Blueprint('categories', __name__)


def _slice_base(category, countbase):
    category = re.sub('^%s' % (countbase), '', category)
    if category.startswith('/'):
        category = category[1:]
    return category


# Feels very wrong
def _adjust_base_for_category(countbase):
    if countbase.startswith('/'):
        countbase = countbase[1:]
    return countbase


def _get_bases():
    if cfg('YAWT_CATEGORY_BASE'):
        return cfg('YAWT_CATEGORY_BASE')
    else:
        return ['']


@categoriesbp.app_context_processor
def _categorycounts():
    """Context processor to provide a category counts to a template"""
    return state_context_processor('YAWT_CATEGORY_COUNT_FILE',
                                   'YAWT_CATEGORY_BASE',
                                   'categorycounts')


class CategoryView(CollectionView):
    """YAWT Category view class"""
    def query(self, category, *args, **kwargs):
        """Return the Whoosh query to be used for fetching articles in a
        certain category.
        """
        return unicode(category)

    def get_template_name(self):
        """Return the template to be used for category collections"""
        return current_app.config['YAWT_CATEGORY_TEMPLATE']

    def is_load_articles(self, flav):
        return flav in current_app.config['YAWT_CATEGORY_FULL_ARTICLE_FLAVOURS']


class YawtCategories(Plugin):
    """YAWT category extension class"""
    def __init__(self, app=None):
        super(YawtCategories, self).__init__(app)
        self.category_counts_map = {}

    def init_app(self, app):
        """Register the bluepriont and set some default config"""
        app.config.setdefault('YAWT_CATEGORY_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_CATEGORY_BASE', [''])
        app.config.setdefault('YAWT_CATEGORY_COUNT_FILE', 'categorycounts')
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
        self.category_counts_map = {}
        for base in _get_bases():
            base = _adjust_base_for_category(base)
            self.category_counts_map[base] = HierarchyCount()

    def on_visit_article(self, article):
        """Register this article against the HierarchyCounts instance"""
        for base in [b for b in _get_bases() if article.info.under(b)]:
            category = article.info.category
            countbase = _adjust_base_for_category(base)  # blech
            if category == countbase or category.startswith(countbase):
                category = _slice_base(category, countbase)
                self.category_counts_map[base].add(category)

    def on_post_walk(self):
        """Save HierarchyCounts to disk"""
        statefiles = StateFiles(abs_state_folder(),
                                cfg('YAWT_CATEGORY_COUNT_FILE'))
        statefiles.save_state_files(self.category_counts_map)

    def on_files_changed(self, changed):
        """Register changed files against HierarchyCounts"""
        changed = changed.content_changes().normalize()
        statefiles = StateFiles(abs_state_folder(),
                                cfg('YAWT_CATEGORY_COUNT_FILE'))
        self.category_counts_map = statefiles.load_state_files(_get_bases())
        for base in _get_bases():
            for repofile in changed.deleted + changed.modified:
                name = fullname(repofile)
                if name:
                    category = unicode(os.path.dirname(name))
                    if category.startswith(base):
                        countbase = _adjust_base_for_category(base)  # blech
                        category = _slice_base(category, countbase)
                        self.category_counts_map[base].remove(category)

        map(self.on_visit_article,
            g.site.fetch_articles_by_repofiles(changed.modified + changed.added))

        self.on_post_walk()
