def _split_category(category):
    (head, rest) = category, ''
    if '/' in category:
        (head, rest) = category.split('/',1)
    return (head, rest)

class HierarchyCount(object):
    def __init__(self):
        self.category = ''
        self.count = 0
        self.children = []

    def count_hierarchy(self, hierarchy):
        self.count += 1
        if hierarchy:
            (head, rest) = _split_category(hierarchy)
            next_node = None
            for c in self.children:
                if c.category == head:
                    next_node = c
            if next_node is None:
                next_node = HierarchyCount()
                next_node.category = head
                self.children.append(next_node)
            next_node.count_hierarchy(rest)

    def remove_hierarchy(self, hierarchy):
        self.count -= 1
        if hierarchy:
            (head, rest) = _split_category(hierarchy)
            for c in self.children:
                if c.category == head:
                    c.remove_category(rest)
                    break
            self.children = [c for c in self.children if c.count > 0]

    def sort_children(self, reverse=False):
        if len(self.children) > 0:
            for child in self.children:
                child.sort_children()
            self.children.sort(key=lambda c: c.category, reverse=reverse)
            
