import unittest

from mock import call, patch, ANY
from yawt.repository import Repository, RepoException
from yawt.fileutils import isfile, isdir, load_string
from yawt.test.utils import FakeOs

class TestRepository(unittest.TestCase):
    def setUp(self):
        self.fake_os = FakeOs('yawt.fileutils')
        self.fake_os.start()
        self.patch_repo_impl()
        
    def tearDown(self):
        self.fake_os.stop()
        self.unpatch_repo_impl()
        
    def test_initialize_creates_repo_at_root_directory(self):
        repo = Repository('/blogroot')
        repo.initialize(repotype="hg")
        self.get_repo_impl.init.assert_called_once_with('/blogroot')

    def test_initialize_adds_and_commits_files_after_repo_creation(self):
        repo = Repository('/blogroot')
        repo.initialize(repotype="hg", files={'file1': 'contents1'})
        expected_calls = [call.init('/blogroot'),
                          call.add('/blogroot', ['file1']),
                          call.commit('/blogroot','initial commit')]
        self.get_repo_impl.assert_has_calls( expected_calls )
        self.assertTrue( isfile('/blogroot/file1') )
        self.assertEquals( 'contents1', load_string('/blogroot/file1')  )
        
    def test_initialize_creates_directory_when_file_ends_in_slash(self):
        repo = Repository('/blogroot')
        repo.initialize(files={'dir1/': None})
        self.assertTrue( isdir('/blogroot/dir1') )

    def test_initialize_fails_when_blogroot_exists(self):
        self.fake_os.os.mkdir("/blogroot")
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.initialize, files={'file1': 'contents1'})

    def test_initialize_fails_when_repo_init_fails(self):
        self.get_repo_impl.init.side_effect = RepoException
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.initialize, files={'file1': 'contents1'})
         
    def test_initialize_fails_when_repo_add_fails(self):
        self.get_repo_impl.add.side_effect = RepoException
        repo = Repository('/blogroot') 
        self.assertRaises( RepoException, repo.initialize, files={'file1': 'contents1'})

    def test_initialize_fails_when_repo_commit_fails(self):
        self.get_repo_impl.commit.side_effect = RepoException
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.initialize, files={'file1': 'contents1'})
    
    def test_commit_contents_adds_and_commits_files(self):
        repo = Repository('/blogroot')
        repo.commit_contents(files={'file1': 'contents1'})
        expected_calls = [call.add('/blogroot', ['file1']),
                          call.commit('/blogroot','initial commit')]
        self.detect_repo_impl.assert_has_calls( expected_calls )
        self.assertTrue( isfile('/blogroot/file1') )
        self.assertEquals( 'contents1', load_string('/blogroot/file1')  )
    
    def test_commit_contents_fails_when_repo_type_unknown(self):
        self.detect_repo_func.side_effect = RepoException
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.commit_contents, files={'file1': 'contents1'})

    def test_commit_contents_fails_when_repo_add_fails(self):
        self.detect_repo_impl.add.side_effect = RepoException
        repo = Repository('/blogroot') 
        self.assertRaises( RepoException, repo.commit_contents, files={'file1': 'contents1'})
  
    def test_commit_contents_fails_when_repo_commit_fails(self):
        self.detect_repo_impl.commit.side_effect = RepoException
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.commit_contents, files={'file1': 'contents1'})
 
    def test_save_commits_changes_in_repo(self):
        repo = Repository('/blogroot')
        repo.save("awesome message")
        expected_calls = [call.commit('/blogroot','awesome message')]
        self.detect_repo_impl.assert_has_calls( expected_calls )
 
    def test_save_fails_when_commit_fails(self):
        self.detect_repo_impl.commit.side_effect = RepoException
        repo = Repository('/blogroot')
        self.assertRaises( RepoException, repo.save, "blahblah")

    def test_move_commits_after_move_in_repo(self):
        repo = Repository('/blogroot')
        repo.move("some_draft", "blah/somepost", "move message")
        expected_calls = [call.move("/blogroot", "some_draft", "blah/somepost"), 
                          call.commit("/blogroot", "move message")]
        self.detect_repo_impl.assert_has_calls( expected_calls )

    def patch_repo_impl(self):
        self.get_repo_patcher = patch('yawt.repository.get_repo_impl')
        self.get_repo_func = self.get_repo_patcher.start()
        self.get_repo_impl = self.get_repo_func.return_value
 
        self.detect_repo_patcher = patch('yawt.repository.detect_repo_impl')
        self.detect_repo_func = self.detect_repo_patcher.start()
        self.detect_repo_impl = self.detect_repo_func.return_value

    def unpatch_repo_impl(self):
        self.get_repo_impl.stop()
        self.detect_repo_impl.stop()
