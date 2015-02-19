from flask import current_app, request, g, Blueprint
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh

searchbp = Blueprint('search', __name__)

class SearchView(CollectionView): 
    methods = ['GET', 'POST']

    def query(self, category, *args, **kwargs):
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
        app.config.setdefault('YAWT_SEARCH_TEMPLATE', 'article_list')
        app.register_blueprint(searchbp)


@searchbp.context_processor
def collection_title():
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
