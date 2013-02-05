import os
import yawt

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher, ListIndexView
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
    

class SearchView(ListIndexView):
    methods = ['GET', 'POST']
    
    def _title(self, *args, **kwargs):
        return 'Search results for: "%s"' % request.args.get('searchtext', '')
    
    def _default_field(self, *args, **kwargs):
        return 'content'
    
    def _query(self, *args, **kwargs):
        return unicode(request.args.get('searchtext', ''))
    
class SearchPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'fulltextsearch',
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
        app.add_url_rule('/search/index.<flav>', view_func = self._view_func('full_text_search_index_flav'))
        app.add_url_rule('/<path:category>/search/index.<flav>',
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
