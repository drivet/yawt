#pylint: skip-file

import unittest
import datetime
import shutil
import os
from yawtext.git import YawtGit
from repoutils import TempRepo
from yawt.article import Article, ArticleInfo
from yawt import create_app
from flask import g

class TestYawtGitNewSite(unittest.TestCase):
    def setUp(self): 
        self.root_dir = '/tmp/blah'
        self.plugin = YawtGit()
        self.app = create_app(self.root_dir, extension_info = extension_info(self.plugin))
        self.app.config['GIT_REPOPATH'] = self.root_dir
        self.app.config['GIT_SEARCH_PATH'] = self.root_dir

    def test_git_saves_ignore_file(self): 
        self.assertFalse(os.path.isfile(os.path.join(self.root_dir, '.gitignore')))
        with self.app.test_request_context():
            self.app.preprocess_request()
            g.site.new_site()
        self.assertTrue(os.path.isfile(os.path.join(self.root_dir, '.gitignore')))

    def tearDown(self):
        shutil.rmtree(self.root_dir)


def setup_repo():
    tr = TempRepo()
    tr.init()
    tr.copy_contents('content/hello.md', 'stuff')
    tr.commit("first commit", 100, author="Daffy Duck")
    tr.copy_contents('content/hello.md', 'more stuff')
    tr.commit("second commit", 200, author="Porky Pig")
    tr.copy_contents('content/bar.md', 'foo')
    tr.commit("third commit", 300, author="Roger Rabbit")
    return tr

def extension_info(plugin):
    from flask_git import Git
    git = Git()
    return ({'flask_git.Git': git, 'yawtext.git.YawtGit': plugin}, 
            [git, plugin])

