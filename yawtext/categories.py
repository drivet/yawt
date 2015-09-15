"""YAWT extension for category management

This extension registers a Blueprint and provides - a template varable with the
article counts for all the categories (folders), on the system.
"""
from __future__ import absolute_import

import os
import re

from flask import current_app, Blueprint

from yawt.utils import cfg
from yawtext import HierarchyCount, Plugin, SummaryProcessor, BranchedVisitor
from yawtext.collections import CollectionView


# Category pages plugin


class YawtCategories(Plugin):
    """YAWT category extension class"""
    def __init__(self, app=None):
        super(YawtCategories, self).__init__(app)

    def init_app(self, app):
        """Register the bluepriont and set some default config"""
        app.config.setdefault('YAWT_CATEGORY_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_CATEGORY_FULL_ARTICLE_FLAVOURS', [])

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


# Category Counter plugin
#
#
#
categoriesbp = Blueprint('categories', __name__)


@categoriesbp.app_context_processor
def _categorycounts():
    """Context processor to provide a category counts to a template"""
    return SummaryProcessor.context_processor('YAWT_CATEGORY_COUNT_FILE',
                                              'YAWT_CATEGORY_BASE',
                                              'categorycounts')

class YawtCategoryCounter(BranchedVisitor):
    """The Yawt category counter plugin"""
    def __init__(self, app=None):
        super(YawtCategoryCounter, self).__init__('YAWT_CATEGORY_BASE',
                                                  CategoryProcessor,
                                                  app)

    def init_app(self, app):
        """set some default config"""
        app.config.setdefault('YAWT_CATEGORY_BASE', [''])
        app.config.setdefault('YAWT_CATEGORY_COUNT_FILE', 'categorycounts')
        app.register_blueprint(categoriesbp)


class CategoryProcessor(SummaryProcessor):
    """Subclass of SummaryProcessor which counts categories under a root"""
    def __init__(self, root=''):
        super(CategoryProcessor, self).__init__(root, '',
                                                cfg('YAWT_CATEGORY_COUNT_FILE'))

    def _init_summary(self):
        self.summary = HierarchyCount()

    def on_visit_article(self, article):
        category = article.info.category
        if category == self.root or category.startswith(self.root):
            category = self._slice_base(category, self.root)
            self.summary.add(category)

    def unvisit(self, name):
        category = unicode(os.path.dirname(name))
        if category.startswith(self.root):
            category = self._slice_base(category, self.root)
            self.summary.remove(category)

    @staticmethod
    def _slice_base(category, countbase):
        category = re.sub('^'+countbase, '', category)
        if category.startswith('/'):
            category = category[1:]
        return category
