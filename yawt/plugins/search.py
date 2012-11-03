import os
import yawt

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher
from flask import g, request, current_app
from flask.views import View

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser


class TextIndexer(ArticleIndexer):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        super(TextIndexer, self).__init__(store, index_dir, index_name, doc_root)

    def _get_schema_fields(self):
        return {'title': TEXT(stored=True), 'content': TEXT}
    
    def _get_article_fields(self, article):
        return {'title': unicode(article.title), 'content': unicode(article.content)}
    

class SearchView(View):
    methods = ['GET', 'POST']
    
    def __init__(self, plugin_config):
        self._plugin_config = plugin_config
   
    def dispatch_request(self, flavour=None, category=''):
        yawtview = YawtView(g.plugins, yawt.util.get_content_types())
        fetcher = ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name())
        
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        page_size = int(g.config['YAWT_PAGE_SIZE'])
        
        search_text = request.args.get('searchtext', '')
 
        articles = fetcher.fetch(category, 'content', unicode(search_text))
        if len(articles) < 1:
            return yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), request.base_url)
            return self._render_collection(yawtview, flavour, articles, search_text, page_info, category)
        
    def _render_collection(self, yawtview, flavour, articles, search_text, page_info, category):
        title = self._search_title(search_text)
        return yawtview.render_collection(flavour, articles, title, page_info, category)
                                                      
    def _search_title(self, search_text):
        return 'Search results for: "%s"' % search_text

    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(current_app, self._plugin_config['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config['INDEX_NAME']
    
class SearchPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'fulltextsearch',
            'BASE': ''
        }
        
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        app.add_url_rule('/search/', view_func = self._view_func('full_text_search'))
        app.add_url_rule('/<path:category>/search/',
                         view_func = self._view_func('full_text_search_cat'))
        app.add_url_rule('/search/index', view_func = self._view_func('full_text_search_index'))
        app.add_url_rule('/<path:category>/search/index',
                         view_func = self._view_func('full_text_search_index_cat'))
        app.add_url_rule('/search/index.flav', view_func = self._view_func('full_text_search_index_flav'))
        app.add_url_rule('/<path:category>/search/index.flav',
                         view_func = self._view_func('full_text_search_index_flav_cat'))
        
    def walker(self, store):
        return TextIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return TextIndexer(store, self._get_index_dir(), self._get_index_name())

    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']

    def _plugin_config(self):
        return self.app.config[self.name]
    
    def _view_func(self, endpoint):
        return SearchView.as_view(endpoint, plugin_config = self._plugin_config())

        
def create_plugin():
    return SearchPlugin()
