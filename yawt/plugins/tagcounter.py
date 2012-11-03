import yawt.util
import os

from flask import url_for
from yawt.plugins.tagging import article_tags, tag_url

class TagCounter(object):
    def __init__(self, store, base, tag_count_file, article_tag_file):
        self._store = store  
        self._base = base
        self._tag_count_file = tag_count_file
        self._article_tag_file = article_tag_file
        
    def pre_walk(self):
        self._tag_counts = {}
        self._article_tags = {}
       
    def visit_article(self, fullname):
        if not fullname.startswith(self._base):
            return
        
        tags = article_tags(self._store.fetch_article_by_fullname(fullname))
       
        # save the tags associated with the article so we can remove
        # them later if they change
        if len(tags) > 0:
            self._article_tags[fullname] = tags

        for tag in tags:
            if tag not in self._tag_counts.keys():
                self._tag_counts[tag] = {'count': 0, 'url': tag_url(self._base, tag)}
            self._tag_counts[tag]['count'] += 1
      
    def update(self, statuses):
        self._tag_counts = yawt.util.load_yaml(self._tag_count_file)
        self._article_tags = yawt.util.load_yaml(self._article_tag_file)
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','M','R']:
                continue

            # no matter what, remove all old article_tags.
            if fullname in self._article_tags:
                old_tags = self._article_tags[fullname]
                for tag in old_tags:
                    if tag in self._tag_counts.keys():
                        self._tag_counts[tag]['count'] -= 1
                        if self._tag_counts[tag]['count'] == 0:
                            del self._tag_counts[tag]
                del self._article_tags[fullname]
 
            # if this is a R status, then removing the old article_tags was all we needed to do
            if status in ('A', 'M'):
                # file added or modified - treat it the same way.
                # namely add the article_tags (since we deleted all the old ones)
                self.visit_article(fullname)
        self.post_walk()

    def post_walk(self):
        yawt.util.save_yaml(self._tag_count_file, self._tag_counts)
        yawt.util.save_yaml(self._article_tag_file, self._article_tags)
    
class TagCounterPlugin(object):
    def __init__(self):
        self.default_config = { 'TAG_DIR': '_tags',
                                'TAG_COUNT_FILE': '_tags/tag_counts.yaml',
                                'ARTICLE_TAG_FILE': '_tags/article_tags.yaml',
                                'BASE': '' }

    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name
     
    def template_vars(self):
        return {'article_tags': self._load_tag_counts()}

    def walker(self, store):
        return TagCounter(store, self._get_base(),
                          self._get_tag_count_file(),
                          self._get_article_tag_file())
    
    def updater(self, store):
        return TagCounter(store, self)
    
    def _load_tag_counts(self):
        return yawt.util.load_yaml(self._get_tag_count_file())
    
    def _load_article_tags(self):
        return yawt.util.load_yaml(self._get_article_tag_file())
    
    def _get_article_tag_file(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['ARTICLE_TAG_FILE'])
    
    def _plugin_config(self):
        return self.app.config[self.name]

    def _get_tag_count_file(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['TAG_COUNT_FILE'])
    
    def _get_base(self):
        base = self._plugin_config()['BASE'].strip()
        return base.rstrip('/')
    
def create_plugin():
    return TagCounterPlugin()
