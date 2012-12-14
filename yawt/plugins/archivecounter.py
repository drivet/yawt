import yawt.util

class ArchiveCounter(object):
    def __init__(self, store, base, archive_count_file, article_date_file):
        self._store = store  
        self._base = base
        self._archive_count_file = archive_count_file
        self._article_date_file = article_date_file
        
    def pre_walk(self):
        self._archive_counts = {}
        self._article_dates = {}
    
    def visit_article(self, fullname):
        if not fullname.startswith(self._base):
            return
        
        article = self._store.fetch_article_by_fullname(fullname)
        ym = (article.ctime_tm.tm_year, article.ctime_tm.tm_mon)

        self._article_dates[fullname] = [ym[0], ym[1]]

        if ym not in self._archive_counts.keys():
            archive_url = '/%s/%04d/%02d/' % (self._base, ym[0], ym[1])
            self._archive_counts[ym] = {'count':0, 'url': archive_url}
        self._archive_counts[ym]['count'] += 1
        
    def update(self, statuses):
        self._article_dates = yawt.util.load_yaml(self._article_date_file)
        archive_counts_dump = yawt.util.load_yaml(self._archive_count_file)
        self._archive_counts = {}
        for ac in archive_counts_dump:
            ym = (ac['year'],ac['month'])
            self._archive_counts[ym] = {'count': ac['count'],
                                        'url': ac['url']}
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
        
    def post_walk(self):
        archive_counts_dump = []
        for date, info in self._archive_counts.items():
            archive_counts_dump.append({'year': date[0], 'month': date[1],
                                        'count': info['count'], 'url': info['url']})
        archive_counts_dump.sort(key = lambda item: (item['year'], item['month']),
                                 reverse = True)

        yawt.util.save_yaml(self._archive_count_file, archive_counts_dump)
        yawt.util.save_yaml(self._article_date_file, self._article_dates)
        
class ArchiveCounterPlugin(object):
    def __init__(self):
        self.default_config = { 'ARCHIVE_DIR': '_archivecounter',
                                'ARCHIVE_COUNT_FILE': '_archivecounter/archive_counts.yaml',
                                'ARCHIVE_DATE_FILE': '_archivecounter/archive_dates.yaml',
                                'BASE': '' }

    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name
     
    def template_vars(self):
        return {'archives': self._load_archive_counts()}

    def walker(self, store):
        return ArchiveCounter(store, self._get_base(),
                              self._get_archive_count_file(),
                              self._get_archive_date_file())
    
    def updater(self, store):
        return ArchiveCounter(store, self._get_base(),
                              self._get_archive_count_file(),
                              self._get_archive_date_file())

    def _load_archive_counts(self):
        return yawt.util.load_yaml(self._get_archive_count_file())

    def _plugin_config(self):
        return self.app.config[self.name]
    
    def _get_archive_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['ARCHIVE_DIR'])

    def _get_archive_count_file(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['ARCHIVE_COUNT_FILE'])

    def _get_archive_date_file(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['ARCHIVE_DATE_FILE'])
        
    def _get_base(self):
        base = self._plugin_config()['BASE'].strip()
        return base.rstrip('/')
 
def create_plugin():
    return ArchiveCounterPlugin()
