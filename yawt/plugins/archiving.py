import yawt.util
import os
import yaml
import datetime

from whoosh.fields import Schema, STORED, ID, DATETIME, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

from yawt.view import YawtView, PagingInfo
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


class ArchiveIndexer(object):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        self._doc_root = doc_root

    def pre_walk(self):
        self._writer = self._get_writer(clean = True)
        
    def visit_article(self, fullname):
        if self._doc_root and not fullname.startswith(self._doc_root):
            return
        self._update_document(fullname)

    def update(self, statuses):
        self.pre_walk()
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','M','R']:
                continue
            self.visit_article(fullname)
        self.post_walk()
        
    def post_walk(self):
        self._writer.commit()
        
    def _update_document(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        mtime = os.path.getmtime(self._store._name2file(fullname))
        ctime_dt = datetime.datetime.fromtimestamp(article.ctime)
        self._writer.update_document(fullname = unicode(article.fullname),
                                     mtime = mtime,
                                     ctime = ctime_dt)
        
    def _create_schema(self):
        schema = Schema(fullname = ID(stored=True, unique=True),
                        mtime = STORED,
                        ctime = DATETIME)
        return schema
    
    def _get_writer(self, clean):
        if not os.path.exists(self._index_dir):
            os.mkdir(self._index_dir)

        if clean or not exists_in(self._index_dir, self._index_name):
            schema = self._create_schema()
            ix = create_in(self._index_dir, schema = schema,
                           indexname = self._index_name)
        else:
            ix = open_dir(self._index_dir, indexname = self._index_name)
            
        return ix.writer()


class PermalinkView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    def dispatch_request(self, flavour, category, year, month, day, slug):
        articles = self._store.fetch_dated_articles(year, month, day, slug, category=category)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            article = articles[0]
            permalink = url_for_permalink(category, year, month, day, slug)
            
            return self._yawtview.render_article(flavour, article,
                                                 yawt.util.breadcrumbs(permalink))
  
class ArchiveView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    def dispatch_request(self, flavour, category, year, month, day,
                         page, page_size, base_url):
        articles =  self._store.fetch_dated_articles(year, month, day, category=category)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, date, page_info, category)

    def _render_collection(self, flavour, articles, date, page_info, category):
        #title = self._archive_title(date)
        link = _archivelink(date.year, date.month, date.day, category)
        return self._yawtview.render_collection(flavour, articles, '', page_info, category,
                                                yawt.util.breadcrumbs(link))
       
    def _archive_title(self, date):
        return 'Archives: %s' % str(date)


class ArchivingStore(object):
    def __init__(self, store, index_dir, index_name):
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        
    def fetch_dated_articles(self, year, month=None, day=None, slug=None, category=''):
        """
        Fetch collection of articles by date.
        """
        ix = open_dir(self._index_dir, indexname = self._index_name)
        search_results = None
        searcher = None
        results = []
        with ix.searcher() as searcher:
            qp = QueryParser('ctime', schema = ix.schema)
            q = qp.parse(unicode(_datestr(year, month, day)))
            search_results = searcher.search(q, limit=None)    
            if search_results is not None:
                for sr in search_results:
                    article = self._store.fetch_article_by_fullname(sr['fullname'])
                    results.append(article)
        results = filter(lambda a: a.fullname.startswith(category) and \
                             (slug is None or a.slug == slug), results)
        return sorted(results, key = lambda info: info.ctime, reverse=True)

    
def _datestr(year, month=None, day=None):
    datestr = ''
    if year:
        datestr += '%04d' % year
    if month:
        datestr += '%02d' % month
    if day:
        datestr += '%02d' % day
    return datestr

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
        return PermalinkView(ArchivingStore(g.store, self._get_index_dir(), self._get_index_name()),
                             YawtView(g.plugins, yawt.util.get_content_types()))

    def _create_archive_view(self):
        return ArchiveView(ArchivingStore(g.store, self._get_index_dir(), self._get_index_name()),
                           YawtView(g.plugins, yawt.util.get_content_types()))


def create_plugin():
    return ArchivingPlugin()
