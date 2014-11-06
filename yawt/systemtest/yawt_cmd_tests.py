import os
import sys

import shutil
import unittest
from mock import patch

import yawt
from yawt import create_app
from yawt.cli2 import NewSite, CreateOrUpdateDraft, \
    CreateOrUpdateArticle, Move, Delete, Publish


path_to_site = "/tmp/testsite"

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


class TestNewsiteCommand(unittest.TestCase):
    """NewSite command tests"""

    def test_creates_site_directory(self):
        self.assertFalse(os.path.exists(path_to_site))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_site))

    def test_creates_content_directory(self):
        path_to_content = os.path.join(path_to_site, 'content')
        self.assertFalse(os.path.exists(path_to_content))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_content))

    def test_creates_draft_directory(self):
        path_to_drafts = os.path.join(path_to_site, 'drafts')
        self.assertFalse(os.path.exists(path_to_drafts))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_drafts))
 
    def test_creates_template_directory(self):
        path_to_templates = os.path.join(path_to_site, 'templates')
        self.assertFalse(os.path.exists(path_to_templates))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_templates))

    def test_creates_404_template(self):
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'templates/404.html')))

    def test_creates_article_template(self):
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'templates/article.html')))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestCreateOrUpdateDraft(unittest.TestCase):
    """CreateOrUpdateDraft command tests"""
    
    def test_saves_new_draft(self): 
        app = create_app(root_dir = path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            NewSite().run()
            cmd = CreateOrUpdateDraft()
            cmd.run('blah')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        
    def test_updates_draft(self):
        os.makedirs(os.path.join(path_to_site, 'drafts'))
        app = create_app(root_dir = path_to_site)

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = CreateOrUpdateDraft()
            cmd.run('blah', content='something here')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        assert 'something here' in load_file(os.path.join(path_to_site, 'drafts', 'blah.txt'))

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = CreateOrUpdateDraft()
            cmd.run('blah', content='something else')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        assert 'something here' not in load_file(os.path.join(path_to_site, 'drafts', 'blah.txt'))
        assert 'something else' in load_file(os.path.join(path_to_site, 'drafts', 'blah.txt'))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestCreateOrUpdateArticle(unittest.TestCase):
    """CreateOrUpdateArticle command tests"""
    
    def test_saves_new_article(self): 
        os.makedirs(os.path.join(path_to_site, 'content'))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            cmd = CreateOrUpdateArticle()
            cmd.run('blah')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        
    def test_updates_article(self):
        os.makedirs(os.path.join(path_to_site, 'content'))
        app = create_app(root_dir = path_to_site)

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = CreateOrUpdateArticle()
            cmd.run('blah', content='something here')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        assert 'something here' in load_file(os.path.join(path_to_site, 'content', 'blah.txt'))

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = CreateOrUpdateArticle()
            cmd.run('blah', content='something else')
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        assert 'something here' not in load_file(os.path.join(path_to_site, 'content', 'blah.txt'))
        assert 'something else' in load_file(os.path.join(path_to_site, 'content', 'blah.txt'))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestMove(unittest.TestCase):
    """Move command tests"""

    def test_move_article(self):
        os.makedirs(os.path.join(path_to_site, 'content'))
        app = create_app(root_dir = path_to_site)

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = CreateOrUpdateArticle()
            cmd.run('blah', content='something here')
    
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'content/foo.txt')))

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = Move()
            cmd.run('blah', 'foo')

        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/foo.txt')))        

    def test_move_draft(self):
        os.makedirs(os.path.join(path_to_site, 'drafts'))
        app = create_app(root_dir = path_to_site)

        with app.test_request_context():
            app.preprocess_request() 
            cmd = CreateOrUpdateDraft()
            cmd.run('blah', content='something here')
    
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'drafts/foo.txt')))

        with app.test_request_context(): 
            app.preprocess_request()
            cmd = Move()
            cmd.run('blah', 'foo', draft=True)

        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/foo.txt')))
        
    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestPublish(unittest.TestCase):
    """Publish command tests"""
     
    def test_publish_draft(self):
        os.makedirs(os.path.join(path_to_site, 'drafts'))
        os.makedirs(os.path.join(path_to_site, 'content'))
        app = create_app(root_dir = path_to_site)

        with app.test_request_context():
            app.preprocess_request()
            cmd = CreateOrUpdateDraft()
            cmd.run('blah', content='something here')
    
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'content/foo.txt')))

        with app.test_request_context():
            app.preprocess_request()
            cmd = Publish()
            cmd.run('blah', 'foo')

        self.assertFalse(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/foo.txt')))
        
    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


class TestDelete(unittest.TestCase):
    """Delete command tests"""

    def test_delete_article(self):
        os.makedirs(os.path.join(path_to_site, 'content'))
        save_file(os.path.join(path_to_site, 'content/blah.txt'), 'stuff here' )
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context(): 
            app.preprocess_request()
            cmd = Delete()
            cmd.run('blah')
            self.assertFalse(os.path.exists(os.path.join(path_to_site, 'content/blah.txt')))

    def test_delete_draft(self):
        os.makedirs(os.path.join(path_to_site, 'drafts'))
        save_file(os.path.join(path_to_site, 'drafts/blah.txt'), 'stuff here' )
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))
        app = create_app(root_dir = path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            cmd = Delete()
            cmd.run('blah', draft=True)
            self.assertFalse(os.path.exists(os.path.join(path_to_site, 'drafts/blah.txt')))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


def save_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents)

def load_file(filename):
    with open(filename, 'r') as f:
        file_contents = f.read()
    return file_contents
