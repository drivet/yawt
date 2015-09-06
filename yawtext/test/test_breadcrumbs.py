#pylint: skip-file
import unittest

from yawtext.breadcrumbs import YawtBreadcrumbs, _breadcrumbs


class TestYawtBreadcrumbs(unittest.TestCase):
    def setUp(self):
        self.plugin = YawtBreadcrumbs()

    def test_breadcrumbs_breakup_path(self):
        bc = _breadcrumbs('/blog/path1/path2')
        self.assertEquals(3, len(bc))
        self.assertEquals('blog', bc[0]['crumb'])
        self.assertEquals('path1', bc[1]['crumb'])
        self.assertEquals('path2', bc[2]['crumb'])

        self.assertEquals('/blog', bc[0]['url'])
        self.assertEquals('/blog/path1', bc[1]['url'])
        self.assertEquals('/blog/path1/path2', bc[2]['url'])
