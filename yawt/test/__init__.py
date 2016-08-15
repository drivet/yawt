#pylint: skip-file
import os
import shutil
import tempfile

from flask_testing import TestCase

import yawt
from yawt.utils import save_file, remove_file, load_file, ChangedFiles,\
    call_plugins


POST_TEMPLATE = """\
---
{metadata}
---

{content}
"""


# The template for creating YAWT test templates.
# They look like this:
#
# NAME
# {{article}}
#
TEST_TEMPLATE = """\
{name}
{{{{article}}}}
"""


def dump_post(metadata, content):
    return POST_TEMPLATE.format(metadata=metadata, content=content)


def template(name):
    return TEST_TEMPLATE.format(name=name)


# Manages a set of files and folders in the /tmp folder
class BaseTestSite(object):
    def __init__(self, files=None, folders=None):
        self.site_root = None

        # map of filename relative to the root folder to content.  content can
        # be a string, or a tuple where the first is the metadata and the
        # second is the content
        self.files = files or {}

        # folders to create
        self.folders = folders or []

    def initialize(self):
        self.site_root = tempfile.mkdtemp()

        for folder in self.folders:
            os.makedirs(os.path.join(self.site_root, folder))

        for the_file in self.files.keys():
            abs_filename = os.path.join(self.site_root, the_file)
            content = self.files[the_file]
            if isinstance(content, tuple):
                save_file(abs_filename, dump_post(content[0], content[1]))
            else:
                save_file(abs_filename, content)

    def save_file(self, repofile, contents):
        save_file(os.path.join(self.site_root, repofile), contents)

    def delete_file(self, repofile):
        remove_file(os.path.join(self.site_root, repofile))

    def load_file(self, repofile):
        return load_file(os.path.join(self.site_root, repofile))

    def remove(self):
        assert self.site_root.startswith('/tmp/')
        if os.path.exists(self.site_root):
            shutil.rmtree(self.site_root)

    def change(self, **kwargs):
        added = kwargs.get('added', {})
        modified = kwargs.get('modified', {})
        deleted = kwargs.get('deleted', [])
        renamed = kwargs.get('renamed', {})
        plugins = kwargs.get('call_plugins', True)

        for repofile in added:
            self.save_file(repofile, added[repofile])
        for repofile in modified:
            self.save_file(repofile, modified[repofile])
        for repofile in deleted:
            self.delete_file(repofile)

        if plugins:
            # verify that renamed is correct
            assert len(set(renamed.values())) == len(renamed)

            for oldfile in renamed:
                assert oldfile in deleted
                deleted.remove(oldfile)

            for newfile in renamed.values():
                assert newfile in added
                added.remove(newfile)

            changed = ChangedFiles(added=list(added.keys()),
                                   modified=list(modified.keys()),
                                   deleted=deleted,
                                   renamed=renamed)
            call_plugins('on_files_changed', changed)


class TestCaseWithSite(TestCase):
    # config
    DEBUG = True
    TESTING = True

    files = {}
    folders = []

    def create_app(self):
        self.site = BaseTestSite(files=self.files, folders=self.folders)
        self.site.initialize()
        return yawt.create_app(self.site.site_root, config=self)

    def setUp(self):
        self.app.preprocess_request()

    def tearDown(self):
        self.site.remove()
