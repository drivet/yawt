import unittest
import yawt.util
from mock import patch, Mock
from yawt.plugins.categories import CategoryTree, CategoryNode, CategoryCounter, dict2tree, tree2dict
from yawt.test import fake_filesystem

class TestCategoryTree(unittest.TestCase): 
    def test_initial(self):
        tree = CategoryTree()
        self.assertEquals(tree.root.count, 0)
        self.assertEquals(tree.root.category, '')
        self.assertEquals(len(tree.root.subcategories.keys()), 0)
    
    def test_add_item_to_empty(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        self.assertEquals(tree.root.count, 1)
        self.assertEquals(len(tree.root.subcategories.keys()), 1)
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 1)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(cooking_node.url, 'cooking/')
        self.assertEquals(len(cooking_node.subcategories.keys()), 1)
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 1)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(indian_node.url, 'cooking/indian/')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)
        
    def test_add_items_with_same_category(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/indian')
        
        self.assertEquals(tree.root.count, 2)
        self.assertEquals(len(tree.root.subcategories.keys()), 1)
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 2)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(cooking_node.url, 'cooking/')
        self.assertEquals(len(cooking_node.subcategories.keys()), 1)
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 2)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(indian_node.url, 'cooking/indian/')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)
        
    def test_add_items_with_partially_same_categories(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/asian')
        
        self.assertEquals(tree.root.count, 2)
        self.assertEquals(len(tree.root.subcategories.keys()), 1)
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 2)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(cooking_node.url, 'cooking/')
        self.assertEquals(len(cooking_node.subcategories.keys()), 2)
        
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 1)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(indian_node.url, 'cooking/indian/')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)
        
        assert 'asian' in cooking_node.subcategories
        asian_node = cooking_node.subcategories['asian']
        self.assertEquals(asian_node.count, 1)
        self.assertEquals(asian_node.category, 'asian')
        self.assertEquals(asian_node.url, 'cooking/asian/')
        self.assertEquals(len(asian_node.subcategories.keys()), 0)

    def test_add_items_different_categories(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('reviews/movies')
        self.assertEquals(tree.root.count, 2)
        self.assertEquals(len(tree.root.subcategories.keys()), 2)
        
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 1)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(cooking_node.url, 'cooking/')
        self.assertEquals(len(cooking_node.subcategories.keys()), 1)

        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 1)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(indian_node.url, 'cooking/indian/')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)
        
        assert 'reviews' in tree.root.subcategories
        reviews_node = tree.root.subcategories['reviews']
        self.assertEquals(reviews_node.count, 1)
        self.assertEquals(reviews_node.category, 'reviews')
        self.assertEquals(reviews_node.url, 'reviews/')
        self.assertEquals(len(reviews_node.subcategories.keys()), 1)

        assert 'movies' in reviews_node.subcategories
        movies_node = reviews_node.subcategories['movies']
        self.assertEquals(movies_node.count, 1)
        self.assertEquals(movies_node.category, 'movies')
        self.assertEquals(movies_node.url, 'reviews/movies/')
        self.assertEquals(len(movies_node.subcategories.keys()), 0)
        
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
        
        self.assertEquals(tree.root.count, 2)
        
        tree.del_item('cooking/asian')

        self.assertEquals(tree.root.count, 1)
        self.assertEquals(len(tree.root.subcategories.keys()), 1)
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 1)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(len(cooking_node.subcategories.keys()), 1)
        assert 'indian' in cooking_node.subcategories
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 1)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)
        
    def test_get_dict(self):
        tree = CategoryTree()
        tree.add_item('cooking/indian')
        tree.add_item('cooking/asian')
        d = tree2dict(tree.root)
        self.assertEquals(d['count'], 2)
        self.assertEquals(len(d['subcategories'].keys()), 1)
        assert 'cooking' in d['subcategories']
        cooking_node = d['subcategories']['cooking']
        self.assertEquals(cooking_node['count'], 2)
        self.assertEquals(cooking_node['category'], 'cooking')
        self.assertEquals(len(cooking_node['subcategories'].keys()), 2)
        
        assert 'indian' in cooking_node['subcategories']
        indian_node = cooking_node['subcategories']['indian']
        self.assertEquals(indian_node['count'], 1)
        self.assertEquals(indian_node['category'], 'indian')
        self.assertEquals(len(indian_node['subcategories'].keys()), 0)
        
        assert 'asian' in cooking_node['subcategories']
        asian_node = cooking_node['subcategories']['asian']
        self.assertEquals(asian_node['count'], 1)
        self.assertEquals(asian_node['category'], 'asian')
        self.assertEquals(len(asian_node['subcategories'].keys()), 0)
        
    def test_from_dict(self):
        indian_node = {'count': 1, 'category': 'indian', 'subcategories': {}, 'url': '/indian'}
        asian_node = {'count': 1, 'category': 'asian', 'subcategories': {}, 'url': '/asian'}
        cooking_node = {'count': 2,
                        'category': 'cooking',
                        'url': '/cooking',
                        'subcategories': {'indian': indian_node,
                                         'asian': asian_node}}
        root = {'count': 2,
                'category': '',
                'url': '/',
                'subcategories' : { 'cooking': cooking_node }}

        tree = dict2tree(root)

        self.assertEquals(tree.root.count, 2)
        self.assertEquals(len(tree.root.subcategories.keys()), 1)
        assert 'cooking' in tree.root.subcategories
        cooking_node = tree.root.subcategories['cooking']
        self.assertEquals(cooking_node.count, 2)
        self.assertEquals(cooking_node.category, 'cooking')
        self.assertEquals(len(cooking_node.subcategories.keys()), 2)
        assert 'indian' in cooking_node.subcategories
        assert 'asian' in cooking_node.subcategories
        
        indian_node = cooking_node.subcategories['indian']
        self.assertEquals(indian_node.count, 1)
        self.assertEquals(indian_node.category, 'indian')
        self.assertEquals(len(indian_node.subcategories.keys()), 0)

        asian_node = cooking_node.subcategories['asian']
        self.assertEquals(asian_node.count, 1)
        self.assertEquals(asian_node.category, 'asian')
        self.assertEquals(len(asian_node.subcategories.keys()),  0)

class TestCategoryCounter(unittest.TestCase):
    def setUp(self):
        self._patch_os()
        
    def test_counter_starts_at_zero(self):
        category_counter = CategoryCounter('', '/category_dir/category_file')
        category_counter.pre_walk()
        category_counter.post_walk()
        counts = yawt.util.load_yaml('/category_dir/category_file')
        self.assertEquals(counts['category'], '')
        self.assertEquals(counts['count'], 0)
        self.assertEquals(counts['subcategories'], {})
        self.assertEquals(counts['url'], '')

    def test_counter_visit_not_in_base(self):
        category_counter = CategoryCounter('hobbies', '/category_dir/category_file')
        category_counter.pre_walk()
        category_counter.visit_article('cooking/indian/madras')
        category_counter.post_walk()
        counts = yawt.util.load_yaml('/category_dir/category_file')
        self.assertEquals(counts['category'], '')
        self.assertEquals(counts['count'], 0)
        self.assertEquals(counts['subcategories'], {})
        self.assertEquals(counts['url'], '')
        
    def test_counter_visit_in_base(self):
        counter = CategoryCounter('cooking', '/category_dir/category_file')
        counter.pre_walk()
        counter.visit_article('cooking/tools')
        counter.visit_article('cooking/indian/madras')
        counter.visit_article('cooking/indian/vindaloo')
        counter.visit_article('cooking/asian/wonton')
        counter.post_walk()
        counts = yawt.util.load_yaml('/category_dir/category_file')
        
        self.assertEquals(counts['category'], '')
        self.assertEquals(counts['count'], 4)
        self.assertEquals(counts['url'], '')
        self.assertEquals(len(counts['subcategories'].keys()), 3)

        self.assertTrue('indian' in counts['subcategories'])
        indian = counts['subcategories']['indian']
        self.assertEquals(indian['category'], 'indian')
        self.assertEquals(indian['count'], 2)
        self.assertEquals(indian['url'], 'indian/')
        
        self.assertTrue('asian' in counts['subcategories'])
        asian = counts['subcategories']['asian']
        self.assertEquals(asian['category'], 'asian')
        self.assertEquals(asian['count'], 1)
        self.assertEquals(asian['url'], 'asian/')
        
    def _patch_os(self):
        self._fs = fake_filesystem.FakeFilesystem()
        self._os = fake_filesystem.FakeOsModule(self._fs)
        self._os_patcher = patch('yawt.util.os', self._os)
        self._os_path_patcher = patch('yawt.util.os.path',self._os.path)
        self._open_patcher = patch('__builtin__.open', fake_filesystem.FakeFileOpen(self._fs))
        self._os_patcher.start() 
        self._os_path_patcher.start()
        self._open_patcher.start()

    def _unpatch_os(self):
        self._os_patcher.stop()
        self._os_path_patcher.stop()
        self._open_patcher.stop()

    def tearDown(self):
        self._unpatch_os()
        
