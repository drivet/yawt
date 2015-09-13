from flask.ext.testing import TestCase
from yawt.test import TempFolder
from yawt import create_app
from yawt.utils import call_plugins
from yawtext.vc import ChangedFiles
import yawtext.autodates
import datetime

HAMLET = """---
---
to be or not to be
"""

MADRAS = """---
create_time: 2007-06-01 10:10:10
---
spicy
"""

SOUP = """---
create_time: 2008-06-03 10:10:10
---
yummy
"""

SPAGHETTI = """---
---
mamma mia!
"""

class TestFolder(TempFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'content/reading/hamlet.txt': HAMLET,
            'content/cooking/indian/madras.txt': MADRAS,
            'content/cooking/soup.txt': SOUP,
        }


class TestAutodates(TestCase):
    YAWT_EXTENSIONS = ['yawtext.autodates.YawtAutodates']

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def setUp(self):
        self.old_now = yawtext.autodates._now
        yawtext.autodates._now = lambda: datetime.datetime(2015, 9, 13)

    def test_autodates_adjusts_dates(self):
        self.site.save_file('content/cooking/italian/spaghetti.txt', SPAGHETTI)
        changed = ChangedFiles(added=['content/cooking/italian/spaghetti.txt'],
                               modified=['content/reading/hamlet.txt'])
        call_plugins('on_pre_sync', changed)

        self.assertIn('create_time: 2015-09-13',
                      self.site.load_file('content/cooking/italian/spaghetti.txt'))
        self.assertIn('modified_time: 2015-09-13',
                      self.site.load_file('content/cooking/italian/spaghetti.txt'))

        self.assertIn('create_time: 2015-09-13',
                      self.site.load_file('content/reading/hamlet.txt'))
        self.assertIn('modified_time: 2015-09-13',
                      self.site.load_file('content/reading/hamlet.txt'))


    def test_autodates_uses_existing_create_time(self):
        changed = ChangedFiles(modified=['content/cooking/indian/madras.txt'])
        call_plugins('on_pre_sync', changed)

        self.assertIn('create_time: 2007-06-01',
                      self.site.load_file('content/cooking/indian/madras.txt'))
        self.assertIn('modified_time: 2015-09-13',
                      self.site.load_file('content/cooking/indian/madras.txt'))


    def tearDown(self):
        yawtext.autodates._now = self.old_now
        self.site.remove()
