from flask import current_app
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh


class TaggingView(CollectionView):
    def query(self, category, tag):
        query_str = 'tags:' + tag
        if category:
            query_str += ' AND ' + category
        qp = QueryParser('categories', schema=yawtwhoosh().schema())
        return qp.parse(unicode(query_str))
        
    def get_template_name(self):
        return current_app.config['YAWT_TAGGING_TEMPLATE']

class YawtTagging(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_TAGGING_TEMPLATE', 'article_collection')
        app.add_url_rule('/tags/<tag>/', view_func=TaggingView.as_view('tag_canonical'))
        app.add_url_rule('/tags/<tag>/index', view_func=TaggingView.as_view('tag_index'))
        app.add_url_rule('/<path:category>/tags/<tag>/', 
                         view_func=TaggingView.as_view('tag_category_canonical'))
        app.add_url_rule('/<path:category>/tags/<tag>/index', 
                         view_func=TaggingView.as_view('tag_category_index'))
        app.add_url_rule('/<tag>/index.<flav>', view_func=TaggingView.as_view('tag_index_flav'))
        app.add_url_rule('/<path:category>/tags/<tag>/index.<flav>', 
                         view_func=TaggingView.as_view('tag_category_index_flav'))
