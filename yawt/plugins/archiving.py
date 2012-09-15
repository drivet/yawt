import yawt.util
import os
import yaml

from yawt.view import YawtView, PagingInfo
from flask import g, url_for, request
from werkzeug.routing import BaseConverter

flask_app = None
name = None

_archive_dir = '_archive_counts'
_archive_count_file = _archive_dir + '/archive_counts.yaml'
_archive_date_file = _archive_dir + '/archive_dates.yaml' # used for updates
_base = ''

default_config = {
    'archive_dir': _archive_dir,
    'archive_count_file': _archive_count_file,
    'archive_date_file': _archive_date_file,
    'base': _base
}

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
         
def _create_permalink_view():
    return PermalinkView(ArchivingStore(g.store),
                         YawtView(g.plugins, g.config['content_types']))

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

def _create_archive_view():
    return ArchiveView(ArchivingStore(g.store),
                       YawtView(g.plugins, g.config['content_types']))
   
class ArchivingStore(object):
    def __init__(self, store):
        self._store = store

    def fetch_dated_articles(self, year, month=None, day=None, slug=None, category=""):
        """
        Finds article collection by create time and slug.  Only year is required.
        If you specify everything, this becomes a permalink, and only
        one entry should be returned (but in a list)
        """
        results = []
        for af in self._store.walk_articles(category):
            article = self._store.fetch_article_by_fullname(af)
            if self._date_match(article, year, month, day, slug):
                results.append(article)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
    
    def _date_match(self, article, year, month, day, slug):
        current_slug = os.path.split(article.fullname)[1]
        return article.ctime_tm.tm_year == year and \
               (month is None or month == article.ctime_tm.tm_mon) and \
               (day is None or day == article.ctime_tm.tm_mday) and \
               (slug is None or slug == current_slug)
   
class ArchiveCounter(object):
    def __init__(self, store, app):
        self._store = store
        self._app = app
        self._archive_counts = None
        self._article_dates = None

    def pre_walk(self):
        self._archive_counts = {}
        self._article_dates = {}
    
    def visit_article(self, fullname):
        archive_base = _get_archive_base()
        if not fullname.startswith(archive_base):
            return
        
        article = self._store.fetch_article_by_fullname(fullname)
        ym = (article.ctime_tm.tm_year, article.ctime_tm.tm_mon)

        self._article_dates[fullname] = [ym[0], ym[1]]

        if ym not in self._archive_counts.keys():
            archive_url = '/%s/%04d/%02d/' % (archive_base, ym[0], ym[1])
            self._archive_counts[ym] = {'count':0, 'url': archive_url}
        self._archive_counts[ym]['count'] += 1

    def post_walk(self):
        archive_counts_dump = []
        for date, info in self._archive_counts.items():
            archive_counts_dump.append({'year': date[0], 'month': date[1],
                                        'count': info['count'], 'url': info['url']})
        archive_counts_dump.sort(key = lambda item: (item['year'], item['month']),
                                 reverse = True)
        
        self._save_info(_get_archive_count_file(), archive_counts_dump)
        self._save_info(_get_archive_date_file(), self._article_dates)

    def update(self, statuses):
        archive_counts_dump = _load_archive_counts()
        self._archive_counts = {}
        for ac in archive_counts_dump:
            ym = (ac['year'],ac['month'])
            self._archive_counts[ym] = {'count':ac['count'], 'url': ac['url']}
        self._article_dates = _load_article_dates()
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','M','R']:
                continue

            if fullname in self._article_dates:
                old_date = self._article_dates[fullname]
                ym = (old_date[0], old_date[1])
                if ym in self._archive_counts:
                    self._archive_counts[ym]['count'] -= 1
                    if self._archive_counts[ym]['count'] == 0:
                        del self._archive_counts[ym]
                del self._article_dates[fullname]
            
            if status in ('A', 'M'):
                self.visit_article(fullname)
        self.post_walk()
   
    def _save_info(self, filename, info):
        archive_dir = _get_archive_dir()
        if not os.path.exists(archive_dir):
            os.mkdir(archive_dir)
        stream = file(filename, 'w')
        yaml.dump(info, stream)
        stream.close()


def init(app, plugin_name):
    global flask_app
    flask_app = app

    global name
    name = plugin_name
    
    # filter for showing article permalinks
    @app.template_filter('permalink')
    def permalink(article):
        year = article.ctime_tm.tm_year
        month = article.ctime_tm.tm_mon
        day = article.ctime_tm.tm_mday
        slug = os.path.split(article.fullname)[1]
        return url_for_permalink(_get_archive_base(), year, month, day, slug)

    @app.template_filter('archive_url')
    def archive_url(relative_url):
        return request.url_root + relative_url

    # Permalinks
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>')
    def permalink_category(category, year, month, day, slug):
        return _create_permalink_view().dispatch_request(None, category, year, month, day, slug)

    @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>')
    def permalink(year, month, day, slug):
        return _create_permalink_view().dispatch_request(None, "", year, month, day, slug)
   
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>')
    def permalink_category_flav(category, year, month, day, slug, flav):
        return _create_permalink_view().dispatch_request(flav, category, year, month, day, slug)
         
    @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>')
    def permalink_flav(year, month, day, slug, flav):
        return _create_permalink_view().dispatch_request(flav, "", year, month, day, slug)

    # Date URLs
    @app.route('/<path:category>/<int:year>/')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/')
    def archive_category(category, year, month=None, day=None):
        return _handle_archive_url(None, category, year, month, day)

    @app.route('/<int:year>/')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/')
    def archive(year, month=None, day=None):
        return _handle_archive_url(None, "", year, month, day)
        
    @app.route('/<path:category>/<int:year>/index')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index')
    def archive_category_index(category, year, month=None, day=None):
        return _handle_archive_url(None, category, year, month, day)

    @app.route('/<int:year>/index')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/index')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index')
    def archive_index(year, month=None, day=None):
        return _handle_archive_url(None, "", year, month, day)

    @app.route('/<path:category>/<int:year>/index.<flav>')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index.<flav>')
    @app.route('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>')
    def archive_category_index_flav(category, year, month=None, day=None, flav=None):
        return _handle_archive_url(flav, category, year, month, day)

    @app.route('/<int:year>/index.<flav>')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/index.<flav>')
    @app.route('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>')
    def archive_index_flav(year, month=None, day=None, flav=None):
        return _handle_archive_url(flav, "", year, month, day)
    
    def _handle_archive_url(flav, category, year, month, day):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        av = _create_archive_view()
        return av.dispatch_request(flav, category, year, month, day,
                                   page, g.config['page_size'], request.base_url)

    
def template_vars():
    return {'archives':_load_archive_counts()}

def walker(store):
    return ArchiveCounter(store, flask_app)

def updater(store):
    return ArchiveCounter(store, flask_app)

def _load_archive_counts():
    return yawt.util.load_yaml(_get_archive_count_file())

def _load_article_dates():
    return yawt.util.load_yaml(_get_archive_date_file())

def _plugin_config():
    return flask_app.config[name]
    
def _get_archive_dir():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['archive_dir'])

def _get_archive_count_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['archive_count_file'])

def _get_archive_date_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['archive_date_file'])

def _get_archive_base():
    base = _plugin_config()['base'].strip()
    return base.rstrip('/')
