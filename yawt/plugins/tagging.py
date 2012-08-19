import yawt.util
import os
import yaml

from yawt.view import YawtView, PagingInfo
from flask import g, request, url_for

flask_app = None
name = None

_tag_dir = '_tags'
_tag_file = _tag_dir + '/tags.yaml'
_name_file = _tag_dir + '/names.yaml'

default_config = {
    'tag_dir': _tag_dir,
    'tag_file': _tag_file,
    'name_file': _name_file,
}

def _tag_url(category, tag):
    if category:
        return url_for('tag_category_canonical', category=category, tag=tag)
    else:
        return url_for('tag_canonical', tag=tag)
        
class TagView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store

    def dispatch_request(self, flavour, category, tag, page, page_size, base_url):
        articles =  self._fetch_tagged_articles(category, tag)
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, tag, page_info, category)
        
    def _render_collection(self, flavour, articles, tag, page_info, category):
        title = self._tag_title(tag)
        return self._yawtview.render_collection(flavour, articles, title, page_info, category)
    
    def _tag_title(self, tag):
        return 'Tag results for: "%s"' % tag
 
    def _fetch_tagged_articles(self, category, tag):
        """
        Fetch article collection by tag.
        """
        results = []
        for af in self._store.walk_articles(category):
            article = self._store.fetch_article_by_fullname(af)
            if self._tag_match(article, tag):
                results.append(article)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
    
    def _tag_match(self, article, tag):
        tags = article.get_metadata('tags')
        if tags is None:
            return False
        return tag in tags


def _create_tag_view():
    return TagView(g.store,
                   YawtView(g.plugins,
                            g.config['content_types']))


class TagCounter(object):
    def __init__(self, store):
        self._store = store
        self._tag_infos = None
        self._name_infos = None

    def pre_walk(self):
        self._tag_infos = {}
        self._name_infos = {}
    
    def visit_article(self, fullname):
        base = _get_tagging_base()
        if not fullname.startswith(base):
            return
        
        article = self._store.fetch_article_by_fullname(fullname)
        tags = article.get_metadata('tags')

        # save the tags associated with the article so we can remove
        # them later if they change
        if tags is not None and len(tags) > 0:
            self._name_infos[fullname] = tags
        
        if tags is not None:
            for tag in tags:
                if tag not in self._tag_infos.keys():
                    tag_url = _tag_url(base, tag)
                    self._tag_infos[tag] = {'count': 0, 'url': tag_url}
                self._tag_infos[tag]['count'] += 1
 
    def post_walk(self):
        self._save_info(_get_tag_file(), self._tag_infos)
        self._save_info(_get_name_file(), self._name_infos)
       
    def update(self, statuses):
        self._tag_infos = _load_tag_infos()
        self._name_infos = _load_name_infos()
        
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','M','R']:
                continue

            # no matter what, remove all old tags.
            if fullname in self._name_infos:
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
                # namely add the tags (since we deleted all the old ones)
                self.visit_article(fullname)
        self.post_walk()
          
    def _save_info(self, filename, info):
        tag_dir = _get_tag_dir()
        if not os.path.exists(tag_dir):
            os.mkdir(tag_dir)
        stream = file(filename, 'w')
        yaml.dump(info, stream)
        stream.close()
    
def init(app, plugin_name):
    global flask_app
    flask_app = app
    
    global name
    name = plugin_name
 
    # filter for showing article tags
    @app.template_filter('tags')
    def tags(article):
        tags = article.get_metadata('tags')
        if tags is not None:
            base = _get_tagging_base()
            tag_links = []
            for tag in tags:
                tag_links.append({'tag': tag, 'url': _tag_url(base, tag)})
            return tag_links
        else:
            return None
     
    @app.route('/tags/<tag>/')
    def tag_canonical(tag):
        return _handle_tag_url(None, '', tag)

    @app.route('/<path:category>/tags/<tag>/')
    def tag_category_canonical(category, tag):
        return _handle_tag_url(None, category, tag)

    @app.route('/tags/<tag>/index')
    def tag_index(tag):
        return _handle_tag_url(None, '', tag)

    @app.route('/<path:category>/tags/<tag>/index')
    def tag_category_index(category, tag):
        return _handle_tag_url(None, category, tag)

    @app.route('/tags/<tag>/index.<flav>')
    def tag_index_flav(tag):
        return _handle_tag_url(flav, '', tag)

    @app.route('/<path:category>/tags/<tag>/index.<flav>')
    def tag_category_index_flav(category, tag):
        return _handle_tag_url(flav, category, tag)

    def _handle_tag_url(flavour, category, tag):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        tag_view = _create_tag_view()
        return tag_view.dispatch_request(flavour, category, tag, page,
                                         int(g.config['page_size']), request.base_url)
            
def template_vars():
    return {'tags':_load_tag_infos()}

def walker(store):
    return TagCounter(store)

def updater(store):
    return TagCounter(store)

def _load_tag_infos():
    return yawt.util.load_yaml(_get_tag_file())

def _load_name_infos():
    return yawt.util.load_yaml(_get_name_file())

def _plugin_config():
    return flask_app.config[name]
    
def _get_tag_dir():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['tag_dir'])

def _get_tag_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['tag_file'])

def _get_name_file():
    return yawt.util.get_abs_path_app(flask_app, _plugin_config()['name_file'])

def _get_tagging_base():
    base = _plugin_config()['base'].strip()
    return base.rstrip('/')
