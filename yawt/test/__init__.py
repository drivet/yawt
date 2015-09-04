#pylint: skip-file

import tempfile
import os
import shutil
from yawt.utils import save_file

POST_TEMPLATE = """\
---
{metadata}
---

{content}
"""


def dump_post(metadata, content):
    return POST_TEMPLATE.format(metadata=metadata, content=content)


# Manages a set of files and folders in the /tmp folder
class TempFolder(object):
    def __init__(self):
        self.site_root = None

        # map of filename relative to the root folder to content content can be
        # a string, or a tuple where the first is the metadata and the second is
        # the content
        self.files = {}

        # folders to create
        self.folders = []

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

    def remove(self):
        assert self.site_root.startswith('/tmp/')
        if os.path.exists(self.site_root):
            shutil.rmtree(self.site_root)


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


def template(name):
    return TEST_TEMPLATE.format(name=name)
