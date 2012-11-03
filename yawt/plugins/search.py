import os
from yawt.view import YawtView, PagingInfo
import yawt
from flask import g, request

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

class SearchView(object):
    def __init__(self, store, yawtview, index_dir, index_name):
        self._yawtview = yawtview
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
  
    def dispatch_request(self, flavour, category, search_text, page, page_size, base_url):
        articles = filter(lambda a: a.is_in_category(category),
                          self._fetch_articles_by_text(category, search_text))
        if len(articles) < 1:
            return self._yawtview.render_missing_resource()
        else:
            page_info = PagingInfo(page, page_size, len(articles), base_url)
            return self._render_collection(flavour, articles, search_text, page_info, category)
        
    def _render_collection(self, flavour, articles, search_text, page_info, category):
        title = self._search_title(search_text)
        return self._yawtview.render_collection(flavour, articles, title, page_info, category)
                                                      
    def _search_title(self, search_text):
        return 'Search results for: "%s"' % search_text
 
    def _fetch_articles_by_text(self, category, searchtext):
        """
        Fetch collection of articles by searchtext.
        """
        ix = open_dir(self._index_dir, indexname = self._index_name)
        search_results = None
        searcher = None
        results = []
        with ix.searcher() as searcher:
            qp = QueryParser('content', schema = ix.schema)
            q = qp.parse(unicode(searchtext))
            search_results = searcher.search(q, limit=None)    
            if search_results is not None:
                for sr in search_results:
                    article = self._store.fetch_article_by_fullname(sr['fullname'])
                    results.append(article)
        results = filter(lambda a: a.fullname.startswith(category), results)
        return sorted(results, key = lambda info: info.ctime, reverse=True)

class TextIndexer(object):
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
        self._writer.update_document(fullname = unicode(article.fullname),
                                     mtime = mtime,
                                     title = unicode(article.title),
                                     content = unicode(article.content))
            
    def _create_schema(self):
        schema = Schema(fullname=ID(stored=True, unique=True),
                        mtime=STORED,
                        title=TEXT(stored=True),
                        content=TEXT)
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


class SearchPlugin(object):
    def __init__(self):
        self.default_config = {
            'INDEX_DIR': '_whoosh_index',
            'INDEX_NAME': 'fulltextsearch',
            'BASE': ''
        }
        
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        @app.route('/search/', methods=['POST', 'GET'])
        def full_text_search():
            return self._full_text_search(request, None, '')
        
        @app.route('/<path:category>/search/', methods=['POST', 'GET'])
        def full_text_search(category):
            return self._full_text_search(request, None, category)
        
        @app.route('/search/index', methods=['POST', 'GET'])
        def full_text_search_index():
            return self._full_text_search(request, None, '')
        
        @app.route('/<path:category>/search/index', methods=['POST', 'GET'])
        def full_text_search_index(category):
            return self._full_text_search(request, None, category)
        
        @app.route('/search/index.<flav>', methods=['POST', 'GET'])
        def full_text_search_index():
            return self._full_text_search(request, flav, '')
        
        @app.route('/<path:category>/search/index.<flav>', methods=['POST', 'GET'])
        def full_text_search_index(category):
            return self._full_text_search(request, flav, category)

    def walker(self, store):
        return TextIndexer(store, self._get_index_dir(), self._get_index_name())

    def updater(self, store):
        return TextIndexer(store, self._get_index_dir(), self._get_index_name())

    def _get_index_dir(self):
        return yawt.util.get_abs_path_app(self.app, self._plugin_config()['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config()['INDEX_NAME']

    def _plugin_config(self):
        return self.app.config[self.name]
    
    def _full_text_search(self, request, flav, category):
        page = 1
        try:
            page = int(request.args.get('page', '1'))
        except ValueError:
            page = 1
            
        search_text = request.args.get('searchtext', '')
        sv = self._create_search_view()
        return sv.dispatch_request(flav, category, search_text,
                                   page, g.config['YAWT_PAGE_SIZE'], request.base_url)

    def _create_search_view(self):
        return SearchView(g.store, YawtView(g.plugins, yawt.util.get_content_types()),
                          self._get_index_dir(), self._get_index_name())


def create_plugin():
    return SearchPlugin()
