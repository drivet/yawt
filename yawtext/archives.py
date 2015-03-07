from flask import current_app, g, Blueprint
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh
from flask.views import View
from yawt.view import render
from yawtext.hierarchy_counter import HierarchyCount
from datetime import datetime
import jsonpickle
import os
from yawt.utils import save_file, load_file

archivesbp = Blueprint('archives', __name__)

@archivesbp.app_context_processor
def archive_counts_cp():
    archivecountfile = abs_archivecount_file()
    tvars = {}
    if os.path.isfile(archivecountfile):
        archivebase = current_app.config['YAWT_ARCHIVE_BASE']
        if not archivebase.endswith('/'):
            archivebase += '/'

        archivecounts = jsonpickle.decode(load_file(archivecountfile))
        tvars = {'archivecounts': archivecounts, 'archivebase': archivebase}
    return tvars

    
def abs_archivecount_file():
    root = current_app.yawt_root_dir
    archivecountfile = current_app.config['YAWT_ARCHIVE_COUNT_FILE']
    state_folder = current_app.config['YAWT_STATE_FOLDER']
    return os.path.join(root, state_folder, archivecountfile)

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
    if type(value) is unicode:
        value = long(value)
    v = datetime.fromtimestamp(value)
    return v.strftime('%Y/%m/%d')

def _query(category='', year=None, month=None, day=None):
    datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
    query_str = datefield+':' + _datestr(year, month, day)
    if category:
        query_str += ' AND ' + category
    qp = QueryParser('categories', schema=yawtwhoosh().schema())
    return qp.parse(unicode(query_str))
        

class ArchiveView(CollectionView):
    def dispatch_request(self, *args, **kwargs):
        return super(ArchiveView, self).dispatch_request(*args, **kwargs)
        
    def query(self, category='', year=None, month=None, day=None, *args, **kwargs):
        return _query(category, year, month, day)

    def get_template_name(self):
        return current_app.config['YAWT_ARCHIVE_TEMPLATE']


class PermalinkView(View):
    def dispatch_request(self, category, year, month, day, slug, flav):
        datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
        article_infos = yawtwhoosh().search(_query(category, year, month, day),
                                            datefield,
                                            g.page, g.pagelen,
                                            True)
        article = None
        for info in article_infos:
            if info.slug == slug:
                article = g.site.fetch_article(info.fullname)

        return render(self.get_template_name(), category, slug,
                      flav, {'article' : article})

    def get_template_name(self):
        return current_app.config['YAWT_PERMALINK_TEMPLATE']


class YawtArchives(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app) 
        self.archive_counts = None

    def init_app(self, app):
        app.config.setdefault('YAWT_ARCHIVE_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_PERMALINK_TEMPLATE', 'article') 
        app.config.setdefault('YAWT_ARCHIVE_BASE', '')
        app.config.setdefault('YAWT_ARCHIVE_DATEFIELD', 'create_time')
        app.config.setdefault('YAWT_ARCHIVE_COUNT_FILE', 'archivecounts')
        app.register_blueprint(archivesbp)
        
    def on_pre_walk(self):
        self.archive_counts = HierarchyCount()

    def on_visit_article(self, article):
        category = article.info.category
        countbase = self._adjust_base_for_category() #blech

        if category == countbase or category.startswith(countbase):
            datefield = current_app.config['YAWT_ARCHIVE_DATEFIELD']
            date = getattr(article.info, datefield)
            dh = _date_hierarchy(date)
            self.archive_counts.count_hierarchy(dh)

    def on_post_walk(self):
        self.archive_counts.sort_children(reverse=True)
        self.convert_archive_dates_to_ints(self.archive_counts)
        pickled_info = jsonpickle.encode(self.archive_counts)
        save_file(abs_archivecount_file(), pickled_info)

    def convert_archive_dates_to_ints(self, archive_dates):
        if len(archive_dates.children) > 0:
            for c in archive_dates.children:
                self.convert_archive_dates_to_ints(c)
        if archive_dates.category:
            archive_dates.category = int(archive_dates.category)

    # Feels very wrong
    def _adjust_base_for_category(self):
        countbase = current_app.config['YAWT_CATEGORY_BASE']
        if countbase.startswith('/'):
            countbase = countbase[1:]
        return countbase



archivesbp.add_url_rule('/<path:category>/<int:year>/', 
                        view_func=ArchiveView.as_view('archive_category_y'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/', 
                        view_func=ArchiveView.as_view('archive_category_ym'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>', 
                        view_func=ArchiveView.as_view('archive_category_ymd'))

archivesbp.add_url_rule('/<int:year>/', view_func=ArchiveView.as_view('archive_y'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/',
                        view_func=ArchiveView.as_view('archive_ym'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/', 
                        view_func=ArchiveView.as_view('archive_ymd'))

archivesbp.add_url_rule('/<path:category>/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_category_index_y'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index', 
                        view_func=ArchiveView.as_view('archive_category_index_ym'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index', 
                        view_func=ArchiveView.as_view('archive_category_index_ymd'))

archivesbp.add_url_rule('/<int:year>/index',
                        view_func=ArchiveView.as_view('archive_index_y'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index',
                        view_func=ArchiveView.as_view('archive_index_ym'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index',
                        view_func=ArchiveView.as_view('archive_index_ymd'))

archivesbp.add_url_rule('/<path:category>/<int:year>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_category_index_flav_y'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_category_index_flav_ym'))
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_category_index_flav_ymd'))

archivesbp.add_url_rule('/<int:year>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_index_flav_y'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_index_flav_ym'))
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/index.<flav>', 
                        view_func=ArchiveView.as_view('archive_index_flav_ymd'))      
        
# Permalinks
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                        view_func=PermalinkView.as_view('permalink_category'))
       
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>',
                        view_func=PermalinkView.as_view('permalink'))
       
archivesbp.add_url_rule('/<path:category>/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_category_flav'))
       
archivesbp.add_url_rule('/<int:year>/<int(fixed_digits=2):month>/<int(fixed_digits=2):day>/<slug>.<flav>',
                        view_func=PermalinkView.as_view('permalink_flav'))
