"""YAWT Indexing extension

The goal here is to index each article using Whoosh and the configured fields.
The indexing itself is done via the walk phase and the on_files_changed phase.
"""
from __future__ import absolute_import

from flask import g
from whoosh.fields import TEXT

from yawt.utils import fullname, cfg
from yawtext import Plugin


def update_index(added, modified, removed):
    """Delete all modified and removed files from the index.  Then index
    all the added files and re-index all the modifed files.
    """
    for repofile in removed + modified:
        name = fullname(repofile)
        if name:
            remove_article(name)

    for repofile in modified + added:
        article = g.site.fetch_article_by_repofile(repofile)
        if article:
            add_article(article)

    commit()


class YawtIndexer(Plugin):
    """YAWT Whoosh extension class.  Implement the walk and on_file_changed
    protocol.
    """
    def __init__(self, app=None):
        super(YawtIndexer, self).__init__(app)

    def init_app(self, app):
        """Set up default config values.  By default we index content"""
        app.config.setdefault('YAWT_INDEXER_IFC', 'yawtext.whoosh')
        app.config.setdefault('YAWT_INDEXER_WHOOSH_INFO_FIELDS', {})
        app.config.setdefault('YAWT_INDEXER_WHOOSH_FIELDS', {'content': TEXT()})

    def on_new_site(self, files):
        """Set up the index when we crate a new site"""
        init_index()

    def on_pre_walk(self):
        """Clear the index"""
        init_index(clear=True)

    def on_visit_article(self, article):
        """Index this article"""
        add_article(article)

    def on_post_walk(self):
        """Commit the index"""
        commit()

    def on_files_changed(self, changed):
        changed = changed.content_changes().normalize()
        update_index(changed.added, changed.modified, changed.deleted)


# Indexing API starts here

def init_index(clear=False):
    """Create the index, optionally clearing it first"""
    return _run_indexer_func("init_index", clear)


def add_article(article):
    """Index the supplied article"""
    return _run_indexer_func("add_article", article)


def search(query, sortedby=None, reverse=False):
    """Search the index using the supplied query string"""
    return _run_indexer_func("search", query, sortedby, reverse)


def search_page(query, sortedby, page, pagelen, reverse=False):
    """Search the index using the supplied query string, giving back the
    specified page"""
    return _run_indexer_func("search_page", query, sortedby,
                             page, pagelen, reverse)


def remove_article(fname):
    """Remove article at fullname ferom index"""
    return _run_indexer_func("remove_article", fname)


def commit():
    """Commit the index changes"""
    return _run_indexer_func("commit")


def _run_indexer_func(funcname, *args, **kwargs):
    temp = __import__(cfg('YAWT_INDEXER_IFC'),
                      globals(), locals(), [funcname])
    return getattr(temp, funcname)(*args, **kwargs)
