import unittest
import shutil
import subprocess
import os
import sys
import yaml
import yawt
from yawt.cli import NewBlog, NewPost, Save, Publish
from yawt.fileutils import exists, join, isdir, isfile, save_string, ensure_path
from yawt.repository import HgRepo, GitRepo

from mock import patch, Mock

def initialize(repoimpl, rootdir, files=None):
    repoimpl.init(rootdir)

    if files is not None:
        for f in files:
            path_to_file = join(rootdir, f)
            if path_to_file.endswith('/'):
                ensure_path(path_to_file)
            else:
                save_string(path_to_file, files[f])
            
        repoimpl.add(rootdir, files.keys())
        repoimpl.commit(rootdir, "initial commit")

def _run_command_line_option_test(method_to_patch, argv, **expected_run_args):
    with patch(method_to_patch) as run_mock:  
        retval = 0
        sys.argv = argv
        manager = yawt.cli.create_manager()
        try:
            manager.run()
        except SystemExit as sysexit:
            retval = sysexit.code
        if expected_run_args:
            run_mock.assert_called_once_with(**expected_run_args)
        return retval

class TestCommands(unittest.TestCase):
    def get_path_to_blog(self):
        return "/tmp/testblog"

    def assert_file_in_last_hg_commit(self, message, blogroot, filename):
        try:
            (node, desc, files) = self.get_hg_commit_data(blogroot)           
        except subprocess.CalledProcessError:
            self.fail("checking for hg commit failed")
        self.assertTrue(node)
        self.assertEquals(message, desc)
        self.assertIn(filename, files.split())
            
    def get_hg_commit_data(self, blogroot):
        template = "{node}|{desc}|{files}"
        data = subprocess.check_output(["hg", "--cwd", blogroot, "parent", 
                                        "--template", template]) 
        tokens = data.split("|")
        return (tokens[0], tokens[1], tokens[2])

    def assert_file_in_last_git_commit(self, message, blogroot, filename):
        cwd = os.getcwd()
        os.chdir(blogroot)
        try:
            data = subprocess.check_output(["git", "show", "--name-status"])
        except subprocess.CalledProcessError:
            self.fail("checking for git commit failed")
        finally:
            os.chdir(cwd)

        self.assertRegexpMatches(data, "^commit (.*)") 
        self.assertRegexpMatches(data, message)
        self.assertRegexpMatches(data, r"A|M\t" + filename)

    def tearDown(self):
        shutil.rmtree(self.get_path_to_blog(), ignore_errors=True)
        #pass

class TestNewblogCommand(TestCommands):
    def test_creates_blog_directory(self):
        blogroot = self.get_path_to_blog()
        self.assertFalse(exists(blogroot))
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run()
        self.assertTrue(exists(blogroot))

    def test_creates_hg_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="hg")
        self.assertTrue(isdir(join(blogroot, '.hg')))

    def test_creates_git_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="git")
        self.assertTrue(isdir(join(blogroot, '.git')))
   
    def test_commits_config_file_to_hg_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="hg")
        self.assertTrue(isfile(join(blogroot, 'config.yaml')))
        self.assert_file_in_last_hg_commit("initial commit", blogroot, 'config.yaml')

    def test_commits_config_file_to_git_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="git")
        self.assertTrue(isfile(join(blogroot, 'config.yaml')))
        self.assert_file_in_last_git_commit("initial commit", blogroot, 'config.yaml')

    def test_creates_content_directory(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run()
        self.assertTrue(isdir(join(blogroot, 'content')))

    def test_creates_draft_directory(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run()
        self.assertTrue(isdir(join(blogroot, 'drafts')))
        
    def test_commits_404_template_to_hg_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="hg")
        self.assertTrue(isfile(join(blogroot, 'templates/404.html')))
        self.assert_file_in_last_hg_commit("initial commit", blogroot, 'templates/404.html')

    def test_commits_404_template_to_git_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="git")
        self.assertTrue(isfile(join(blogroot, 'templates/404.html')))
        self.assert_file_in_last_git_commit("initial commit", blogroot, 'templates/404.html')

    def test_commits_article_template_to_hg_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="hg")
        self.assertTrue(isfile(join(blogroot, 'templates/article.html')))
        self.assert_file_in_last_hg_commit("initial commit", blogroot, 'templates/article.html')

    def test_commits_article_template_to_git_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog() 
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="git")
        self.assertTrue(isfile(join(blogroot, 'templates/article.html')))
        self.assert_file_in_last_git_commit("initial commit", blogroot, 'templates/article.html')

    def test_commits_article_list_template_to_hg_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="hg")
        self.assertTrue(isfile(join(blogroot, 'templates/article_list.html')))
        self.assert_file_in_last_hg_commit("initial commit", blogroot, 'templates/article_list.html')
 
    def test_commits_article_list_template_to_git_repo(self):
        blogroot = self.get_path_to_blog()
        newblog = NewBlog()
        newblog.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog()})
        newblog.run(repotype="git")
        self.assertTrue(isfile(join(blogroot, 'templates/article_list.html')))
        self.assert_file_in_last_git_commit("initial commit", blogroot, 'templates/article_list.html')


class TestNewpostCommand(TestCommands):
    def test_new_post_committed_to_hg_repo_in_drafts(self):
        initialize(HgRepo(), self.get_path_to_blog())
        newpost = NewPost()
        newpost.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                               yawt.YAWT_EXT: 'blog', 
                               yawt.YAWT_PATH_TO_DRAFTS: 'drafts'})
        newpost.run("a_new_post")
        self.assert_file_in_last_hg_commit("initial commit", self.get_path_to_blog(), 'drafts/a_new_post.blog')
 
    def test_new_post_committed_to_git_repo_in_drafts(self):
        initialize(GitRepo(), self.get_path_to_blog())
        newpost = NewPost()
        newpost.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                               yawt.YAWT_EXT: 'blog', 
                               yawt.YAWT_PATH_TO_DRAFTS: 'drafts'})
        newpost.run("a_new_post")
        self.assert_file_in_last_git_commit("initial commit", self.get_path_to_blog(), 'drafts/a_new_post.blog')
        
class TestSaveCommand(TestCommands):
    def test_save_committed_to_hg_repo(self):
        initialize(HgRepo(), self.get_path_to_blog(), files={"contents/post.txt": "contents1\n"})
        with open(self.get_path_to_blog() + "/contents/post.txt", "a") as f:
            f.write("more stuff")
        save = Save()
        save.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                            yawt.YAWT_EXT: 'blog', 
                            yawt.YAWT_PATH_TO_DRAFTS: 'drafts',
                            yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        save.run("awesome commit")
        self.assert_file_in_last_hg_commit("awesome commit", self.get_path_to_blog(), 'contents/post.txt')
        with open(self.get_path_to_blog() + "/contents/post.txt", "r") as f:
            contents = f.read()
        self.assertEquals("contents1\nmore stuff", contents)

    def test_save_committed_to_git_repo(self):
        initialize(GitRepo(), self.get_path_to_blog(), files={"contents/post.txt": "contents1\n"})
        with open(self.get_path_to_blog() + "/contents/post.txt", "a") as f:
            f.write("more stuff")
        save = Save()
        save.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                            yawt.YAWT_EXT: 'blog', 
                            yawt.YAWT_PATH_TO_DRAFTS: 'drafts',
                            yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        save.run("awesome commit")
        self.assert_file_in_last_git_commit("awesome commit", self.get_path_to_blog(), 'contents/post.txt')
        with open(self.get_path_to_blog() + "/contents/post.txt", "r") as f:
            contents = f.read()
        self.assertEquals("contents1\nmore stuff", contents)

class TestPublishCommand(TestCommands):
    def test_publish_creates_new_move_commit_with_draft_to_post_in_hg_repo(self):
        initialize(HgRepo(), self.get_path_to_blog(), files={"drafts/draftpost.blog": "contents1\n",
                                                                  "contents/": None})
        publish = Publish()
        publish.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                               yawt.YAWT_EXT: 'blog', 
                               yawt.YAWT_PATH_TO_DRAFTS: 'drafts', 
                               yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        publish.run("draftpost", "blah/newpost")
        self.assert_file_in_last_hg_commit("published blah/newpost", 
                                           self.get_path_to_blog(), 
                                           "contents/blah/newpost.blog")

    def test_publish_creates_new_move_commit_with_draft_to_post_in_git_repo(self):
        initialize(GitRepo(), self.get_path_to_blog(), files={"drafts/draftpost.blog": "contents1\n",
                                                            "contents/": None } )
        publish = Publish()
        publish.app = FakeApp({yawt.YAWT_BLOGPATH: self.get_path_to_blog(),
                               yawt.YAWT_EXT: 'blog', 
                               yawt.YAWT_PATH_TO_DRAFTS: 'drafts', 
                               yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        publish.run("draftpost", "blah/newpost")
        self.assert_file_in_last_git_commit("published blah/newpost", 
                                           self.get_path_to_blog(), 
                                           "contents/blah/newpost.blog")

class TestYawtInfoCommandLineArguments(TestCommands):
    def setUp(self):
        initialize(HgRepo(), self.get_path_to_blog(), 
                        files={"config.yaml": yaml.dump(yawt.default_config),
                               "drafts/draftpost.blog": "contents1\n",
                               "contents/": None})
        self.saved_argv = sys.argv

    def test_item_command_line_option_maps_to_info_cmd(self):
        retval =_run_command_line_option_test("yawt.cli.Info.run",
                                              ['yawt', 'info', '-b', self.get_path_to_blog(), 'YAWT_PATH_TO_ARTICLES'],
                                              item='YAWT_PATH_TO_ARTICLES')
        self.assertEquals(0, retval)

    def tearDown(self):
        super(TestYawtInfoCommandLineArguments, self).tearDown()
        sys.argv = self.saved_argv

class TestNewBlogCommandLineArguments(TestCommands):
    def setUp(self):
        self.saved_argv = sys.argv

    def test_repotype_git_command_line_option_maps_to_git_run_parameter(self):
        retval = _run_command_line_option_test("yawt.cli.NewBlog.run",
                                               self._newblog_command_line(['--repotype', 'git']), 
                                               repotype="git" )
        self.assertEquals(0, retval)

    def test_r_git_command_line_option_maps_to_git_run_parameter(self):
        retval = _run_command_line_option_test("yawt.cli.NewBlog.run",
                                               self._newblog_command_line(['-r', 'git']),
                                               repotype="git" )
        self.assertEquals(0, retval)

    def test_repotype_hg_command_line_option_maps_to_hg_run_parameter(self):
        retval =  _run_command_line_option_test("yawt.cli.NewBlog.run",
                                                self._newblog_command_line(['--repotype', 'hg']),
                                                repotype="hg" )
        self.assertEquals(0, retval)

    def test_r_hg_command_line_option_maps_to_hg_run_parameter(self):
        retval = _run_command_line_option_test("yawt.cli.NewBlog.run", 
                                               self._newblog_command_line(['-r', 'hg']),
                                               repotype="hg" )
        self.assertEquals(0, retval)

    def test_no_repotype_command_line_argument_maps_to_hg_run_parameter(self):
        retval = _run_command_line_option_test("yawt.cli.NewBlog.run", 
                                               self._newblog_command_line([]),
                                               repotype="hg" )
        self.assertEquals(0, retval)

    def _newblog_command_line(self, args):
        return ['yawt', 'newblog', '-b', self.get_path_to_blog()] + args

    def tearDown(self):
        super(TestNewBlogCommandLineArguments, self).tearDown()
        sys.argv = self.saved_argv

class TestNewPostCommandLineArguments(TestCommands):
    def setUp(self):  
        initialize(HgRepo(), self.get_path_to_blog(), 
                   files={"config.yaml": yaml.dump(yawt.default_config),
                          "contents/": None})
        self.saved_argv = sys.argv

    def test_postname_command_line_arg_is_passed_to_newpost_cmd(self):
        retval = _run_command_line_option_test("yawt.cli.NewPost.run",
                                      ['yawt', 'newpost', '-b', self.get_path_to_blog(), "a_new_post"],
                                      postname="a_new_post")
        self.assertEquals(0, retval)

    def tearDown(self):
        super(TestNewPostCommandLineArguments, self).tearDown()
        sys.argv = self.saved_argv

class TestSaveCommandLineArguments(TestCommands):
    def setUp(self):  
        initialize(HgRepo(), self.get_path_to_blog(), 
                   files={"config.yaml": yaml.dump(yawt.default_config)})
        self.saved_argv = sys.argv
  
    def test_message_command_line_arg_is_passed_to_save_cmd(self):
        retval = _run_command_line_option_test("yawt.cli.Save.run",
                                               ['yawt', 'save', '-b', self.get_path_to_blog(), "-m", "awesome message"],
                                               message="awesome message")
        self.assertEquals(0, retval)

    def test_message_command_line_arg_is_optional(self):
        retval = _run_command_line_option_test("yawt.cli.Save.run",
                                               ['yawt', 'save', '-b', self.get_path_to_blog()],
                                               message=None)
        self.assertEquals(0, retval)

    def tearDown(self):
        super(TestSaveCommandLineArguments, self).tearDown()
        sys.argv = self.saved_argv

class TestPublishCommandLineArguments(TestCommands):
    def setUp(self):  
        initialize(HgRepo(), self.get_path_to_blog(), 
                   files={"config.yaml": yaml.dump(yawt.default_config)})
        self.saved_argv = sys.argv
  
    def test_draftname_and_postname_command_line_args_are_passed_to_publish_cmd(self):
        retval = _run_command_line_option_test("yawt.cli.Publish.run",
                                               ['yawt', 'publish', '-b', self.get_path_to_blog(), "the_draft", "the_post"],
                                               draftname="the_draft", postname="the_post")
        self.assertEquals(0, retval)

    def test_one_command_line_arg_fails(self):
        retval = _run_command_line_option_test("yawt.cli.Publish.run",
                                               ['yawt', 'publish', '-b', self.get_path_to_blog(), "the_draft"])
        self.assertNotEquals(0, retval)

    def test_no_command_line_args_fails(self):
        retval = _run_command_line_option_test("yawt.cli.Publish.run",
                                               ['yawt', 'publish', '-b', self.get_path_to_blog()])
        self.assertNotEquals(0, retval)

    def tearDown(self):
        super(TestPublishCommandLineArguments, self).tearDown()
        sys.argv = self.saved_argv

class FakeApp:
    def __init__(self, config):
        self.config = config
