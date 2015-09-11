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

from yawt.utils import cfg
from yawtext import Plugin, SummaryProcessor, BranchedVisitor
from yawtext.collections import CollectionView
from yawtext.indexer import search


taggingbp = Blueprint('tagging', __name__)


@taggingbp.app_context_processor
def _tagcounts_cp():
    return SummaryProcessor.context_processor('YAWT_TAGGING_COUNT_FILE',
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
        return unicode(query_str)

    def get_template_name(self):
        return current_app.config['YAWT_TAGGING_TEMPLATE']

    def is_load_articles(self, flav):
        return flav in current_app.config['YAWT_TAGGING_FULL_ARTICLE_FLAVOURS']


class TagProcessor(SummaryProcessor):
    """Subclass of SummaryProcessor which counts tags under a root"""
    def __init__(self, root=''):
        super(TagProcessor, self).__init__(root, '',
                                           cfg('YAWT_TAGGING_COUNT_FILE'))

    def _init_summary(self):
        self.summary = {}

    def on_visit_article(self, article):
        if hasattr(article.info, 'tags'):
            for tag in article.info.tags:
                if tag in self.summary:
                    self.summary[tag] += 1
                else:
                    self.summary[tag] = 1

    def unvisit(self, name):
        tags_to_remove = self._tags_for_name(name)
        for tag in tags_to_remove:
            if tag in self.summary:
                self.summary[tag] -= 1
        self._delete_unused_tags()

    def _tags_for_name(self, name):
        infos = search(unicode('fullname:'+name))
        tags = []
        if len(infos) > 0:
            if hasattr(infos[0], 'tags') and infos[0].tags:
                tags = infos[0].tags
        return tags

    def _delete_unused_tags(self):
        unused_tags = []
        for tag in self.summary:
            if self.summary[tag] == 0 and tag not in unused_tags:
                unused_tags.append(tag)

        for tag in unused_tags:
            if tag in self.summary:
                del self.summary[tag]


class YawtTagging(Plugin):
    """The YAWT tagging plugin class itself"""
    def __init__(self, app=None):
        super(YawtTagging, self).__init__(app)
        self.visitor = None

    def init_app(self, app):
        """Set up some default config and register the blueprint"""
        app.config.setdefault('YAWT_TAGGING_TEMPLATE', 'article_list')
        app.config.setdefault('YAWT_TAGGING_FULL_ARTICLE_FLAVOURS', [])
        app.register_blueprint(taggingbp)


class YawtTagCounter(BranchedVisitor):
    """The Yawt tag counter plugin"""
    def __init__(self, app=None):
        super(YawtTagCounter, self).__init__('YAWT_TAGGING_BASE',
                                             TagProcessor,
                                             app)

    def init_app(self, app):
        """set some default config"""
        app.config.setdefault('YAWT_TAGGING_BASE', [])
        app.config.setdefault('YAWT_TAGGING_COUNT_FILE', 'tagcounts')


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
