import yawt.util
import os
import yaml

from yawt.view import YawtView
from flask import g, url_for

tag_dir = 'tags'
tag_file = tag_dir + '/tags.yaml'
name_file = tag_dir + '/names.yaml'

class TagView(YawtView):
    def __init__(self, store):
        super(TagView, self).__init__()
        self._store = store

    def dispatch_request(self, tag, flavour=None):
        articles =  self._fetch_tagged_articles(tag)
        if len(articles) < 1:
            return self.handle_missing_resource()
        else:
            if flavour is None:
                flavour = 'html'
            return self.render_collection(flavour, articles, self._tag_title(tag))
        
    def _tag_title(self, tag):
        return 'Tags - %s' % tag    
 
    def _fetch_tagged_articles(self, tag):
        """
        Fetch article collection by tag.
        """
        results = []
        for af in self._store.walk_articles():
            article = self._store.fetch_article_by_fullname(af)
            if self._tag_match(article, tag):
                results.append(article)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
    
    def _tag_match(self, article, tag):
        tags = article.get_metadata('tags')
        if tags is None:
            return False
        return tag in tags
    
class TagCounter(object):
    def __init__(self, store):
        self._store = store
        self._tag_infos = None
        self._name_infos = None

    def pre_walk(self):
        self._tag_infos = {}
        self._name_infos = {}
    
    def visit_article(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        tags = article.get_metadata('tags')

        # save the tags associated with the article so we can remove
        # them later if they change
        if tags is not None and len(tags) > 0:
            self._name_infos[fullname] = tags
        
        if tags is not None:
            for tag in tags:
                if tag not in self._tag_infos.keys():
                    tag_url = '/tags/%s/' % tag
                    self._tag_infos[tag] = {'count': 0, 'url': tag_url}
                self._tag_infos[tag]['count'] += 1
               
    def post_walk(self):
        self._save_info(tag_file, self._tag_infos)
        self._save_info(name_file, self._name_infos)
       
   
    def update(self, statuses):
        self._tag_infos = _load_tag_infos()
        self._name_infos = _load_name_infos()
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            assert status in ['A','M','R']

            # no matter what, remove all old tags.
            old_tags = self._name_infos[fullname]
            for tag in old_tags:
                if tag in self._tag_infos.keys():
                    self._tag_infos[tag]['count'] -= 1
                    if self._tag_infos[tag]['count'] == 0:
                        del self._tag_infos[tag]
            del self._name_infos[fullname]
 
            # if this is a R status, then removing the old tags was all we needed to do
            if status in ('A', 'M'):
                # file added or modified - treat it the same way.
                # namely add the tags (since we deleted all the old ones
                self.visit_article(fullname)
        self.post_walk()
          
    def _save_info(self, filename, info):
        if not os.path.exists(tag_dir):
            os.mkdir(tag_dir)
        stream = file(filename, 'w')
        yaml.dump(info, stream)
        stream.close()
    
def init(app):
    # filter for showing article tags
    @app.template_filter('tags')
    def tags(article):
        tags = article.get_metadata('tags')
        if tags is not None:
            return ', '.join(tags)
        else:
            return ''
        
    @app.route('/tags/<tag>/')
    def tag_canonical(tag):
        return TagView(g.store).dispatch_request(tag)

    @app.route('/tags/<tag>/index')
    def tag_index(tag):
        return TagView(g.store).dispatch_request(tag)

    @app.route('/tags/<tag>/index.<flav>')
    def tag_index_flav(tag):
        return TagView(g.store).dispatch_request(tag, flav)
    
def template_vars():
    return {'tags':_load_tag_infos()}

def walker(store):
    return TagCounter(store)

def updater(store):
    return TagCounter(store)

def _load_tag_infos():
    return yawt.util.load_yaml(tag_file)

def _load_name_infos():
    return yawt.util.load_yaml(name_file)
