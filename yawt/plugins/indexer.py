import os

from flask import g, current_app
from flask.views import View
from whoosh.fields import Schema, STORED, ID
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

import yawt.util
from yawt.view import YawtView, ArticleListView
import yawt.fileutils


class ArticleIndexer(object):
    def __init__(self, store, index_dir, index_name, doc_root=None):
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        self._doc_root = doc_root
        self._writer = None

    def pre_walk(self):
        self._writer = self._get_writer(clean = True)
        
    def visit_article(self, fullname):
        if self._doc_root and not fullname.startswith(self._doc_root):
            return
        self._update_document(fullname)

    def update(self, statuses):
        self._writer = self._get_writer()
        for fullname in statuses.keys():
            status = statuses[fullname]
            if status == 'A' or status == 'M':
                self.visit_article(fullname)
            elif status == 'R':
                self._delete_document(fullname)
            else:
                continue
        self._writer.commit()
    
    def post_walk(self):
        self._writer.commit()
    
    def _delete_document(self, fullname):
        self._writer.delete_by_term('fullname', unicode(fullname))

    def _update_document(self, fullname):
        article = self._store.fetch_article_by_fullname(fullname)
        mtime = os.path.getmtime(self._store._name2file(article.fullname, article.ext))
        fields = {'fullname': unicode(article.fullname), 'mtime': mtime}
        fields.update(self._get_article_fields(article))
        self._writer.update_document(**fields)

    def _get_writer(self, clean = False):
        if not os.path.exists(self._index_dir):
            os.mkdir(self._index_dir)
        if clean or not exists_in(self._index_dir, self._index_name):
            fields = {'fullname': ID(stored=True, unique=True), 'mtime': STORED}
            fields.update(self._get_schema_fields())
            schema = Schema(**fields)
            ix = create_in(self._index_dir, schema = schema,
                           indexname = self._index_name)
        else:
            ix = open_dir(self._index_dir, indexname = self._index_name)        
        return ix.writer()

    def _get_article_fields(self):
        return {}
        
    def _get_schema_fields(self):
        return {}
    
class ArticleFetcher(object):
    def __init__(self, store, index_dir, index_name):
        self._store = store
        self._index_dir = index_dir
        self._index_name = index_name
        
    def fetch(self, category, default_field, query):
        """
        Fetch collection of indexed articles
        """
        ix = open_dir(self._index_dir, indexname = self._index_name)
        search_results = None
        searcher = None
        results = []
        with ix.searcher() as searcher:
            qp = QueryParser(default_field, schema = ix.schema)
            q = qp.parse(query)
            search_results = searcher.search(q, limit=None)    
            if search_results is not None:
                for sr in search_results:
                    article = self._store.fetch_article_by_fullname(sr['fullname'])
                    results.append(article)
        results = filter(lambda a: a.is_in_category(category), results)
        return sorted(results, key = lambda info: info.ctime, reverse=True)

class IndexView(View):
    def __init__(self, plugin_config):
        self._plugin_config = plugin_config

    def _get_index_dir(self):
        return yawt.fileutils.get_abs_path_app(current_app, self._plugin_config['INDEX_DIR'])

    def _get_index_name(self):
        return self._plugin_config['INDEX_NAME']

class ListIndexView(ArticleListView, IndexView):
    def __init__(self, plugin_config):
        self._plugin_config = plugin_config 
        self._yawtview = YawtView(g.plugins, yawt.util.get_content_types())

    def _fetch(self, category, *args, **kwargs):
        fetcher = ArticleFetcher(g.store, self._get_index_dir(), self._get_index_name())
        return fetcher.fetch(category,
                             self._default_field(*args, **kwargs),
                             self._query(*args, **kwargs))
  
    def _default_field(self, *args, **kwargs):
        return ''
    
    def _query(self, *args, **kwargs):
        return ''
