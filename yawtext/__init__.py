"""The YAWT extension package.
This file contains utility classes in use by various extensions in YAWT
"""
from __future__ import absolute_import

import os

import jsonpickle
from flask import g

from yawt.utils import load_file, save_file, abs_state_folder, cfg,\
    single_dict_var, ReprMixin, EqMixin, fullname, content_folder


class Plugin(object):
    """Base YAWT Plugin"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Base implementation of init_app, does nothing"""
        pass


class BranchedVisitor(object):
    """Visitor plugin which will divide the article space into groups that
    match the root folders supplied.  It will instantiate a separate visitor
    for each root folder and make sure that it only gets artidles for the
    that root"""
    def __init__(self, roots, processor_factory):
        self.roots = roots
        self.processor_factory = processor_factory
        self.processors = {}

    def on_pre_walk(self):
        """Lazily create the processor for each root and call on_pre_walk()
        on them"""
        for root in self.roots:
            processor = self.processor_factory(root)
            self.processors[root] = processor
            processor.on_pre_walk()

    def on_visit_article(self, article):
        """call on_visit_article(), but only for those visitors which need to
        process the article"""
        for root in [r for r in self.roots if article.info.under(r)]:
            self.processors[root].on_visit_article(article)

    def on_post_walk(self):
        """Call on_post_walk() for all visitors"""
        for root in self.roots:
            self.processors[root].on_post_walk()

    def on_files_changed(self, changed):
        changed = changed.content_changes().normalize()
        split_map = {}
        for root in self.roots:
            path = os.path.join(content_folder(), root)
            split_map[root] = changed.filter(path)
        for root in split_map.keys():
            processor = self.processor_factory(root)
            processor.on_files_changed(split_map[root])


class ArticleProcessor(object):
    """A plugin implementing the Walk protocol that will only be expecting
    a subset of the site's articles, matching those under the defined root"""

    def __init__(self, root):
        self.root = root

    def on_pre_walk(self):
        pass

    def on_visit_article(self, article):
        pass

    def unvisit(self, name):
        pass

    def on_post_walk(self):
        pass

    def on_files_changed(self, changed):
        for repofile in changed.deleted + changed.modified:
            name = fullname(repofile)
            if name:
                self.unvisit(name)

        map(self.on_visit_article,
            g.site.fetch_articles_by_repofiles(changed.modified +
                                               changed.added))
        self.on_post_walk()


class SummaryProcessor(ArticleProcessor):
    """A special kind of ArticleProcessor which will keep track of a summary
    file (a jsonpickle'd python object) in a _state subfolder matching the
    root supplied.

    Subclasses will typically have to implement _init_summary(),
    on_visit_article() and unvisit().
    """
    def __init__(self, root, plugin_name, summary_file):
        super(SummaryProcessor, self).__init__(root)
        self.plugin_name = plugin_name
        self.summary_file = summary_file
        self.summary = None

    def on_pre_walk(self):
        self._init_summary()

    def _init_summary(self):
        raise NotImplementedError()

    def on_post_walk(self):
        self._save_summary()

    def on_files_changed(self, changed):
        self._load_summary()
        super(SummaryProcessor, self).on_files_changed(changed)

    def _load_summary(self):
        self.summary = jsonpickle.decode(load_file(self._abs_summary_file()))

    def _save_summary(self):
        save_file(self._abs_summary_file(), jsonpickle.encode(self.summary))

    def _abs_summary_file(self):
        return os.path.join(abs_state_folder(),
                            self.plugin_name,
                            self.root,
                            self.summary_file)


class SummaryVisitor(Plugin):
    """Base class for summary plugins.  Need to provide the config for the
    roots and the factory to create the processors"""
    def __init__(self, roots_cfg, processor_factory, app=None):
        super(SummaryVisitor, self).__init__(app)
        self.roots_cfg = roots_cfg
        self.processor_factory = processor_factory
        self.visitor = None

    def _visitor(self):
        roots = cfg(self.roots_cfg)
        if roots:
            return BranchedVisitor(roots, self.processor_factory)
        else:
            return self.processor_factory()

    def on_pre_walk(self):
        """Initialize the archive counts"""
        self.visitor = self._visitor()
        self.visitor.on_pre_walk()

    def on_visit_article(self, article):
        """Count the archives for this article"""
        self.visitor.on_visit_article(article)

    def on_post_walk(self):
        """Save the archive counts to disk"""
        self.visitor.on_post_walk()

    def on_files_changed(self, changed):
        """pass in three lists of files, modified, added, removed, all
        relative to the *repo* root, not the content root (so these are
        not absolute filenames)
        """
        self.visitor = self._visitor()
        self.visitor.on_files_changed(changed)


class StateFiles(ReprMixin):
    """Manages a "state file", which is a json pickled python object stored
    in a file.  The file is named "statefile" and is stored under various
    base folders under root_dir.
    """
    def __init__(self, root_dir, statefile):
        self.root_dir = root_dir
        self.statefile = statefile

    def load_state_files(self, bases):
        """Return a map of base names to loaded statefile objects"""
        statemap = {}
        bases = bases or ['']
        for base in bases:
            abs_state_file = self.abs_state_file(base)
            if os.path.isfile(abs_state_file):
                stateobj = jsonpickle.decode(load_file(abs_state_file))
                statemap[base] = stateobj

        if len(statemap) == 1 and statemap.keys()[0] == '':
            return statemap[statemap.keys()[0]]
        else:
            return statemap

    def save_state_files(self, statefilemap):
        """Save statefilemap to disk, distributing among the bases"""
        for base in statefilemap:
            stateobj = statefilemap[base]
            pickled_info = jsonpickle.encode(stateobj)
            save_file(self.abs_state_file(base), pickled_info)

    def abs_state_file(self, base):
        """Return the absolute filename of the statefile at base"""
        return os.path.join(self.root_dir, base, self.statefile)


def state_context_processor(statefile_cfg, bases_cfg, varname):
    """Return a single value dictionary conating all the statefiles loaded"""
    statefiles = StateFiles(abs_state_folder(), cfg(statefile_cfg))
    stateobj = statefiles.load_state_files(cfg(bases_cfg))
    return single_dict_var(varname, stateobj)


def _split_category(category):
    (head, rest) = category, ''
    if '/' in category:
        (head, rest) = category.split('/', 1)
    return (head, rest)


class HierarchyCount(ReprMixin, EqMixin):
    """Class which can process paths to count a 'hierarchy'.  You pass in
    something like blah/foo.bar and we will count at each level.
    """
    def __init__(self, **kwargs):
        self.category = kwargs.get('category', '')
        self.count = kwargs.get('count', 0)
        self.children = kwargs.get('children', [])

    def add(self, hierarchy):
        """Pass in something like 'blah/foo/hello' and we'll keep track of a
        tree where each node of the tree is an element in the hierarchy,
        keeping track of the counts below it.
        """
        self.count += 1
        if hierarchy:
            (head, rest) = _split_category(hierarchy)
            next_node = None
            for child in self.children:
                if child.category == head:
                    next_node = child
            if next_node is None:
                next_node = HierarchyCount()
                next_node.category = head
                self.children.append(next_node)
            next_node.add(rest)

    def remove(self, hierarchy):
        """Pass in something like 'blah/foo/hello' and we'll keep track of a
        tree where each node of the tree is an element in the hierarchy,
        keeping track of the counts below it."""
        self.count -= 1
        if hierarchy:
            (head, rest) = _split_category(hierarchy)
            for child in self.children:
                if child.category == head:
                    child.remove(rest)
                    break
            self.children = [child for child in self.children
                             if child.count > 0]

    def child(self, category):
        """Return node matching category"""
        for child in self.children:
            if child.category == category:
                return child
        return None

    def sort(self, reverse=False):
        """Recursively sort the children of this tree"""
        if len(self.children) > 0:
            for child in self.children:
                child.sort(reverse)
            self.children.sort(key=lambda c: c.category, reverse=reverse)
