import unittest
import yawt
import yawt.cli
import sys

from mock import patch, Mock, ANY
from yawt.test.utils import FakeOs

from StringIO import StringIO

class TestYawtNewblogCommand(unittest.TestCase):
    def setUp(self):
        self._repo_patcher = patch('yawt.cli.Repository', autospec=True)
        self.repo_class = self._repo_patcher.start()
        self.repo = self.repo_class.return_value
        self.newblogcmd = yawt.cli.NewBlog()

    def test_repo_created_with_root_folder(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.repo_class.assert_called_once_with('/blogroot')

    def test_adds_config_file_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='config.yaml')

    def test_adds_404_template_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='templates/404.html')

    def test_adds_article_template_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='templates/article.html')

    def test_adds_article_list_template_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='templates/article_list.html')
        
    def test_adds_content_folder_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='content/')

    def test_adds_draft_folder_to_repo(self):
        self.newblogcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newblogcmd.run("/blogroot")
        self.verify_initialize_called_with(self.repo, filename='drafts/')

    def verify_initialize_called_with(self, repo, filename=None):
        POSITIONAL_ARGS = 0
        self.assertEquals( 1, repo.initialize.call_count )

        call_args = repo.initialize.call_args
        assert call_args != None

        file_dict_arg = call_args[POSITIONAL_ARGS][1]
        if filename is not None:
            self.assertIn(filename, file_dict_arg.keys())

    def tearDown(self):
        self._repo_patcher.stop()

class TestYawtNewpostCommand(unittest.TestCase):
    def setUp(self):
        self.repo_patcher = patch('yawt.cli.Repository', autospec=True)
        self.repo_class = self.repo_patcher.start()
        self.repo = self.repo_class.return_value

        self.fake_os = FakeOs("yawt.cli")
        self.fake_os.start()
        
        self.newpostcmd = yawt.cli.NewPost()
 
    def test_repo_created_with_blog_root(self):
        self.newpostcmd.app = FakeApp({yawt.YAWT_EXT: 'blog', 
                                       yawt.YAWT_PATH_TO_DRAFTS: 'drafts',
                                       yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newpostcmd.run("randompost")
        self.repo_class.assert_called_once_with('/blogroot')

    def test_new_post_added_to_draft_folder_in_blog_directory(self):
        self.newpostcmd.app = FakeApp({yawt.YAWT_EXT: 'blog', 
                                       yawt.YAWT_PATH_TO_DRAFTS: 'drafts',
                                       yawt.YAWT_BLOGPATH: '/blogroot'})
        self.newpostcmd.run("randompost")
        self.repo.commit_contents.assert_called_once_with({"drafts/randompost.blog":""} )

    def tearDown(self):
        self.repo_patcher.stop()
        self.fake_os.stop()

class TestYawtSaveCommand(unittest.TestCase):
    def setUp(self):
        self.repo_patcher = patch('yawt.cli.Repository', autospec=True)
        self.repo_class = self.repo_patcher.start()
        self.repo = self.repo_class.return_value
       
        self.fake_os = FakeOs("yawt.cli")
        self.fake_os.start()

        self.savecmd = yawt.cli.Save()

    def test_repo_created_with_blog_root(self): 
        self.savecmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'})
        self.savecmd.run("awesome message")
        self.repo_class.assert_called_once_with('/blogroot')
  
    def test_commit_message_supplied_to_repo(self):
        self.savecmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot'}) 
        self.savecmd.run("awesome message")
        self.repo.save.assert_called_once_with("awesome message")


class TestYawtPublishCommand(unittest.TestCase):
    def setUp(self):
        self.repo_patcher = patch('yawt.cli.Repository', autospec=True)
        self.repo_class = self.repo_patcher.start()
        self.repo = self.repo_class.return_value
        self.fake_os = FakeOs("yawt.cli")
        self.fake_os.start()
        
        self.publishcmd = yawt.cli.Publish()

    def test_repo_created_with_blog_root(self):
        self.publishcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot', 
                                       yawt.YAWT_EXT: 'blog',
                                       yawt.YAWT_PATH_TO_DRAFTS: 'drafts', 
                                       yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        self.publishcmd.run("randomdraft", "randompost")
        self.repo_class.assert_called_once_with('/blogroot')
    
    def test_draft_is_repo_moved_to_post(self): 
        self.publishcmd.app = FakeApp({yawt.YAWT_BLOGPATH: '/blogroot', 
                                       yawt.YAWT_EXT: 'blog', 
                                       yawt.YAWT_PATH_TO_DRAFTS: 'drafts', 
                                       yawt.YAWT_PATH_TO_ARTICLES: 'contents'})
        self.publishcmd.run("randomdraft", "blah/randompost")
        self.repo.move.assert_called_once_with("drafts/randomdraft.blog", "contents/blah/randompost.blog", ANY)


class TestYawtInfoCommand(unittest.TestCase):
    def setUp(self):
        self.infocmd = yawt.cli.Info()
        self.saved_stdout = sys.stdout
        self.out = StringIO()
        sys.stdout = self.out

    def test_named_item_is_pulled_from_config(self):
        self.infocmd.app = FakeApp({yawt.YAWT_EXT: 'blog', yawt.YAWT_PATH_TO_DRAFTS: 'drafts'})
        self.infocmd.run(yawt.YAWT_PATH_TO_DRAFTS)
        output = self.out.getvalue().strip()
        self.assertEquals("drafts", output)
 
    def test_message_is_shown_when_item_does_not_exist(self):
        self.infocmd.app = FakeApp({yawt.YAWT_EXT: 'blog', yawt.YAWT_PATH_TO_DRAFTS: 'drafts'})
        self.infocmd.run("yadda")
        output = self.out.getvalue().strip()
        self.assertEquals("no configuration item found at yadda", output)

    def tearDown(self):
        sys.stdout = self.saved_stdout


class TestWalkCommand(unittest.TestCase):
    def setUp(self): 
        self.create_store_patcher = patch('yawt.article.create_store')
        self.create_store = self.create_store_patcher.start()
        self.store = Mock()
        self.create_store.return_value = self.store
        self.walkcmd = yawt.cli.Walk()

    def test_pre_walkers_called(self):
        pass
#        plugin1 = Mock()
#        plugin2 = Mock() 
#        plugins = Mock()
#        plugins.walkers.return_value = [plugin1, plugin2]
#        self.walkcmd.app = FakeAppWithConfigAndPlugins({}, plugins)
#        self.walkcmd.run()
#        self.store.walk_articles.return_value = ["post1", "post2"]
        

#class TestYawtInfoCommandLineArguments(unittest.TestCase):
#    def setUp(self):
#        self.old_argv = sys.argv
#        sys.argv = ['yawt', 'info', 'YAWT_PATH_TO_ARTICLES']

#    def test_item_command_line_option_maps_to_item_run_parameter(self):
#        with patch("yawt.cli.Info.run"):
#            with patch("yawt.create_app") as create_app_patch:
#                app = Mock()
#                app.config = yawt.default_config
#                create_app_patch.return_value = app
#                manager = yawt.cli.create_manager()
#                manager.run()

#    def tearDown(self):
#        sys.argv = self.old_argv


class FakeApp:
    def __init__(self, config):
        self.config = config

class FakeAppWithConfigAndPlugins:
    def __init__(self, config, plugins):
        self.config = config
        self.plugins = plugins
