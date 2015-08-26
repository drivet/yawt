"""The YAWT Search plugin.

Implements full text search using Whoosh.
"""
from __future__ import absolute_import

from flask import current_app, request, g, Blueprint
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView
from yawtext.indexer import schema
from yawtext.base import Plugin


searchbp = Blueprint('search', __name__)


class SearchView(CollectionView):
    """The main SearchView.  Implements a fulltext search on the article
    content
    """

    methods = ['GET', 'POST']

    def query(self, category, *args, **kwargs):
        searchtext = unicode(request.args.get('searchtext', ''))
        query_str = 'content:' + searchtext
        if category:
            query_str += ' AND ' + category
        qparser = QueryParser('categories', schema=schema())
        return qparser.parse(unicode(query_str))

    def get_template_name(self):
        return current_app.config['YAWT_SEARCH_TEMPLATE']


class YawtSearch(Plugin):
    """The actual YAWT search plugin class"""

    def __init__(self, app=None):
        super(YawtSearch, self).__init__(app)

    def init_app(self, app):
        """Set some config default and register blueprint"""
        app.config.setdefault('YAWT_SEARCH_TEMPLATE', 'article_list')
        app.register_blueprint(searchbp)


@searchbp.context_processor
def _collection_title():
    searchtext = unicode(request.args.get('searchtext', ''))
    return {'collection_title': 'Found %s search results for "%s"' % (g.total_results, searchtext)}


searchbp.add_url_rule('/search/',
                      view_func=SearchView.as_view('full_text_search'))
searchbp.add_url_rule('/<path:category>/search/',
                      view_func=SearchView.as_view('full_text_search_cat'))
searchbp.add_url_rule('/search/index',
                      view_func=SearchView.as_view('full_text_search_index'))
searchbp.add_url_rule('/<path:category>/search/index',
                      view_func=SearchView.as_view('full_text_search_index_cat'))
searchbp.add_url_rule('/search/index.<flav>',
                      view_func=SearchView.as_view('full_text_search_index_flav'))
searchbp.add_url_rule('/<path:category>/search/index.<flav>',
                      view_func=SearchView.as_view('full_text_search_index_flav_cat'))
