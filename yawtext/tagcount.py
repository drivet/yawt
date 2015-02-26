from flask import current_app, g, Blueprint
import jsonpickle
from yawt.utils import save_file, load_file
import os
import re

tagcountsbp = Blueprint('tagcounts', __name__)

def _config(key):
    return current_app.config[key]

def fullname(repofile):
    content_root = _config('YAWT_CONTENT_FOLDER')
    if not repofile.startswith(content_root):
        return None
    rel_filename = re.sub('^%s/' % (content_root), '', repofile) 
    name, ext = os.path.splitext(rel_filename)
    ext = ext[1:]
    if ext not in _config('YAWT_ARTICLE_EXTENSIONS'):
        return None 
    return name


class TagInfo(object):
    def __init__(self):
        self.tagcounts = {}

        # record of name to tags so we know what to remove if the article
        # gets deleted
        self.name2tags = {}


@tagcountsbp.app_context_processor
def tagcounts():
    tagcountfile = current_app.config['YAWT_TAGCOUNT_FILE']
    tvars = {}
    if os.path.isfile(tagcountfile):
        tagbase = current_app.config['YAWT_TAGCOUNT_BASE']
        if not tagbase.endswith('/'):
            tagbase += '/'

        taginfo = jsonpickle.decode(load_file(tagcountfile))
        tagcounts = taginfo.tagcounts
        tvars = {'tagcounts': tagcounts, 'tagbase': tagbase}
    return tvars


class YawtTagCount(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.taginfo = TagInfo()

    def init_app(self, app):
        app.config.setdefault('YAWT_TAGCOUNT_BASE', '')
        app.config.setdefault('YAWT_TAGCOUNT_FILE', '/tmp/tagcounts')
        app.register_blueprint(tagcountsbp)

    def on_pre_walk(self):
        self.taginfo = TagInfo()

    def on_visit_article(self, article):
        if hasattr(article.info, 'taglist'):
            self.taginfo.name2tags[article.info.fullname] = article.info.taglist
            for tag in article.info.taglist:
                if tag in self.taginfo.tagcounts:
                    self.taginfo.tagcounts[tag] += 1
                else:
                    self.taginfo.tagcounts[tag] = 1

    def on_post_walk(self): 
        pickled_info = jsonpickle.encode(self.taginfo)
        save_file(current_app.config['YAWT_TAGCOUNT_FILE'], pickled_info)

    def on_files_changed(self, files_modified, files_added, files_removed):
        pickled_info = load_file(current_app.config['YAWT_TAGCOUNT_FILE'])
        self.taginfo = jsonpickle.decode(pickled_info)

        for f in files_removed + files_modified:
            name = fullname(f)
            tags_to_remove = self.taginfo.name2tags[name]
            del self.taginfo.name2tags[name]
            for tag in tags_to_remove:
                self.taginfo.tagcounts[tag] -= 1

        for f in files_modified + files_added:
            article = g.site.fetch_article_by_repofile(f)
            if article:
                self.on_visit_article(article)

        self.delete_unused_tags()
        
        self.on_post_walk()

    def delete_unused_tags(self):
        unused_tags = []
        for tag in self.taginfo.tagcounts:
            if self.taginfo.tagcounts[tag] == 0:
                unused_tags.append(tag)

        for tag in unused_tags:
            del self.taginfo.tagcounts[tag]
