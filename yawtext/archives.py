"""The YAWT archives extension.

Provides archive and permalink views and categorized archive routes.
"""
from __future__ import absolute_import

from datetime import datetime
from flask import current_app, g, Blueprint
from flask.views import View

from yawt.utils import cfg
from yawt.view import render
from yawtext import HierarchyCount, Plugin, SummaryProcessor, BranchedVisitor
from yawtext.collections import CollectionView
from yawtext.indexer import search, search_page


archivesbp = Blueprint('archives', __name__)


@archivesbp.app_template_filter('permalink')
def _permalink(info):
    datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
    date = getattr(info, datefield)
    base = _find_base(info.fullname)
    if base:
        base = "/" + base + "/"
    return base + _date_hierarchy(date) + '/' + info.slug


def _find_base(name):
    longest_base = None
    for base in current_app.config['YAWT_ARCHIVE_BASE']:
        if not base or name.startswith(base + "/"):
            if not longest_base or len(base) > len(longest_base):
                longest_base = base
    return longest_base


@archivesbp.app_context_processor
def _archive_counts_cp():
    return SummaryProcessor.context_processor('YAWT_ARCHIVE_COUNT_FILE',
                                              'YAWT_ARCHIVE_BASE',
                                              'archivecounts')


def _datestr(year, month=None, day=None):
    datestr = ''
    if year:
        datestr += '%04d' % year
    if month:
        datestr += '%02d' % month
    if day:
        datestr += '%02d' % day
    return datestr


def _date_hierarchy(value):
    value = datetime.fromtimestamp(value)
    return value.strftime('%Y/%m/%d')


def _query(category='', year=None, month=None, day=None):
    datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
    query_str = datefield+':' + _datestr(year, month, day)
    if category:
        query_str += ' AND ' + category
    return unicode(query_str)


def _fetch_date_for_name(name):
    infos = search(unicode('fullname:'+name))
    create_time = None
    if len(infos) > 0:
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        create_time = getattr(infos[0], datefield)
    return create_time


class ArchiveView(CollectionView):
    def dispatch_request(self, *args, **kwargs):
        return super(ArchiveView, self).dispatch_request(*args, **kwargs)

    def query(self, category='', year=None, month=None, day=None,
              *args, **kwargs):
        return _query(category, year, month, day)

    def get_template_name(self):
        return current_app.config['YAWT_ARCHIVE_TEMPLATE']


class PermalinkView(View):
    def dispatch_request(self, category=None, year=None, month=None, day=None,
                         slug=None, flav=None):
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        ainfos, _ = search_page(_query(category, year, month, day),
                                datefield,
                                g.page, g.pagelen,
                                True)
        article = None
        for info in ainfos:
            if info.slug == slug:
                article = g.site.fetch_article(info.fullname)

        return render(self.get_template_name(), category, slug,
                      flav, {'article': article})

    def get_template_name(self):
        return current_app.config['YAWT_PERMALINK_TEMPLATE']


class ArchiveProcessor(SummaryProcessor):
    """Subclass of SummaryProcessor which counts archives under a root"""
    def __init__(self, root=''):
        super(ArchiveProcessor, self).__init__(root, '',
                                               cfg('YAWT_ARCHIVE_COUNT_FILE'))

    def _init_summary(self):
        self.summary = HierarchyCount()

    def on_visit_article(self, article):
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        date = getattr(article.info, datefield)
        datestring = _date_hierarchy(date)
        self.summary.add(datestring)

    def unvisit(self, name):
        create_time = _fetch_date_for_name(name)
        if create_time:
            datestring = _date_hierarchy(create_time)
            self.summary.remove(datestring)

    def on_post_walk(self):
        self.summary.sort(reverse=True)
        super(ArchiveProcessor, self).on_post_walk()


class YawtArchives(Plugin):
    """The YAWT archive plugin class itself"""
    def __init__(self, app=None):
        super(YawtArchives, self).__init__(app)
        self.visitor = None

    def init_app(self, app):
        """Set up some default config and register the blueprint"""
        app.config.setdefault('YAWT_ARCHIVE_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_PERMALINK_TEMPLATE', 'article')
        app.config.setdefault('YAWT_ARCHIVE_DATEFIELD', 'create_time')
        app.register_blueprint(archivesbp)


class YawtArchiveCounter(BranchedVisitor):
    """The Yawt archive counter plugin"""
    def __init__(self, app=None):
        super(YawtArchiveCounter, self).__init__('YAWT_ARCHIVE_BASE',
                                                 ArchiveProcessor,
                                                 app)

    def init_app(self, app):
        """set some default config"""
        app.config.setdefault('YAWT_ARCHIVE_BASE', [''])
        app.config.setdefault('YAWT_ARCHIVE_COUNT_FILE', 'archivecounts')


archivesbp.add_url_rule('/<path:category>/<int:year>/',
                        view_func=ArchiveView.as_view('archive_category_y'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/',
                        view_func=ArchiveView.as_view('archive_category_ym'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>',
                        view_func=ArchiveView.as_view('archive_category_ymd'))

archivesbp.add_url_rule('/<int:year>/',
                        view_func=ArchiveView.as_view('archive_y'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/',
                        view_func=ArchiveView.as_view('archive_ym'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/',
                        view_func=ArchiveView.as_view('archive_ymd'))

archivesbp.add_url_rule('/<path:category>/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_category_index_y'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/index',
                        view_func=ArchiveView.as_view('archive_category_index_ym'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index',
                        view_func=ArchiveView.as_view('archive_category_index_ymd'))

archivesbp.add_url_rule('/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_index_y'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index',
                        view_func=ArchiveView.as_view('archive_index_ym'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index',
                        view_func=ArchiveView.as_view('archive_index_ymd'))

archivesbp.add_url_rule('/<path:category>/<int:year>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_y'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_ym'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_ymd'))

archivesbp.add_url_rule('/<int:year>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_y'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_ym'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_ymd'))


# Permalinks
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug>',
                        view_func=PermalinkView.as_view('permalink_category'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug>',
                        view_func=PermalinkView.as_view('_permalink'))

archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_category_flav'))

archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_flav'))
