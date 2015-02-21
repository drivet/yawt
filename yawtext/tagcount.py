from flask import current_app, g, Blueprint
import jsonpickle
from yawt.utils import save_file, load_file
import os

tagcountsbp = Blueprint('tagcounts', __name__)

@tagcountsbp.app_context_processor
def tagcounts():
    tagcountfile = current_app.config['YAWT_TAGCOUNT_FILE']
    tvars = {}
    if os.path.isfile(tagcountfile):
        tagbase = current_app.config['YAWT_TAGCOUNT_BASE']
        if not tagbase.endswith('/'):
            tagbase += '/'
        tvars = {'tagcounts': jsonpickle.decode(load_file(tagcountfile)),
                 'tagbase': tagbase}
    return tvars


class YawtTagCount(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.tagcounts = {}

    def init_app(self, app):
        app.config.setdefault('YAWT_TAGCOUNT_BASE', '')
        app.config.setdefault('YAWT_TAGCOUNT_FILE', '/tmp/tagcounts')
        app.register_blueprint(tagcountsbp)

    def on_pre_walk(self):
        self.tagcounts = {}

    def on_visit_article(self, article):
        if hasattr(article.info, 'taglist'):
            for tag in article.info.taglist:
                if tag in self.tagcounts:
                    self.tagcounts[tag] += 1
                else:
                    self.tagcounts[tag] = 1

    def on_post_walk(self): 
        pickled_counts = jsonpickle.encode(self.tagcounts)
        save_file(current_app.config['YAWT_TAGCOUNT_FILE'], pickled_counts)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_counts = load_file(current_app.config['YAWT_TAGCOUNT_FILE'])
        self.tagcounts = jsonpickle.decode(pickled_counts)

        for f in files_removed + files_modified: 
            article = g.store.fetch_article_by_repofile(f)
            for tag in article.info.taglist:
                self.tagcounts[tag] -= 1

        for f in files_modified + files_added:
            article = g.store.fetch_article_by_repofile(f)
            self.on_visit_article(article)

        self.on_post_walk()
