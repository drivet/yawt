import os
import yawt

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher
from flask import g, request
from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser


class SearchView(object):
    def __init__(self, fetcher, yawtview):
        self._yawtview = yawtview
        self._fetcher = fetcher
  
    def dispatch_request(self, flavour, category, search_text, page, page_size, base_url):
        articles = self._fetcher.fetch(category, 'content', unicode(search_text))
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, search_text, page_info, category)
        
    def _render_collection(self, flavour, articles, search_text, page_info, category):
        title = self._search_title(search_text)
        return self._yawtview.render_collection(flavour, articles, title, page_info, category)
                                                      
    def _search_title(self, search_text):
        return 'Search results for: "%s"' % search_text
 

class TextIndexer(ArticleIndexer):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        super(TextIndexer, self).__init__(store, index_dir, index_name, doc_root)

    def _get_schema_fields(self):
        return {'title': TEXT(stored=True), 'content': TEXT}
    
    def _get_article_fields(self, article):
        return {'title': unicode(article.title), 'content': unicode(article.content)}
    

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

        @app.route('/search/', methods=['POST', 'GET'])
        def full_text_search():
            return self._full_text_search(request, None, '')
        
        @app.route('/<path:category>/search/', methods=['POST', 'GET'])
        def full_text_search(category):
            return self._full_text_search(request, None, category)
        
        @app.route('/search/index', methods=['POST', 'GET'])
        def full_text_search_index():
            return self._full_text_search(request, None, '')
        
        @app.route('/<path:category>/search/index', methods=['POST', 'GET'])
        def full_text_search_index(category):
            return self._full_text_search(request, None, category)
        
        @app.route('/search/index.<flav>', methods=['POST', 'GET'])
        def full_text_search_index():
            return self._full_text_search(request, flav, '')
        
        @app.route('/<path:category>/search/index.<flav>', methods=['POST', 'GET'])
        def full_text_search_index(category):
            return self._full_text_search(request, flav, category)

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
    
    def _full_text_search(self, request, flav, category):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1
            
        search_text = request.args.get('searchtext', '')
        sv = self._create_search_view()
        return sv.dispatch_request(flav, category, search_text,
                                   page, g.config['YAWT_PAGE_SIZE'], request.base_url)

    def _create_search_view(self):
        return SearchView(ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name()),
                          YawtView(g.plugins, yawt.util.get_content_types()))


def create_plugin():
    return SearchPlugin()
