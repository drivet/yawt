#pylint: skip-file

import unittest
from yawtext.vc import ChangedFiles

class TestChangedFiles(unittest.TestCase):
    def test_normalize_copies_added_modified_and_deleted(self):
        changed = ChangedFiles(added=['file1', 'file2'],
                               modified=['file3', 'file4'],
                               deleted=['file5', 'file6'])
        normalized = changed.normalize()
        self.assertEquals(changed, normalized)
        self.assertTrue(changed.added is not normalized.added)
        self.assertTrue(changed.modified is not normalized.modified)
        self.assertTrue(changed.deleted is not normalized.deleted)

    def test_normalize_moves_renames_into_added_and_deleted(self):
        changed = ChangedFiles(added=['file1', 'file2'],
                               modified=['file3', 'file4'],
                               deleted=['file5', 'file6'],
                               renamed={'file7': 'file8'})
        normalized = changed.normalize()
        self.assertEqual(normalized.added, ['file1', 'file2', 'file8'])
        self.assertEqual(normalized.modified, ['file3', 'file4'])
        self.assertEqual(normalized.deleted, ['file5', 'file6', 'file7'])
        self.assertEqual(normalized.renamed, {})

    def test_filters_non_content_files_from_added_modified_and_deleted(self):
        changed = ChangedFiles(added=['the_content/file1', 'file2'],
                               modified=['file3', 'the_content/file4'],
                               deleted=['the_content/file5', 'file6'])
        contents = changed.content_changes('the_content')
        self.assertEquals(contents.added, ['the_content/file1'])
        self.assertEquals(contents.modified, ['the_content/file4'])
        self.assertEquals(contents.deleted, ['the_content/file5'])

    def test_filters_non_content_renames(self):
        changed = ChangedFiles(renamed={'file1': 'the_content/file2',
                                        'the_content/file3':'the_content/file4',
                                        'file4': 'file6'})
        contents = changed.content_changes('the_content')
        self.assertEquals(contents.added, ['the_content/file2'])
        self.assertEquals(contents.modified, [])
        self.assertEquals(contents.deleted, [])
        self.assertEquals(contents.renamed, {'the_content/file3': 'the_content/file4'})

