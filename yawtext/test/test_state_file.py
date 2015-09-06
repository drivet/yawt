#pylint: skip-file
import unittest

import jsonpickle

from yawt.utils import save_file
from yawtext import StateFiles


class TestStateFiles(unittest.TestCase):
    def test_statefiles_are_loaded(self):
        save_file('/tmp/statefiles/blog/tagcounts',
                  jsonpickle.encode([1, 2, 3]))
        save_file('/tmp/statefiles/microposts/tagcounts',
                  jsonpickle.encode([4, 5, 6]))
        statefiles = StateFiles('/tmp/statefiles', 'tagcounts')
        statemap = statefiles.load_state_files(['blog', 'microposts'])
        self.assertEquals(2, len(statemap.keys()))
        self.assertEquals(statemap['blog'], [1, 2, 3])
        self.assertEquals(statemap['microposts'], [4, 5, 6])
