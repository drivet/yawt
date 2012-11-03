import yawt.util
import os
import yaml
import datetime

from whoosh.fields import Schema, STORED, ID, DATETIME, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

from yawt.view import YawtView, PagingInfo
from yawt.plugins.indexer import ArticleIndexer, ArticleFetcher
from flask import g, url_for, request
from werkzeug.routing import BaseConverter

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
        return {'ctime': DATETIME(stored=True)}
    
    def _get_article_fields(self, article):
        ctime_dt = datetime.datetime.fromtimestamp(article.ctime)
        return {'ctime': ctime_dt}

        
class PermalinkView(object):
    def __init__(self, fetcher, yawtview):
        self._yawtview = yawtview
        self._fetcher = fetcher
        
    def dispatch_request(self, flavour, category, year, month, day, slug):
        articles = self._fetcher.fetch(category, 'ctime', unicode(_datestr(year, month, day)))
        articles = filter(lambda a: a.slug == slug, articles)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            article = articles[0]
            permalink = url_for_permalink(category, year, month, day, slug)
            
            return self._yawtview.render_article(flavour, article,
                                                 yawt.util.breadcrumbs(permalink))
  
class ArchiveView(object):
    def __init__(self, fetcher, yawtview):
        self._yawtview = yawtview
        self._fetcher = fetcher
        
    def dispatch_request(self, flavour, category, year, month, day,
                         page, page_size, base_url):
        articles = self._fetcher.fetch(category, 'ctime', unicode(_datestr(year, month, day)))
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, yawt.util.Date(year, month, day),
                                           page_info, category)

    def _render_collection(self, flavour, articles, date, page_info, category):
        link = _archivelink(date.year, date.month, date.day, category)
        return self._yawtview.render_collection(flavour, articles, '', page_info, category,
                                                yawt.util.breadcrumbs(link))
       
    def _archive_title(self, date):
        return 'Archives: %s' % str(date)


class ArchivingPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'archiving',
            'BASE': ''
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
            return url_for_permalink(self._get_archive_base(), year, month, day, slug)

        @app.template_filter('archive_url')
        def archive_url(relative_url):
            return request.url_root + relative_url

        # Permalinks
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>')
        def permalink_category(category, year, month, day, slug):
            return self._create_permalink_view().dispatch_request(None, category, year, month, day, slug)

        @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>')
        def permalink(year, month, day, slug):
            return self._create_permalink_view().dispatch_request(None, "", year, month, day, slug)
   
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>')
        def permalink_category_flav(category, year, month, day, slug, flav):
            return self._create_permalink_view().dispatch_request(flav, category, year, month, day, slug)
         
        @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>')
        def permalink_flav(year, month, day, slug, flav):
            return self._create_permalink_view().dispatch_request(flav, "", year, month, day, slug)

        # Date URLs
        @app.route('/<path:category>/<int:year>/')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/')
        def archive_category(category, year, month=None, day=None):
            return self._handle_archive_url(None, category, year, month, day)

        @app.route('/<int:year>/')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/')
        def archive(year, month=None, day=None):
            return self._handle_archive_url(None, '', year, month, day)
        
        @app.route('/<path:category>/<int:year>/index')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index')
        def archive_category_index(category, year, month=None, day=None):
            return self._handle_archive_url(None, category, year, month, day)

        @app.route('/<int:year>/index')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/index')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index')
        def archive_index(year, month=None, day=None):
            return self._handle_archive_url(None, '', year, month, day)

        @app.route('/<path:category>/<int:year>/index.<flav>')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index.<flav>')
        @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>')
        def archive_category_index_flav(category, year, month=None, day=None, flav=None):
            return self._handle_archive_url(flav, category, year, month, day)

        @app.route('/<int:year>/index.<flav>')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/index.<flav>')
        @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>')
        def archive_index_flav(year, month=None, day=None, flav=None):
            return self._handle_archive_url(flav, '', year, month, day)

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
         
    def _get_archive_base(self):
        base = self._plugin_config()['BASE'].strip()
        return base.rstrip('/')

    def _handle_archive_url(self, flav, category, year, month, day):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1
            
        av = self._create_archive_view()
        return av.dispatch_request(flav, category, year, month, day,
                                   page, g.config['YAWT_PAGE_SIZE'], request.base_url)

    def _create_permalink_view(self):
        return PermalinkView(ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name()),
                             YawtView(g.plugins, yawt.util.get_content_types()))

    def _create_archive_view(self):
        return ArchiveView(ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name()),
                           YawtView(g.plugins, yawt.util.get_content_types()))


def create_plugin():
    return ArchivingPlugin()
