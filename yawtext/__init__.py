"""The YAWT extension package.
This file contains utility classes in use by various extensions in YAWT
"""
from __future__ import absolute_import

import os

import jsonpickle
from flask import g, request

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


class BranchedVisitor(Plugin):
    """Visitor plugin which will divide the article space into groups that
    match the root folders supplied.  It will instantiate a separate visitor
    for each root folder and make sure that it only gets artidles for the
    that root"""
    def __init__(self, roots_cfg, processor_factory, app=None):
        super(BranchedVisitor, self).__init__(app)
        self.roots_cfg = roots_cfg
        self.processor_factory = processor_factory
        self.processors = {}

    def _roots(self):
        return cfg(self.roots_cfg) or ['']

    def on_pre_walk(self):
        """Lazily create the processor for each root and call on_pre_walk()
        on them"""
        for root in self._roots():
            processor = self.processor_factory(root)
            self.processors[root] = processor
            processor.on_pre_walk()

    def on_visit_article(self, article):
        """call on_visit_article(), but only for those visitors which need to
        process the article"""
        for root in [r for r in self._roots() if article.info.under(r)]:
            self.processors[root].on_visit_article(article)

    def on_post_walk(self):
        """Call on_post_walk() for all visitors"""
        for root in self._roots():
            self.processors[root].on_post_walk()

    def on_files_changed(self, changed):
        split_map = {}
        for root in self._roots():
            path = os.path.join(content_folder(), root)
            split_map[root] = changed.filter(path)
        for root in split_map.keys():
            processor = self.processor_factory(root)
            processor.on_files_changed(split_map[root])


class ArticleProcessor(object):
    """A plugin implementing the Walk protocol that will only be expecting
    a subset of the site's articles, matching those under the defined root"""

    def __init__(self, root=None):
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
        changed = changed.content_changes().normalize()
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
        path = os.path.join(abs_state_folder(),
                            self.plugin_name,
                            self.root,
                            self.summary_file)
        return path

    @staticmethod
    def context_processor(summaryfile_cfg, bases_cfg, varname):
        """Return a single value dictionary containing the summary file which
        currently applies"""
        summary_file = cfg(summaryfile_cfg)
        bases = cfg(bases_cfg) or ['']
        for base in bases:
            if request.path.startswith('/'+base):
                path = os.path.join(abs_state_folder(), base, summary_file)
                loaded_file = load_file(path)
                return single_dict_var(varname, jsonpickle.decode(loaded_file))
        return {}


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
