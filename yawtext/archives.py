"""The YAWT archives extension.

Provides archive and permalink views and categorized archive routes.
"""
from __future__ import absolute_import

import os

from datetime import datetime
from flask import current_app, g, Blueprint
from flask.views import View

from yawt.utils import cfg
from yawt.view import render
from yawtext import HierarchyCount, Plugin, SummaryProcessor, BranchedVisitor
from yawtext.collections import CollectionView
from yawtext.indexer import search, search_page
from werkzeug.routing import BaseConverter, ValidationError


archivesbp = Blueprint('archives', __name__)


@archivesbp.app_template_filter('permalink')
def _permalink(info):
    datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
    date = getattr(info, datefield)
    base = _find_base(info.fullname)
    if base:
        base = "/" + base + "/"
    else:
        base = '/'
    return base + _date_hierarchy(date) + '/' + info.slug


@archivesbp.app_template_filter('canonical')
def _canonical(info):
    return os.path.join(cfg('YAWT_BASE_URL'), info.fullname)


def _find_base(name):
    longest_base = None
    for base in current_app.config['YAWT_ARCHIVE_BASE']:
        if (not base or name.startswith(base + "/")) and \
           (not longest_base or len(base) > len(longest_base)):
            longest_base = base
    return longest_base


def _datestr(year, month=None, day=None):
    datestr = ''
    if year:
        datestr += '{0:04d}'.format(year)
    if month:
        datestr += '{0:02d}'.format(month)
    if day:
        datestr += '{0:02d}'.format(day)
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
    if infos:
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        create_time = getattr(infos[0], datefield)
    return create_time


class SlugConverter(BaseConverter):
    """Custom convertor to match slugs, i.e. base filenames that are
    not 'index'"""
    def to_python(self, value):
        if value != 'index':
            return value
        else:
            raise ValidationError()


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
                      flav, {'article': article, 'is_permalink': True})

    def get_template_name(self):
        return current_app.config['YAWT_PERMALINK_TEMPLATE']


# /reading/2015/
archivesbp.add_url_rule('/<path:category>/<int:year>/',
                        view_func=ArchiveView.as_view('archive_category_y'))

# /reading/2015/11/
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/',
                        view_func=ArchiveView.as_view('archive_category_ym'))

# /reading/2015/11/18
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/',
                        view_func=ArchiveView.as_view('archive_category_ymd'))

# /2015/
archivesbp.add_url_rule('/<int:year>/',
                        view_func=ArchiveView.as_view('archive_y'))

# /2015/11/
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/',
                        view_func=ArchiveView.as_view('archive_ym'))

# /2015/11/18/
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/',
                        view_func=ArchiveView.as_view('archive_ymd'))

# /reading/2015/index
archivesbp.add_url_rule('/<path:category>/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_category_index_y'))

# /reading/2015/11/index
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/index',
                        view_func=ArchiveView.as_view('archive_category_index_ym'))

# /reading/2015/11/18/index
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index',
                        view_func=ArchiveView.as_view('archive_category_index_ymd'))

# /2015/index
archivesbp.add_url_rule('/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_index_y'))

# /2015/11/index
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index',
                        view_func=ArchiveView.as_view('archive_index_ym'))

# /2015/11/18/index
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index',
                        view_func=ArchiveView.as_view('archive_index_ymd'))

# /reading/2015/index.html
archivesbp.add_url_rule('/<path:category>/<int:year>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_y'))

# /reading/2015/11/index.html
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_ym'))

# /reading/2015/11/18/index.html
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_category_index_flav_ymd'))

# /2015/index.html
archivesbp.add_url_rule('/<int:year>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_y'))

# /2015/11/index.html
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_ym'))

# /2015/11/18/index.html
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/index.<flav>',
                        view_func=ArchiveView.as_view('archive_index_flav_ymd'))


# Permalinks

# /reading/2015/11/18/entry
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug:slug>',
                        view_func=PermalinkView.as_view('permalink_category'))

# /2015/11/18/entry
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug:slug>',
                        view_func=PermalinkView.as_view('_permalink'))

# /reading/2015/11/18/entry.html
archivesbp.add_url_rule('/<path:category>/<int:year>/' +
                        '<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug:slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_category_flav'))

# /2015/11/18/entry.html
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/' +
                        '<int(fixed_digits=2):day>/<slug:slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_flav'))


class YawtArchives(Plugin):
    """The YAWT archive plugin class itself"""
    def __init__(self, app=None):
        super(YawtArchives, self).__init__(app)

    def init_app(self, app):
        """Set up some default config and register the blueprint"""
        app.config.setdefault('YAWT_ARCHIVE_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_PERMALINK_TEMPLATE', 'article')
        app.config.setdefault('YAWT_ARCHIVE_DATEFIELD', 'create_time')
        app.config.setdefault('YAWT_ARCHIVE_BASE', [''])
        app.url_map.converters['slug'] = SlugConverter
        app.register_blueprint(archivesbp)


archivecountsbp = Blueprint('archivecounts', __name__)

@archivecountsbp.app_context_processor
def _archive_counts_cp():
    return SummaryProcessor.context_processor('YAWT_ARCHIVE_COUNT_FILE',
                                              'YAWT_ARCHIVE_BASE',
                                              'archivecounts')

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
        app.config.setdefault('YAWT_ARCHIVE_DATEFIELD', 'create_time')
        app.register_blueprint(archivecountsbp)
