"""The YAWT extension package.
This file contains utility classes in use by various extensions in YAWT
"""
from __future__ import absolute_import

import os
import jsonpickle
from yawt.utils import load_file, abs_state_folder, cfg, single_dict_var,\
    ReprMixin, EqMixin


class Plugin(object):
    """Base YAWT Plugin"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Base implementation of init_app, does nothing"""
        pass


class StateFiles(object):
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
        for base in bases:
            abs_state_file = self.abs_state_file(base)
            if os.path.isfile(abs_state_file):
                stateobj = jsonpickle.decode(load_file(abs_state_file))
                statemap[base] = stateobj
        return statemap

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
