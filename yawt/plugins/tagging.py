import yawt.util
import yaml
import os

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher, ListIndexView
from flask import g, request, url_for, current_app

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser
import yawt.utils

def tag_url(category, tag):
    if category:
        return url_for('tag_category_canonical', category=category, tag=tag)
    else:
        return url_for('tag_canonical', tag=tag)
    
def article_tags(article):
    tags = []
    tagdata = article.get_metadata('tags', '')
    if tagdata is not '':
        tags = tagdata.split(',')
    return tags

class TagIndexer(ArticleIndexer):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        super(TagIndexer, self).__init__(store, index_dir, index_name, doc_root)

    def _get_schema_fields(self):
        return {'fullname': ID(stored=True), 'tags': KEYWORD(commas=True)}
    
    def _get_article_fields(self, article):
        tags = article.get_metadata('tags', '')
        return {'fullname': unicode(article.fullname), 'tags': unicode(tags)}

     
class TagView(ListIndexView):
    def _title(self, tag, *args, **kwargs):
        return 'Tag results for: "%s"' % tag
    
    def _default_field(self, *args, **kwargs):
        return 'tags'
    
    def _query(self, tag, *args, **kwargs):
        return unicode(tag)
    

class TaggingPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'tagging',
        }

    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        @app.template_filter('tags')
        def tags(article):
            tag_links = []
            for tag in article_tags(article):
                tag_links.append({'tag': tag, 'url': tag_url(None, tag)})
            return tag_links

        app.add_url_rule('/tags/<tag>/', 
                         view_func = self._view_func('tag_canonical'))
        app.add_url_rule('/tags/<tag>/index', 
                         view_func = self._view_func('tag_index'))
        app.add_url_rule('/<path:category>/tags/<tag>/', 
                         view_func = self._view_func('tag_category_canonical'))
        app.add_url_rule('/<path:category>/tags/<tag>/index', 
                         view_func = self._view_func('tag_category_index'))
        app.add_url_rule('/tags/<tag>/index.<flav>', 
                         view_func = self._view_func('tag_index_flav'))
        app.add_url_rule('/<path:category>/tags/<tag>/index.<flav>', 
                         view_func = self._view_func('tag_category_index_flav'))

    def walker(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())
    
    def _get_index_dir(self):
        return yawt.utils.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']

    def _plugin_config(self):
        return self.app.config[self.name]

    def _view_func(self, endpoint):
        return TagView.as_view(endpoint, plugin_config = self._plugin_config())
        
def create_plugin():
    return TaggingPlugin()
