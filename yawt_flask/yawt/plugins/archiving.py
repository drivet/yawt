import yawt.util
import os
import yaml

from yawt.view import YawtView, PagingInfo
from flask import g, url_for, request

flask_app = None

_archive_dir = '_archive_counts'
_archive_file = _archive_dir + '/archive_counts.yaml'
_name_file = _archive_dir + '/name_infos.yaml'
    
default_config = {
    'archive_dir': _archive_dir,
    'archive_file': _archive_file,
    'name_file': _name_file,
}
    
class PermalinkView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    def dispatch_request(self, flavour, year, month, day, slug):
        articles = self._store.fetch_dated_articles(year, month, day, slug)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            article = articles[0]
            return self._yawtview.render_article(flavour, article)
         
def _create_permalink_view():
    return PermalinkView(ArchivingStore(g.store),
                         YawtView(g.plugins, g.config['content_types']))

class ArchiveView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    def dispatch_request(self, flavour, year, month, day, page, page_size, base_url):
        articles =  self._store.fetch_dated_articles(year, month, day)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, date, page_info)

    def _render_collection(self, flavour, articles, date, page_info):
        title = self._archive_title(date)
        return self._yawtview.render_collection(flavour, articles, title, page_info)
       
    def _archive_title(self, date):
        return 'Archives - %s' % str(date)

def _create_archive_view():
    return ArchiveView(ArchivingStore(g.store),
                       YawtView(g.plugins, g.config['content_types']))
   
class ArchivingStore(object):
    def __init__(self, store):
        self._store = store

    def fetch_dated_articles(self, year, month=None, day=None, slug=None):
        """
        Finds article collection by create time and slug.  Only year is required.
        If you specify everything, this becomes a permalink, and only
        one entry should be returned (but in a list)
        """
        results = []
        for af in self._store.walk_articles():
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
        self._name_infos = None

    def pre_walk(self):
        self._archive_counts = {}
        self._name_infos = {}
    
    def visit_article(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        ym = (article.ctime_tm.tm_year, article.ctime_tm.tm_mon)

        self._name_infos[fullname] = [ym[0], ym[1]]

        if ym not in self._archive_counts.keys():
            archive_url = '/%s/%s/' % (ym[0], ym[1])
            self._archive_counts[ym] = {'count':0, 'url': archive_url}
        self._archive_counts[ym]['count'] = self._archive_counts[ym]['count'] + 1

    def post_walk(self):
        archive_counts_dump = []
        for date, info in self._archive_counts.items():
            archive_counts_dump.append({'year': date[0], 'month': date[1],
                                        'count': info['count'], 'url': info['url']})
        archive_counts_dump.sort(key = lambda item: (item['year'], item['month']),
                                 reverse = True)
        
        self._save_info(_get_archive_file(), archive_counts_dump)
        self._save_info(_get_name_file(), self._name_infos)

    def update(self, statuses):
        archive_counts_dump = _load_archive_counts()
        self._archive_counts = {}
        for ac in archive_counts_dump:
            ym = (ac['year'],ac['month'])
            self._archive_counts[ym] = {'count':ac['count'], 'url': ac['url']}
        self._name_infos = _load_name_infos()
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            assert status in ['A','M','R']

            old_date = self._name_infos[fullname]
            ym = (old_date[0], old_date[1])
            if ym in self._archive_counts:
                self._archive_counts[ym]['count'] -= 1
                if self._archive_counts[ym]['count'] == 0:
                    del self._archive_counts[ym]
            del self._name_infos[fullname]
            
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
        
def init(app):
    global flask_app
    flask_app = app

    _load_config()
    
    # filter for showing article permalinks
    @app.template_filter('permalink')
    def permalink(article, external=True):
        year = article.ctime_tm.tm_year
        month = article.ctime_tm.tm_mon
        day = article.ctime_tm.tm_mday
        slug = os.path.split(article.fullname)[1]
        return url_for('permalink', _external=external,
                       year=year, month=month, day=day, slug=slug)

    @app.template_filter('archive_url')
    def archive_url(relative_url):
        return request.url_root + relative_url

    # Permalinks
    @app.route('/<int:year>/<int:month>/<int:day>/<slug>')
    def permalink(year, month, day, slug):
        return _create_permalink_view().dispatch_request(None, year, month, day, slug)
       
    @app.route('/<int:year>/<int:month>/<int:day>/<slug>.<flav>')
    def permalink_flav(year, month, day, slug, flav):
        return _create_permalink_view().dispatch_request(flav, year, month, day, slug)
   
    # Date URLs
    @app.route('/<int:year>/')
    @app.route('/<int:year>/<int:month>/')
    @app.route('/<int:year>/<int:month>/<int:day>/')
    def archive(year, month=None, day=None):
        return _handle_archive_url(None, year, month, day)
       
    @app.route('/<int:year>/index')
    @app.route('/<int:year>/<int:month>/index')
    @app.route('/<int:year>/<int:month>/<int:day>/index')
    def archive_index(year, month=None, day=None):
        return _handle_archive_url(None, year, month, day)

    @app.route('/<int:year>/index.<flav>')
    @app.route('/<int:year>/<int:month>/index.<flav>')
    @app.route('/<int:year>/<int:month>/<int:day>/index.<flav>')
    def archive_index_flav(year, month=None, day=None, flav=None):
        return _handle_archive_url(flav, year, month, day)

    def _handle_archive_url(flav, year, month, day):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        av = _create_archive_view()
        return av.dispatch_request(flav, year, month, day,
                                   page, g.config['page_size'], request.base_url)

    
def template_vars():
    return {'archives':_load_archive_counts()}

def walker(store):
    return ArchiveCounter(store, flask_app)

def updater(store):
    return ArchiveCounter(store, flask_app)

def _load_archive_counts():
    return yawt.util.load_yaml(_get_archive_file())

def _load_name_infos():
    return yawt.util.load_yaml(_get_name_file())

def _plugin_config():
    return flask_app.config[__name__]

def _load_config():
    if __name__ not in flask_app.config:
        flask_app.config[__name__] = {}
    flask_app.config[__name__].update(default_config)
    
def _get_archive_dir():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['archive_dir'])

def _get_archive_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['archive_file'])

def _get_name_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['name_file'])
