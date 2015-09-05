"""The YAWT tagging module.

A YAWT module which provides tagging functionality.

This module implements the walk protocol.  For each article in the repository,
it will:

- index the tags in the article
- keep a running count of the tags seen in the repository, acccording to the
  base categories configured.

Tags are stored in the "tags" key in YAML frontmatter for each article.

Tag counts are stored as JSON pickled data in a file whose path is defined by
the concatenation of

- the base (from YAWT_TAGGING_BASE) used to define the particular set of counts
  you want
- the YAWT_TAGGING_COUNT_FILE value

YAWT_TAGGING_BASE is a list.  One tag count file will be produced for every
base defined in this list.

In addition, the tag count files are made available to templates via the
tagcounts template variable, which is a map of bases mapped to tag counts maps.

"""
from __future__ import absolute_import

from flask import current_app, Blueprint, g
from whoosh.qparser import QueryParser
import jsonpickle

from yawt.utils import save_file, load_file, fullname,\
    cfg, abs_state_folder
from yawtext.base_state_files import StateFiles, state_context_processor
from yawtext.collections import CollectionView
from yawtext.indexer import schema
from yawtext import Plugin


taggingbp = Blueprint('tagging', __name__)


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


@taggingbp.app_context_processor
def _tagcounts_cp():
    return state_context_processor('YAWT_TAGGING_COUNT_FILE',
                                   'YAWT_TAGGING_BASE',
                                   'tagcounts')

@taggingbp.context_processor
def _collection_title():
    return {'collection_title':
            'Found %s tag results for "%s"' % (g.total_results, g.tag)}


class TaggingView(CollectionView):
    """The Tagging view.  Use this to display collections of article which
    match a tag.
    """
    def dispatch_request(self, *args, **kwargs):
        g.tag = kwargs['tag']  # for use in templates
        return super(TaggingView, self).dispatch_request(*args, **kwargs)

    def query(self, category='', tag=None, *args, **kwargs):
        query_str = 'tags:' + tag
        if category:
            query_str += ' AND ' + category
        qparser = QueryParser('categories', schema=schema())
        return qparser.parse(unicode(query_str))

    def get_template_name(self):
        return current_app.config['YAWT_TAGGING_TEMPLATE']

    def is_load_articles(self, flav):
        return flav in current_app.config['YAWT_TAGGING_FULL_ARTICLE_FLAVOURS']


class YawtTagging(Plugin):
    """The YAWT tagging plugin class itself"""
    def __init__(self, app=None):
        super(YawtTagging, self).__init__(app)
        self.tagcountmap = {}

    def init_app(self, app):
        """Set up some default config and register the blueprint"""
        app.config.setdefault('YAWT_TAGGING_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_TAGGING_BASE', [''])
        app.config.setdefault('YAWT_TAGGING_COUNT_FILE', 'tagcounts')
        app.config.setdefault('YAWT_TAGGING_FULL_ARTICLE_FLAVOURS', [])
        app.register_blueprint(taggingbp)

    def on_pre_walk(self):
        """Initialize the tag counts"""
        self.tagcountmap = {}
        for base in current_app.config['YAWT_TAGGING_BASE']:
            self.tagcountmap[base] = {}

    def on_visit_article(self, article):
        """Count the tags for this article"""
        if hasattr(article.info, 'tags'):
            for base in [b for b in cfg('YAWT_TAGGING_BASE')
                         if article.info.under(b)]:
                for tag in article.info.tags:
                    if tag in self.tagcountmap[base]:
                        self.tagcountmap[base][tag] += 1
                    else:
                        self.tagcountmap[base][tag] = 1

    def on_post_walk(self):
        """Save the tag counts to disk"""
        statefiles = StateFiles(abs_state_folder(), cfg('YAWT_TAGGING_COUNT_FILE'))
        for base in self.tagcountmap:
            tagcounts = self.tagcountmap[base]
            pickled_info = jsonpickle.encode(tagcounts)
            save_file(statefiles.abs_state_file(base), pickled_info)

    def on_files_changed(self, changed):
        """pass in three lists of files, modified, added, removed, all
        relative to the *repo* root, not the content root (so these are
        not absolute filenames)
        """
        changed = changed.content_changes().normalize()
        statefiles = StateFiles(abs_state_folder(), cfg('YAWT_TAGGING_COUNT_FILE'))
        for base in current_app.config['YAWT_TAGGING_BASE']:
            pickled_info = load_file(statefiles.abs_state_file(base))
            self.tagcountmap[base] = jsonpickle.decode(pickled_info)
            for f in changed.deleted + changed.modified:
                name = fullname(f)
                if name:
                    tags_to_remove = self._tags_for_name(name)
                    for tag in tags_to_remove:
                        if tag in self.tagcountmap[base]:
                            self.tagcountmap[base][tag] -= 1

        map(self.on_visit_article,
            g.site.fetch_articles_by_repofiles(changed.modified + changed.added))

        self._delete_unused_tags()

        self.on_post_walk()

    def _tags_for_name(self, name):
        searcher = _whoosh().searcher
        qparser = QueryParser('fullname', schema=schema())
        query = qparser.parse(unicode(name))
        results = searcher.search(query)
        tags = []
        if len(results) > 0:
            info = jsonpickle.decode(results[0]['article_info_json'])
            if hasattr(info, 'tags') and info.tags:
                tags = info.tags
        return tags

    def _delete_unused_tags(self):
        unused_tags = []
        for base in current_app.config['YAWT_TAGGING_BASE']:
            for tag in self.tagcountmap[base]:
                if self.tagcountmap[base][tag] == 0 and \
                   tag not in unused_tags:
                    unused_tags.append(tag)

        for tag in unused_tags:
            for base in current_app.config['YAWT_TAGGING_BASE']:
                if tag in self.tagcountmap[base]:
                    del self.tagcountmap[base][tag]


taggingbp.add_url_rule('/tags/<tag>/',
                       view_func=TaggingView.as_view('tag_canonical'))
taggingbp.add_url_rule('/tags/<tag>/index',
                       view_func=TaggingView.as_view('tag_index'))
taggingbp.add_url_rule('/tags/<tag>/index.<flav>',
                       view_func=TaggingView.as_view('tag_index_flav'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/',
                       view_func=TaggingView.as_view('tag_category_canonical'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index',
                       view_func=TaggingView.as_view('tag_category_index'))
taggingbp.add_url_rule('/<path:category>/tags/<tag>/index.<flav>',
                       view_func=TaggingView.as_view('tag_category_index_flav'))
