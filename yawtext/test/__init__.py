#pylint: skip-file
import os
import shutil
import subprocess

from flask import current_app
from whoosh.fields import KEYWORD, DATETIME, IDLIST

import yawt
from yawt.article import Article, ArticleInfo
from yawt.test import BaseTestSite, TestCaseWithSite
from yawt.utils import fullname, base_and_ext
from yawt.cli import Walk
from yawtext.git import _git_cmd
from yawtext.indexer import init_index, add_article, commit


class TempGitFolder(BaseTestSite):
    def initialize_git(self):
        cmd = _git_cmd(['init'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = _git_cmd(['add', '-A'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = _git_cmd(['config', 'user.email', 'user@example.com'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = _git_cmd(['config', 'user.name', 'Dude User'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = _git_cmd(['commit', '-m', 'initialcommit'])
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

#    def save_file(self, repofile, contents, gitadd=False):
#        super(TempGitFolder, self).save_file(repofile, contents)
#        if gitadd:
#            _git_cmd(['add', '-A'])

#    def delete_file(self, repofile, gitadd=False):
#        super(TempGitFolder, self).delete_file(repofile)
#        if gitadd:
#            _git_cmd(['add', '-A'])


class TestCaseWithWalker(TestCaseWithSite):
    """TestCase which will run preprocess_request and a walk before
    every test. This can be turned off"""
    walkOnSetup = True

    def create_app(self):
        self.site = BaseTestSite(files=self.files, folders=self.folders)
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        super(TestCaseWithWalker, self).setUp()
        self.app.preprocess_request()
        if self.walkOnSetup:
            self._walk()

    def _walk(self):
        with self.app.app_context():
            walk = Walk()
            walk.run()


class TestCaseWithIndex(TestCaseWithWalker):
    """TestCase which has appropriate default config for a test that needs the
    index.  The tearDown will remove the index if there.  Index is created by
    performing a walk"""
    YAWT_META_TYPES = {'tags': 'list',
                       'create_time': 'iso8601',
                       'modified_time': 'iso8601'}
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.collections.YawtCollections']
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'tags': KEYWORD(),
                                       'categories': IDLIST(),
                                       'create_time': DATETIME(sortable=True)}
    YAWT_COLLECTIONS_SORT_FIELD = 'create_time'

    def tearDown(self):
        super(TestCaseWithIndex, self).tearDown()
        if os.path.exists(self.app.config['WHOOSH_INDEX_ROOT']):
            shutil.rmtree(self.app.config['WHOOSH_INDEX_ROOT'])
