"""Common routines for counting hierarchical items.

You pass in struings like 'blah/foo/stuff' and we'll keep track of a tree of
counts for each element in the path.
"""


def _split_category(category):
    (head, rest) = category, ''
    if '/' in category:
        (head, rest) = category.split('/', 1)
    return (head, rest)


class HierarchyCount(object):
    """Class which can process paths to count a 'hierarchy'.  You pass in
    something like blah/foo.bar and we will count at each level.
    """
    def __init__(self):
        self.category = ''
        self.count = 0
        self.children = []

    def count_hierarchy(self, hierarchy):
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
            next_node.count_hierarchy(rest)

    def remove_hierarchy(self, hierarchy):
        """Pass in something like 'blah/foo/hello' and we'll keep track of a
        tree where each node of the tree is an element in the hierarchy,
        keeping track of the counts below it."""
        self.count -= 1
        if hierarchy:
            (head, rest) = _split_category(hierarchy)
            for child in self.children:
                if child.category == head:
                    child.remove_hierarchy(rest)
                    break
            self.children = [child for child in self.children
                             if child.count > 0]

    def sort_children(self, reverse=False):
        """Recursively sort the children of this tree"""
        if len(self.children) > 0:
            for child in self.children:
                child.sort_children(reverse)
            self.children.sort(key=lambda c: c.category, reverse=reverse)
