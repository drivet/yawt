import yawt.util
import yaml
import os

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher
from flask import g, request, url_for, current_app
from flask.views import View

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

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
        return {'tags': KEYWORD(commas=True)}
    
    def _get_article_fields(self, article):
        tags = article.get_metadata('tags', '')
        return {'tags': unicode(tags)}

     
class TagView(View):
    def __init__(self, plugin_config):
        self._plugin_config = plugin_config
        
    def dispatch_request(self, tag, flavour=None, category=''):
        yawtview = YawtView(g.plugins, yawt.util.get_content_types())
        fetcher = ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name())
        
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        page_size = int(g.config['YAWT_PAGE_SIZE'])
        
        articles =  fetcher.fetch(category, 'tags', unicode(tag))
        if len(articles) < 1:
            return yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), request.base_url)
            return self._render_collection(yawtview, flavour, articles, tag, page_info, category)
         
    def _render_collection(self, yawtview, flavour, articles, tag, page_info, category):
        title = self._tag_title(tag)
        return yawtview.render_collection(flavour, articles, title, page_info, category)
    
    def _tag_title(self, tag):
        return 'Tag results for: "%s"' % tag
    
    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(current_app, self._plugin_config['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config['INDEX_NAME']


class TaggingPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'tagging',
            'BASE': ''
        }

    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        @app.template_filter('tags')
        def tags(article):
            tag_links = []
            for tag in article_tags(article):
                tag_links.append({'tag': tag, 'url': tag_url(self._get_base(), tag)})
            return tag_links

        app.add_url_rule('/tags/<tag>/', view_func = self._view_func('tag_canonical'))
        app.add_url_rule('/tags/<tag>/index', view_func = self._view_func('tag_index'))
        app.add_url_rule('/<path:category>/tags/<tag>/', view_func = self._view_func('tag_category_canonical'))
        app.add_url_rule('/<path:category>/tags/<tag>/index', view_func = self._view_func('tag_category_index'))
        app.add_url_rule('/tags/<tag>/index.<flav>', view_func = self._view_func('tag_index_flav'))
        app.add_url_rule('/<path:category>/tags/<tag>/index.<flav>', view_func = self._view_func('tag_category_index_flav'))

    def walker(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())
    
    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']

    def _get_base(self):
        return self._plugin_config()['BASE'].strip().rstrip()
    
    def _plugin_config(self):
        return self.app.config[self.name]

    def _view_func(self, endpoint):
        return TagView.as_view(endpoint, plugin_config = self._plugin_config())
        
def create_plugin():
    return TaggingPlugin()
