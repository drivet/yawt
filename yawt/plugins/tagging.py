import yawt.util
import yaml
import os

from yawt.view import YawtView, PagingInfo
from flask import g, request, url_for

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

def tag_url(category, tag):
    if category:
        return url_for('tag_category_canonical', category=category, tag=tag)
    else:
        return url_for('tag_canonical', tag=tag)
    
def article_tags(article):
    tags = []
    tagdata = article.get_metadata('tags', '')
    if tagdata is not '':
        tags = tagdata.split(',')
    return tags
            
class TagIndexer(object):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        self._doc_root = doc_root

    def pre_walk(self):
        self._writer = self._get_writer(clean = True)
        
    def visit_article(self, fullname):
        if self._doc_root and not fullname.startswith(self._doc_root):
            return
        self._update_document(fullname)

    def update(self, statuses):
        self.pre_walk()
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status not in ['A','M','R']:
                continue
            self.visit_article(fullname)
        self.post_walk()
        
    def post_walk(self):
        self._writer.commit()
        
    def _update_document(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        mtime = os.path.getmtime(self._store._name2file(fullname))
        tags = article.get_metadata('tags', '')
        self._writer.update_document(fullname = unicode(article.fullname),
                                     mtime = mtime,
                                     tags = unicode(tags))
        
    def _create_schema(self):
        schema = Schema(fullname = ID(stored=True, unique=True),
                        mtime = STORED,
                        tags = KEYWORD(commas=True))
        return schema
    
    def _get_writer(self, clean):
        if not os.path.exists(self._index_dir):
            os.mkdir(self._index_dir)

        if clean or not exists_in(self._index_dir, self._index_name):
            schema = self._create_schema()
            ix = create_in(self._index_dir, schema = schema,
                           indexname = self._index_name)
        else:
            ix = open_dir(self._index_dir, indexname = self._index_name)
            
        return ix.writer()


class TagView(object):
    def __init__(self, store, yawtview, index_dir, index_name):
        self._yawtview = yawtview
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        
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
        Fetch collection of articles by tag.
        """
        ix = open_dir(self._index_dir, indexname = self._index_name)
        search_results = None
        searcher = None
        results = []
        with ix.searcher() as searcher:
            qp = QueryParser('tags', schema = ix.schema)
            q = qp.parse(unicode(tag))
            search_results = searcher.search(q, limit=None)    
            if search_results is not None:
                for sr in search_results:
                    article = self._store.fetch_article_by_fullname(sr['fullname'])
                    results.append(article)
        results = filter(lambda a: a.fullname.startswith(category), results)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
     
class TaggingPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'tagging',
            'BASE': ''
        }

    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        @app.template_filter('tags')
        def tags(article):
            tag_links = []
            for tag in article_tags(article):
                tag_links.append({'tag': tag, 'url': tag_url(self._get_base(), tag)})
            return tag_links
    
        @app.route('/tags/<tag>/')
        def tag_canonical(tag):
            return self._handle_tag_url(None, '', tag)

        @app.route('/tags/<tag>/index')
        def tag_index(tag):
            return self._handle_tag_url(None, '', tag)
        
        @app.route('/<path:category>/tags/<tag>/')
        def tag_category_canonical(category, tag):
            return self._handle_tag_url(None, category, tag)

        @app.route('/<path:category>/tags/<tag>/index')
        def tag_category_index(category, tag):
            return self._handle_tag_url(None, category, tag)

        @app.route('/tags/<tag>/index.<flav>')
        def tag_index_flav(tag):
            return self._handle_tag_url(flav, '', tag)

        @app.route('/<path:category>/tags/<tag>/index.<flav>')
        def tag_category_index_flav(category, tag):
            return self._handle_tag_url(flav, category, tag)

    def walker(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return TagIndexer(store, self._get_index_dir(), self._get_index_name())
    
    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']

    def _get_base(self):
        base = self._plugin_config()['BASE'].strip()
        return base.rstrip('/')
    
    def _plugin_config(self):
        return self.app.config[self.name]
    
    def _create_tag_view(self):
        return TagView(g.store, YawtView(g.plugins, yawt.util.get_content_types()),
                       self._get_index_dir(), self._get_index_name())

    def _handle_tag_url(self, flavour, category, tag):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1

        tag_view = self._create_tag_view()
        return tag_view.dispatch_request(flavour, category, tag, page,
                                         int(g.config['YAWT_PAGE_SIZE']), request.base_url)

def create_plugin():
    return TaggingPlugin()
