from flask import current_app, Blueprint, g
from whoosh.qparser import QueryParser
from yawtext.collections import CollectionView, yawtwhoosh
import jsonpickle
from yawt.utils import save_file, load_file, fullname
import os

taggingbp = Blueprint('tagging', __name__)

def whoosh():
    return current_app.extension_info[0]['whoosh']

def abs_tagcount_file():
    root = current_app.yawt_root_dir
    tagcountfile = current_app.config['YAWT_TAGGING_COUNT_FILE']
    state_folder = current_app.config['YAWT_STATE_FOLDER']
    return os.path.join(root, state_folder, tagcountfile)


@taggingbp.app_context_processor
def tagcounts_cp():
    tagcountfile = abs_tagcount_file()
    tvars = {}
    if os.path.isfile(tagcountfile):
        tagbase = current_app.config['YAWT_TAGGING_BASE']
        if not tagbase.endswith('/'):
            tagbase += '/'

        tagcounts = jsonpickle.decode(load_file(tagcountfile))
        tvars = {'tagcounts': tagcounts, 'tagbase': tagbase}
    return tvars

        
@taggingbp.context_processor
def collection_title():
    return {'collection_title': 'Found %s tag results for "%s"' % (g.total_results, g.tag)}

    
class TaggingView(CollectionView): 
    def dispatch_request(self, *args, **kwargs):
        g.tag = kwargs['tag'] # for use in templates
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
        self.tagcounts = {}
            
    def init_app(self, app):
        app.config.setdefault('YAWT_TAGGING_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_TAGGING_BASE', '')
        app.config.setdefault('YAWT_TAGGING_COUNT_FILE', 'tagcounts')
        app.register_blueprint(taggingbp)

    def on_pre_walk(self):
        self.tagcounts = {}

    def on_visit_article(self, article):
        if hasattr(article.info, 'tags'):
            for tag in article.info.tags:
                if tag in self.tagcounts:
                    self.tagcounts[tag] += 1
                else:
                    self.tagcounts[tag] = 1

    def on_post_walk(self): 
        pickled_info = jsonpickle.encode(self.tagcounts)
        save_file(abs_tagcount_file(), pickled_info)

    def on_files_changed(self, files_modified, files_added, files_removed):
        """pass in three lists of files, modified, added, removed, all relative to
        the *repo* root, not the content root (so these are not absolute
        filenames)
        """
        pickled_info = load_file(abs_tagcount_file())
        self.tagcounts = jsonpickle.decode(pickled_info)
        for f in files_removed + files_modified: 
            name = fullname(f)
            if name: 
                tags_to_remove = self.tags_for_name(name)
               
                for tag in tags_to_remove:
                    self.tagcounts[tag] -= 1

        for f in files_modified + files_added: 
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.delete_unused_tags()
        
        self.on_post_walk()

    def tags_for_name(self, name):
        searcher = whoosh().searcher
        qp = QueryParser('fullname', schema=yawtwhoosh().schema())
        q = qp.parse(unicode(name))
        results = searcher.search(q)
        tags = []
        if len(results) > 0: 
            info = jsonpickle.decode(results[0]['article_info_json'])
            tags = info.tags
        return tags

    def delete_unused_tags(self):
        unused_tags = []
        for tag in self.tagcounts:
            if self.tagcounts[tag] == 0:
                unused_tags.append(tag)

        for tag in unused_tags:
            del self.tagcounts[tag]


taggingbp.add_url_rule('/tags/<tag>/', view_func=TaggingView.as_view('tag_canonical'))
taggingbp.add_url_rule('/tags/<tag>/index', view_func=TaggingView.as_view('tag_index'))
taggingbp.add_url_rule('/tags/<tag>/index.<flav>', view_func=TaggingView.as_view('tag_index_flav'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/', 
                       view_func=TaggingView.as_view('tag_category_canonical'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index', 
                       view_func=TaggingView.as_view('tag_category_index'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index.<flav>', 
                       view_func=TaggingView.as_view('tag_category_index_flav'))
