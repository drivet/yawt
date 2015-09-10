"""YAWT Collections extension module

Provides some base functionality for all modules wishing to implement a
collection View
"""
from __future__ import absolute_import

from math import ceil

from flask import current_app, g, request, Blueprint, abort
from flask.views import View
from jinja2 import TemplatesNotFound

from yawt.article import Article
from yawt.utils import is_loaded
from yawt.view import render
from yawtext import Plugin
from yawtext.indexer import search_page


collectionsbp = Blueprint('paging', __name__)


@collectionsbp.before_app_request
def _before_request():
    try:
        g.page = int(request.args.get('page', '1'))
    except ValueError:
        g.page = 1
    except KeyError:
        g.page = 1

    try:
        g.pagelen = int(request.args.get('pagelen', '10'))
    except ValueError:
        g.pagelen = current_app.config['YAWT_COLLECTIONS_DEFAULT_PAGELEN']
    except KeyError:
        g.pagelen = current_app.config['YAWT_COLLECTIONS_DEFAULT_PAGELEN']


class YawtCollections(Plugin):
    """YAWT Collection extension class"""
    def __init__(self, app=None):
        super(YawtCollections, self).__init__(app)

    def init_app(self, app):
        """Register Blueprint and set default values"""
        app.config.setdefault('YAWT_COLLECTIONS_DEFAULT_PAGELEN', 10)
        app.config.setdefault('YAWT_COLLECTIONS_SORT_FIELD', None)
        app.register_blueprint(collectionsbp)


class CollectionView(View):
    """YAWT Collection view class"""
    def dispatch_request(self, category='', flav=None, *args, **kwargs):
        """Query whoosh for collection of articles.  Sort the articles.  Setup
        up pagination variables in the g variables.  Finally render the
        template, or abort with a 404 if you don't find a template.
        """
        ainfos, total = [], 0
        if is_loaded('yawtext.indexer.YawtIndexer'):
            query = self.query(category, *args, **kwargs)
            sortfield = current_app.config['YAWT_COLLECTIONS_SORT_FIELD']
            ainfos, total = search_page(query=query,
                                        sortedby=sortfield,
                                        page=g.page, pagelen=g.pagelen,
                                        reverse=True)
        g.total_results = total
        g.total_pages = int(ceil(float(g.total_results)/g.pagelen))
        g.has_prev_page = g.page > 1
        g.has_next_page = g.page < g.total_pages
        g.prev_page = g.page - 1
        g.next_page = g.page + 1

        articles = []
        for ainfo in ainfos:
            if self.is_load_articles(flav):
                article = g.site.fetch_article_by_info(ainfo)
            else:
                article = Article()
                article.info = ainfo
            articles.append(article)

        try:
            return render(self.get_template_name(), category, 'index',
                          flav, {'articles': articles})
        except TemplatesNotFound:
            abort(404)

    def query(self, category, *args, **kwargs):
        """Always passed a category, and the rest varies by collection type"""
        raise NotImplementedError()

    def get_template_name(self):
        """Return the template name for the collection view"""
        raise NotImplementedError()

    def is_load_articles(self, flav):
        """Return True if article content is meant to be loaded along with
        the infos
        """
        return False
