from flask import current_app, g
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh
from flask.views import View
from yawt.view import render


def _datestr(year, month=None, day=None):
    datestr = ''
    if year:
        datestr += '%04d' % year
    if month:
        datestr += '%02d' % month
    if day:
        datestr += '%02d' % day
    return datestr

def _query(schema, category, year, month, day):
    datestr = _datestr(year, month, day)
    query_str = 'create_time:' + datestr
    if category:
        query_str += ' AND ' + category
    qp = QueryParser('categories', schema=schema)
    return qp.parse(unicode(query_str))


class ArchiveView(CollectionView):
    def query(self, category, year, month, day):
        return _query(yawtwhoosh().schema(), category, year, month, day)
        
    def get_template_name(self):
        return current_app.config['YAWT_ARCHIVE_TEMPLATE']


class PermalinkView(View):
    def dispatch_request(self, category, year, month, day, slug, flav):
        article_infos = yawtwhoosh().search(self.query(category, year, month, day),
                                            'create_time',
                                            g.page, g.pagelen,
                                            True)
        article = None
        for info in article_infos:
            if info.slug == slug:
                article = g.site.fetch_article(info.fullname)

        return render(self.get_template_name(), category, 
                      flav, {'article' : article})

    def query(self, category, year, month, day):
        return _query(yawtwhoosh().schema(), category, year, month, day)

    def get_template_name(self):
        return current_app.config['YAWT_PERMALINK_TEMPLATE']


class YawtArchives(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_ARCHIVE_TEMPLATE', 'article_collection')
        app.config.setdefault('YAWT_PERMALINK_TEMPLATE', 'article')

        app.add_url_rule('/<path:category>/<int:year>/', 
                         view_func=ArchiveView.as_view('archive_category'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/', 
                         view_func=ArchiveView.as_view('archive_category'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>', 
                         view_func=ArchiveView.as_view('archive_category'))

        app.add_url_rule('/<int:year>/', view_func=ArchiveView.as_view('archive'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/',
                         view_func=ArchiveView.as_view('archive'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/', 
                         view_func=ArchiveView.as_view('archive'))

        app.add_url_rule('/<path:category>/<int:year>/index',
                         view_func=ArchiveView.as_view('archive_category_index'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index', 
                         view_func=ArchiveView.as_view('archive_category_index'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index', 
                         view_func=ArchiveView.as_view('archive_category_index'))

        app.add_url_rule('/<int:year>/index',
                         view_func=ArchiveView.as_view('archive_index'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index',
                         view_func=ArchiveView.as_view('archive_index'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index',
                         view_func=ArchiveView.as_view('archive_index'))

        app.add_url_rule('/<path:category>/<int:year>/index.<flav>', 
                         view_func=ArchiveView.as_view('archive_category_index_flav'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index.<flav>', 
                         view_func=ArchiveView.as_view('archive_category_index_flav'))
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav', 
                         view_func=ArchiveView.as_view('archive_category_index_flav'))

        app.add_url_rule('/<int:year>/index.<flav>', 
                         view_func=ArchiveView.as_view('archive_index_flav'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index.<flav>', 
                         view_func=ArchiveView.as_view('archive_index_flav'))
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav', 
                         view_func=ArchiveView.as_view('archive_index_flav'))      
        
        # Permalinks
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                         view_func=PermalinkView.as_view('permalink_category'))
       
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                         view_func=PermalinkView.as_view('permalink'))
       
        app.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                         view_func=PermalinkView.as_view('permalink_category_flav'))
       
        app.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                         view_func=PermalinkView.as_view('permalink_flav'))
