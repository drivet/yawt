#pylint: skip-file

import unittest
from yawtext import HierarchyCount

class TestHierarchyCounter(unittest.TestCase):
    def test_adding_creates_counting_tree(self):
        hc = HierarchyCount()
        hc.add('cooking/indian')
        hc.add('cooking/italian')
        hc.add('reading/history')
        hc.add('')
        expected = HierarchyCount(category='',
                                  count=4,
                                  children=[HierarchyCount(category='cooking',
                                                           count=2,
                                                           children=[HierarchyCount(category='indian',
                                                                                    count=1),
                                                                     HierarchyCount(category='italian',
                                                                                    count=1)]),
                                            HierarchyCount(category='reading',
                                                           count=1,
                                                           children=[HierarchyCount(category='history',
                                                                                    count=1)])])
        self.assertEquals(expected, hc)

    def test_removing_adjusts_counting_tree(self):
        hc = HierarchyCount()
        hc.add('cooking/indian')
        hc.add('cooking/italian')
        hc.add('reading/history')
        hc.add('')

        hc.remove('cooking/indian')
        expected = HierarchyCount(category='',
                                  count=3,
                                  children=[HierarchyCount(category='cooking',
                                                           count=1,
                                                           children=[HierarchyCount(category='italian',
                                                                                    count=1)]),
                                            HierarchyCount(category='reading',
                                                           count=1,
                                                           children=[HierarchyCount(category='history',
                                                                                    count=1)])])
        self.assertEquals(expected, hc)

    def test_fetches_named_child(self):
        hc = HierarchyCount()
        hc.add('cooking/indian')
        hc.add('cooking/italian')
        hc.add('reading/history')
        hc.add('')
        self.assertEquals('cooking', hc.child('cooking').category)
        self.assertEquals(None, hc.child('astronomy'))

    def test_sort_children(self):
        hc = HierarchyCount()
        hc.add('cooking/indian')
        hc.add('cooking/italian')
        hc.add('reading/history')
        hc.add('')
        hc.sort(reverse=True)
        self.assertEquals('reading', hc.children[0].category)
        self.assertEquals('cooking', hc.children[1].category)
