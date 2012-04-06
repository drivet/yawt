import yawt.util
import os
import yaml

from yawt.view import YawtView
from flask import g

tag_dir = 'tags'
tag_file = tag_dir + '/tags.yaml'

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
        return 'Tag: %s' % tag    
 
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
        self.tag_counts = {}

    def pre_walk(self):
        pass
    
    def visit_article(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        tags = article.get_metadata('tags')
        if tags is not None:
            for tag in tags:
                if tag in self.tag_counts.keys():
                    self.tag_counts[tag] = self.tag_counts[tag] + 1
                else:
                    self.tag_counts[tag] = 1

    def post_walk(self):
        if not os.path.exists(tag_dir):
            os.mkdir(tag_dir)
        stream = file(tag_file, 'w')
        yaml.dump(self.tag_counts, stream)
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
    return {'tags':_load_tag_counts()}

def walker(store):
    return TagCounter(store)

def _load_tag_counts():
    return yawt.util.load_yaml(tag_file)
