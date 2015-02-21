from flask import current_app, Blueprint, g
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh

taggingbp = Blueprint('tagging', __name__)

class TaggingView(CollectionView): 
    def dispatch_request(self, *args, **kwargs):
        g.tag = kwargs['tag']
        return super(TaggingView, self).dispatch_request(*args, **kwargs)
        
    def query(self, category='', tag=None, *args, **kwargs):
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
        app.config.setdefault('YAWT_TAGGING_TEMPLATE', 'article_list')
        app.register_blueprint(taggingbp)

    def on_article_fetch(self, article):
        if (not hasattr(article.info, 'indexed') or not article.info.indexed) and \
           hasattr(article.info, 'tags'):
            tags_meta = article.info.tags
            article.info.taglist = [x.strip() for x in tags_meta.split(',')] 
        return article

    def on_article_index(self, article):
        """
        We can handle the indexing plugin if it's there
        """
        tags_meta = article.info.tags
        article.info.taglist = [x.strip() for x in tags_meta.split(',')] 
        return article

@taggingbp.context_processor
def collection_title():
    return {'collection_title': 'Found %s tag results for "%s"' % (g.total_results, g.tag)}

taggingbp.add_url_rule('/tags/<tag>/', view_func=TaggingView.as_view('tag_canonical'))
taggingbp.add_url_rule('/tags/<tag>/index', view_func=TaggingView.as_view('tag_index'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/', 
                       view_func=TaggingView.as_view('tag_category_canonical'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index', 
                       view_func=TaggingView.as_view('tag_category_index'))
taggingbp.add_url_rule('/<tag>/index.<flav>', view_func=TaggingView.as_view('tag_index_flav'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index.<flav>', 
                       view_func=TaggingView.as_view('tag_category_index_flav'))
