import yawt.util
import os
import yaml
import datetime

from whoosh.fields import Schema, STORED, ID, DATETIME, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher, ListIndexView, IndexView
from flask import g, url_for, request, current_app
from werkzeug.routing import BaseConverter
from flask.views import View

def url_for_permalink(base, year, month, day, slug):
    if base:
        return url_for('permalink_category', category=base,
                       year=year, month=month, day=day, slug=slug)
    else:
        return url_for('permalink', year=year, month=month, day=day, slug=slug)

def _archivelink(year, month=None, day=None, category=None, slug=None):
    link = ''
    if category:
        link += category + '/'
    if year:
        link += '%04d' % year + '/'
    if month:
        link += '%02d' % month + '/'
    if day:
        link += '%02d' % day + '/'
    if slug:
        link += slug
    return link
  
def _datestr(year, month=None, day=None):
    datestr = ''
    if year:
        datestr += '%04d' % year
    if month:
        datestr += '%02d' % month
    if day:
        datestr += '%02d' % day
    return datestr


class ArchiveIndexer(ArticleIndexer):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        super(ArchiveIndexer, self).__init__(store, index_dir, index_name, doc_root)

    def _get_schema_fields(self):
        return {'fullname': ID(stored=True), 'ctime': DATETIME(stored=True)}
    
    def _get_article_fields(self, article):
        ctime_dt = datetime.datetime.fromtimestamp(article.ctime)
        return {'fullname':unicode(article.fullname), 'ctime': ctime_dt}

        
class PermalinkView(IndexView):
    def __init__(self, plugin_config):
        self._plugin_config = plugin_config
        
    def dispatch_request(self, year, month, day, slug, flavour=None, category=''):
        yawtview = YawtView(g.plugins, yawt.util.get_content_types())
        fetcher = ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name())
        
        articles = fetcher.fetch(category, 'ctime', unicode(_datestr(year, month, day)))
        articles = filter(lambda a: a.slug == slug, articles)
        if len(articles) < 1:
            return yawtview.render_missing_resource()
        else:
            article = articles[0]
            permalink = url_for_permalink(category, year, month, day, slug)
            return yawtview.render_article(flavour, article)

   
class ArchiveView(ListIndexView):
    def _default_field(self, *args, **kwargs):
        return 'ctime'
    
    def _query(self, year, month=None, day=None, *args, **kwargs):
        return unicode(_datestr(year, month, day))

    
class ArchivingPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'archiving',
        }
        
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name
    
        # filter for showing article permalinks
        @app.template_filter('permalink')
        def permalink(article):
            year = article.ctime_tm.tm_year
            month = article.ctime_tm.tm_mon
            day = article.ctime_tm.tm_mday
            slug = os.path.split(article.fullname)[1]
            return url_for_permalink(None, year, month, day, slug)

        @app.template_filter('archive_url')
        def archive_url(relative_url):
            return request.url_root + relative_url

        # Permalinks
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                         view_func = self._pl_view_func('permalink_category'))
       
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                         view_func = self._pl_view_func('permalink'))
       
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                         view_func = self._pl_view_func('permalink_category_flav'))
       
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                         view_func = self._pl_view_func('permalink_flav'))
       
        # Date URLs
        app.add_url_rule('/<path:category>/<int:year>/',
                         view_func = self._view_func('archive_category'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/',
                         view_func = self._view_func('archive_category'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/',
                         view_func = self._view_func('archive_category'))

        app.add_url_rule('/<int:year>/', view_func = self._view_func('archive'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/',
                         view_func = self._view_func('archive'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/',
                         view_func = self._view_func('archive'))
        
 
        app.add_url_rule('/<path:category>/<int:year>/index',
                         view_func = self._view_func('archive_category_index'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index',
                         view_func = self._view_func('archive_category_index'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index',
                         view_func = self._view_func('archive_category_index'))

        app.add_url_rule('/<int:year>/index',
                         view_func = self._view_func('archive_index'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index',
                         view_func = self._view_func('archive_index'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index',
                         view_func = self._view_func('archive_index'))
        
        
        app.add_url_rule('/<path:category>/<int:year>/index.<flav>',
                         view_func = self._view_func('archive_category_index_flav'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index.<flav>',
                         view_func = self._view_func('archive_category_index_flav'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>',
                         view_func = self._view_func('archive_category_index_flav'))
        
        app.add_url_rule('/<int:year>/index.<flav>',
                         view_func = self._view_func('archive_index_flav'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index.<flav>',
                         view_func = self._view_func('archive_index_flav'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>',
                         view_func = self._view_func('archive_index_flav'))
        
    def walker(self, store):
        return ArchiveIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return ArchiveIndexer(store, self._get_index_dir(), self._get_index_name())

    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']
    
    def _plugin_config(self):
        return self.app.config[self.name]
  
    def _view_func(self, endpoint):
        return ArchiveView.as_view(endpoint, plugin_config = self._plugin_config())

    def _pl_view_func(self, endpoint):
        return PermalinkView.as_view(endpoint, plugin_config = self._plugin_config())

   
def create_plugin():
    return ArchivingPlugin()
