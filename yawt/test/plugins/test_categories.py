import unittest
from yawt.plugins.categories import CategoryTree, CategoryNode

class TestCategoryTree(unittest.TestCase): 
    def test_initial(self):
        tree = CategoryTree()
        assert tree.root.count == 0
        assert tree.root.category == ''
        assert len(tree.root.subcategories.keys()) == 0
    
    def test_add_item_to_empty(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        assert tree.root.count == 1
        assert len(tree.root.subcategories.keys()) == 1
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        assert cooking_node.count == 1
        assert cooking_node.category == 'cooking'
        assert len(cooking_node.subcategories.keys()) == 1
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        assert indian_node.count == 1
        assert indian_node.category == 'indian'
        assert len(indian_node.subcategories.keys()) == 0
        
    def test_add_items_with_same_category(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/indian')
        
        assert tree.root.count == 2
        assert len(tree.root.subcategories.keys()) == 1
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        assert cooking_node.count == 2
        assert cooking_node.category == 'cooking'
        assert len(cooking_node.subcategories.keys()) == 1
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        assert indian_node.count == 2
        assert indian_node.category == 'indian'
        assert len(indian_node.subcategories.keys()) == 0
        
    def test_add_items_with_partially_same_categories(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/asian')
        
        assert tree.root.count == 2
        assert len(tree.root.subcategories.keys()) == 1
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        assert cooking_node.count == 2
        assert cooking_node.category == 'cooking'
        assert len(cooking_node.subcategories.keys()) == 2
        assert 'indian' in cooking_node.subcategories
        assert 'asian' in cooking_node.subcategories
        
        indian_node = cooking_node.subcategories['indian']
        assert indian_node.count == 1
        assert indian_node.category == 'indian'
        assert len(indian_node.subcategories.keys()) == 0

        asian_node = cooking_node.subcategories['asian']
        assert asian_node.count == 1
        assert asian_node.category == 'asian'
        assert len(asian_node.subcategories.keys()) == 0
        
    def test_del_item(self):
        indian_node = CategoryNode()
        indian_node.count = 1
        indian_node.category = 'indian'
        
        asian_node = CategoryNode()
        asian_node.count = 1
        asian_node.category = 'asian'
        
        cooking_node = CategoryNode()
        cooking_node.count = 2
        cooking_node.category = 'cooking'
        cooking_node.subcategories = {'indian': indian_node, 'asian': asian_node}
        
        root_node = CategoryNode()
        root_node.count = 2
        root_node.category = ''
        root_node.subcategories = {'cooking': cooking_node}
        
        tree = CategoryTree()
        tree.root = root_node
        
        tree.del_item('cooking/asian')

        print tree.root.subcategories

        assert tree.root.count == 1
        assert len(tree.root.subcategories.keys()) == 1
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        assert cooking_node.count == 1
        assert cooking_node.category == 'cooking'
        assert len(cooking_node.subcategories.keys()) == 1
        assert 'indian' in cooking_node.subcategories
           
    def test_get_dict(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/asian')
        d = tree.get_dict()
        assert d['count'] == 2
        assert len(d['subcategories'].keys()) == 1        
        assert 'cooking' in d['subcategories']
        cooking_node = d['subcategories']['cooking']
        assert cooking_node['count'] == 2
        assert cooking_node['category'] == 'cooking'
        assert len(cooking_node['subcategories'].keys()) == 2
        assert 'indian' in cooking_node['subcategories']
        assert 'asian' in cooking_node['subcategories']
        
        indian_node = cooking_node['subcategories']['indian']
        assert indian_node['count'] == 1
        assert indian_node['category'] == 'indian'
        assert len(indian_node['subcategories'].keys()) == 0

        asian_node = cooking_node['subcategories']['asian']
        assert asian_node['count'] == 1
        assert asian_node['category'] == 'asian'
        assert len(asian_node['subcategories'].keys()) == 0
        
    def test_from_dict(self):
        indian_node = {'count': 1, 'category': 'indian', 'subcategories': {}}
        asian_node = {'count': 1, 'category': 'asian', 'subcategories': {}}
        cooking_node = {'count': 2,
                        'category': 'cooking',
                        'subcategories': {'indian': indian_node,
                                         'asian': asian_node}}
        root = {'count': 2,
                'category': '',
                'subcategories' : { 'cooking': cooking_node }}

        tree = CategoryTree.from_dict(root)

        assert tree.root.count == 2
        assert len(tree.root.subcategories.keys()) == 1
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        assert cooking_node.count == 2
        assert cooking_node.category == 'cooking'
        assert len(cooking_node.subcategories.keys()) == 2
        assert 'indian' in cooking_node.subcategories
        assert 'asian' in cooking_node.subcategories
        
        indian_node = cooking_node.subcategories['indian']
        assert indian_node.count == 1
        assert indian_node.category == 'indian'
        assert len(indian_node.subcategories.keys()) == 0

        asian_node = cooking_node.subcategories['asian']
        assert asian_node.count == 1
        assert asian_node.category == 'asian'
        assert len(asian_node.subcategories.keys()) == 0
