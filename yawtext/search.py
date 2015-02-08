from flask import current_app, request
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh


class SearchView(CollectionView): 
    methods = ['GET', 'POST']

    def query(self, category):
        searchtext = unicode(request.args.get('searchtext', ''))
        query_str = 'content:' + searchtext
        if category:
            query_str += ' AND ' + category
        qp = QueryParser('categories', schema=yawtwhoosh().schema())
        return qp.parse(unicode(query_str))
        
    def get_template_name(self):
        return current_app.config['YAWT_SEARCH_TEMPLATE']


class YawtSearch(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_SEARCH_TEMPLATE', 'article_collection')
        app.add_url_rule('/search/', 
                         view_func = SearchView.as_view('full_text_search'))
        app.add_url_rule('/<path:category>/search/',
                         view_func = SearchView.as_view('full_text_search_cat'))
        app.add_url_rule('/search/index', 
                         view_func = SearchView.as_view('full_text_search_index'))
        app.add_url_rule('/<path:category>/search/index',
                         view_func = SearchView.as_view('full_text_search_index_cat'))
        app.add_url_rule('/search/index.<flav>', 
                         view_func = SearchView.as_view('full_text_search_index_flav'))
        app.add_url_rule('/<path:category>/search/index.<flav>',
                         view_func = SearchView.as_view('full_text_search_index_flav_cat'))
