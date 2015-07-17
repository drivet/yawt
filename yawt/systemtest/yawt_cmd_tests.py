#pylint: skip-file

import os
import sys

import shutil
import unittest
from mock import patch

import yawt
from yawt import create_app
from yawt.cli import NewSite

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
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_site))

    def test_creates_content_directory(self):
        path_to_content = os.path.join(path_to_site, 'content')
        self.assertFalse(os.path.exists(path_to_content))
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_content))

    def test_creates_draft_directory(self):
        path_to_drafts = os.path.join(path_to_site, 'drafts')
        self.assertFalse(os.path.exists(path_to_drafts))
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_drafts))

    def test_creates_template_directory(self):
        path_to_templates = os.path.join(path_to_site, 'templates')
        self.assertFalse(os.path.exists(path_to_templates))
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(path_to_templates))

    def test_creates_404_template(self):
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'templates/404.html')))

    def test_creates_article_template(self):
        app = create_app(root_dir=path_to_site)
        with app.test_request_context():
            app.preprocess_request()
            newsite = NewSite()
            newsite.run()
        self.assertTrue(os.path.exists(os.path.join(path_to_site, 'templates/article.html')))

    def tearDown(self):
        shutil.rmtree(path_to_site, ignore_errors=True)


def save_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents)


def load_file(filename):
    with open(filename, 'r') as f:
        file_contents = f.read()
    return file_contents
