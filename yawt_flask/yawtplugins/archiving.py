import yawt.util
import os
import yaml

from yawt.view import YawtView
from flask import g, url_for

archive_dir = 'archive_counts'
archive_file = archive_dir + '/archive_counts.yaml'

class PermalinkView(YawtView):
    def __init__(self, store):
        super(PermalinkView, self).__init__()
        self._store = store
        
    def dispatch_request(self, flavour, year, month, day, slug):
        articles = self._store.fetch_dated_articles(year, month, day, slug)
        if len(articles) < 1:
            return handle_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            article = articles[0]
            if flavour is None:
                flavour = 'html'
            return self.render_article(flavour, article)
        
class ArchiveView(YawtView):
    def __init__(self, store):
        super(ArchiveView, self).__init__()
        self._store = store
        
    def dispatch_request(self, flavour, year, month, day):
        articles =  self._store.fetch_dated_articles(year, month, day)
        if len(articles) < 1:
            return handle_missing_resource()
        else:
            date = yawt.util.Date(year, month, day)
            if flavour is None:
                flavour = 'html'
            return self.render_collection(flavour, articles, self._archive_title(date))
        
    def _archive_title(self, date):
        return 'Archives for %s' % str(date)
    
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
    def __init__(self, store):
        self._store = store
        self._archive_counts = {}

    def pre_walk(self):
        pass
    
    def visit_article(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        ym = (article.ctime_tm.tm_year, article.ctime_tm.tm_mon)
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
        
        if not os.path.exists(archive_dir):
            os.mkdir(archive_dir)
        stream = file(archive_file, 'w')
        yaml.dump(archive_counts_dump, stream)
        stream.close()
 
def init(app):
    # filter for showing article permalinks
    @app.template_filter('permalink')
    def permalink(article, external=True):
        year = article.ctime_tm.tm_year
        month = article.ctime_tm.tm_mon
        day = article.ctime_tm.tm_mday
        slug = os.path.split(article.fullname)[1]
        return url_for('permalink', _external=external,
                       year=year, month=month, day=day, slug=slug)

    # Permalinks
    @app.route('/<int:year>/<int:month>/<int:day>/<slug>')
    def permalink(year, month, day, slug):
        return PermalinkView(ArchivingStore(g.store)).dispatch_request(None, year, month, day, slug)
       
    @app.route('/<int:year>/<int:month>/<int:day>/<slug>.<flav>')
    def permalink_flav(year, month, day, slug, flav):
        return PermalinkView(ArchivingStore(g.store)).dispatch_request(flav, year, month, day, slug)
   
    # Date URLs
    @app.route('/<int:year>/')
    @app.route('/<int:year>/<int:month>/')
    @app.route('/<int:year>/<int:month>/<int:day>/')
    def archive(year, month=None, day=None):
        return ArchiveView(ArchivingStore(g.store)).dispatch_request(None, year, month, day)
       
    @app.route('/<int:year>/index')
    @app.route('/<int:year>/<int:month>/index')
    @app.route('/<int:year>/<int:month>/<int:day>/index')
    def archive_index(year, month=None, day=None):
        return ArchiveView(ArchivingStore(g.store)).dispatch_request(None, year, month, day)

    @app.route('/<int:year>/index.<flav>')
    @app.route('/<int:year>/<int:month>/index.<flav>')
    @app.route('/<int:year>/<int:month>/<int:day>/index.<flav>')
    def archive_index_flav(year, month=None, day=None, flav=None):
        return ArchiveView(ArchivingStore(g.store)).dispatch_request(flav, year, month, day)
    
def template_vars():
    return {'archives':_load_archive_counts()}

def walker(store):
    return ArchiveCounter(store)

def _load_archive_counts():
    return yawt.util.load_yaml(archive_file)
