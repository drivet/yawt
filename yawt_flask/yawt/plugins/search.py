import os
from yawt.view import YawtView
from flask import g, request

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

index_dir = 'whoosh_index'
index_name = 'fulltextsearch'

class SearchView(YawtView):
    def __init__(self, store):
        super(SearchView, self).__init__()
        self._store = store
  
    def dispatch_request(self, flavour, search_text):
        articles = self._fetch_articles_by_text(search_text)
        if len(articles) < 1:
            return self.handle_missing_resource()
        else:
            if flavour is None:
                flavour = 'html'
            return self.render_collection(flavour, articles, self._search_title(search_text))
  
    def _search_title(self, search_text):
        return 'Search results for: %s' % search_text
 
    def _fetch_articles_by_text(self, searchtext):
        """
        Fetch collection of articles by searchtext.
        """
        ix = open_dir(index_dir, indexname = index_name)
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
        return results
    
class CleanIndexer(object):
    def __init__(self, store, index_root, index_name):
        self._store = store
        self._index_root = index_root
        self._index_name = index_name

    def pre_walk(self):
        if not os.path.exists(self._index_root):
            os.mkdir(self._index_root)
            
        schema = Schema(fullname=ID(stored=True),
                        mtime=STORED,
                        title=TEXT(stored=True),
                        content=TEXT)
             
        ix = create_in(self._index_root, schema = schema,
                       indexname = self._index_name)
    
        self._writer = ix.writer()
        
    def visit_article(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        mtime = os.path.getmtime(self._store._name2file(fullname))
        self._writer.add_document(fullname = unicode(article.fullname),
                                  mtime = mtime,
                                  title = unicode(article.title),
                                  content = unicode(article.content))
        
    def post_walk(self):
        self._writer.commit()
        
class IncrementalIndexer(object):
    def __init__(self, store, index_root, index_name):
        self._store = store
        self._index_root = index_root
        self._index_name = index_name

    def pre_walk(self):
        ix = open_dir(self._index_root, indexname = self._index_name)
        searcher = ix.searcher()
        self._writer = ix.writer()

        # The set of all paths in the index
        self._indexed_paths = set()
        
        # The set of all paths we need to re-index
        self._to_index = set()
        
        # Loop over the stored fields in the index
        for fields in searcher.all_stored_fields():
             indexed_name = fields['fullname']
             path = self._store._name2file(indexed_name)
             self._indexed_paths.add(path)
             
             if not os.path.exists(path):
                 # This file was deleted since it was indexed
                 self._writer.delete_by_term('fullname', indexed_name)
             else:
                 # Check if this file was changed since it
                 # was indexed
                 indexed_time = fields['mtime']
                 mtime = os.path.getmtime(path)
                 if mtime > indexed_time:
                     # The file has changed, delete it and add it to the list of
                     # files to reindex
                     self._writer.delete_by_term('fullname', indexed_name)
                     self._to_index.add(path)
        
    def visit_article(self, fullname):
        filename = self.store._name2file(fullname)
        if filename in self._to_index or filename not in self._indexed_paths:
            # This is either a file that's changed, or a new file
            # that wasn't indexed before. So index it!
            article = self._store.fetch_article_by_fullname(af)
            self._writer.add_document(fullname = unicode(article.fullname),
                                      mtime = mtime,
                                      title = unicode(article.title),
                                      content = unicode(article.content))
                
    def post_walk(self):
        self._writer.commit()
  
def init(app):
    # Search URL
    @app.route('/search/', methods=['POST', 'GET'])
    def full_text_search():
        return _full_text_search(request, None)

    @app.route('/search/index', methods=['POST', 'GET'])
    def full_text_search_index():
        return _full_text_search(request,None)

    @app.route('/search/index.<flav>', methods=['POST', 'GET'])
    def full_text_search_index():
        return _full_text_search(request, flav)

    def _full_text_search(request, flav):
        search_text = request.args.get('searchtext', '')
        return SearchView(g.store).dispatch_request(flav, search_text)
           
def walker(store):
    return CleanIndexer(store, index_dir, index_name)
