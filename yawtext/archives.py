"""The YAWT archives extension.

Provides archive and permalink views and categorized archive routes.
"""
from __future__ import absolute_import
import os
from datetime import datetime

from flask import current_app, g, Blueprint
from whoosh.qparser import QueryParser
from flask.views import View
import jsonpickle

from yawt.utils import save_file, load_file, fullname
from yawtext.collections import CollectionView, _yawtwhoosh
from yawt.view import render
from yawtext.hierarchy_counter import HierarchyCount


archivesbp = Blueprint('archives', __name__)


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


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
    archivecountmap = {}
    for base in current_app.config['YAWT_ARCHIVE_BASE']:
        archivecountfile = _abs_archivecount_file(base)
        if os.path.isfile(archivecountfile):
            archivecounts = jsonpickle.decode(load_file(archivecountfile))
            archivecountmap[base] = archivecounts
    tvars = {}
    if len(archivecountmap) > 0:
        tvars['archivecounts'] = archivecountmap
    return tvars


def _abs_archivecount_file(base):
    root = current_app.yawt_root_dir
    archivecountfile = current_app.config['YAWT_ARCHIVE_COUNT_FILE']
    state_folder = current_app.config['YAWT_STATE_FOLDER']
    return os.path.join(root, state_folder, base, archivecountfile)


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
    v = datetime.fromtimestamp(value)
    return v.strftime('%Y/%m/%d')


def _query(category='', year=None, month=None, day=None):
    datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
    query_str = datefield+':' + _datestr(year, month, day)
    if category:
        query_str += ' AND ' + category
    qparser = QueryParser('categories', schema=_yawtwhoosh().schema())
    return qparser.parse(unicode(query_str))


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
        ainfos, total = _yawtwhoosh().search(_query(category, year, month, day),
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


class YawtArchives(object):
    """The YAWT archive plugin class itself"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.archive_counts_map = {}

    def init_app(self, app):
        """Set up some default config and register the blueprint"""
        app.config.setdefault('YAWT_ARCHIVE_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_PERMALINK_TEMPLATE', 'article')
        app.config.setdefault('YAWT_ARCHIVE_BASE', [''])
        app.config.setdefault('YAWT_ARCHIVE_DATEFIELD', 'create_time')
        app.config.setdefault('YAWT_ARCHIVE_COUNT_FILE', 'archivecounts')
        app.register_blueprint(archivesbp)

    def on_pre_walk(self):
        """Initialize the archive counts"""
        self.archive_counts_map = {}
        for base in current_app.config['YAWT_ARCHIVE_BASE']:
            self.archive_counts_map[base] = HierarchyCount()

    def on_visit_article(self, article):
        """Count and register for this article"""
        for base in self._get_bases(article):
            datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
            date = getattr(article.info, datefield)
            datestring = _date_hierarchy(date)
            self.archive_counts_map[base].count_hierarchy(datestring)

    def _get_bases(self, article):
        bases = []
        for base in current_app.config['YAWT_ARCHIVE_BASE']:
            if article.info.fullname.startswith(base):
                bases.append(base)
        return bases

    def on_post_walk(self):
        """Save the archive counts to disk"""
        for base in self.archive_counts_map:
            archive_counts = self.archive_counts_map[base]
            archive_counts.sort_children(reverse=True)
            pickled_info = jsonpickle.encode(archive_counts)
            save_file(_abs_archivecount_file(base), pickled_info)

    def on_files_changed(self, files_modified, files_added, files_removed):
        """pass in three lists of files, modified, added, removed, all
        relative to the *repo* root, not the content root (so these are not
        absolute filenames)
        """
        for base in current_app.config['YAWT_ARCHIVE_BASE']:
            pickled_info = load_file(_abs_archivecount_file(base))
            self.archive_counts_map[base] = jsonpickle.decode(pickled_info)
            for f in files_removed + files_modified:
                name = fullname(f)
                if name:
                    create_time = _fetch_date_for_name(name)
                    if create_time:
                        datestring = _date_hierarchy(create_time)
                        self.archive_counts_map[base].remove_hierarchy(datestring)

        for f in files_modified + files_added:
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.on_post_walk()


def _fetch_date_for_name(name):
    searcher = _whoosh().searcher
    qparser = QueryParser('fullname', schema=_yawtwhoosh().schema())
    query = qparser.parse(unicode(name))
    results = searcher.search(query)
    create_time = None
    if len(results) > 0:
        info = jsonpickle.decode(results[0]['article_info_json'])
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        create_time = getattr(info, datefield)

    return create_time


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
