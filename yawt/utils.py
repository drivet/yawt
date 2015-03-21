"""Just a hodge podge of utility methods for use in various places in YAWT
"""
from __future__ import absolute_import

import os
import re
from flask import current_app


def load_file(filename):
    """Load file filename and return contents"""
    with open(filename, 'r') as f:
        file_contents = f.read()
    return unicode(file_contents)


def save_file(filename, contents):
    """Save contents to filename"""
    with open(filename, 'w') as f:
        f.write(unicode(contents))


def remove_file(filename):
    """Remove file at filename"""
    os.remove(filename)


def copy_file(oldfile, newfile):
    """Copy file over to new file location"""
    with open(oldfile, 'r') as f:
        contents = f.read()
    with open(newfile, 'w') as f:
        f.write(contents)


def move_file(oldfile, newfile):
    """Move file to new file location"""
    os.rename(oldfile, newfile)


def ensure_path(path):
    """Make sure the path exists, creating it if need be"""
    if not os.path.exists(path):
        os.makedirs(path)


def base_and_ext(basefile):
    """Split basefile into base filename and extension"""
    base, extension = os.path.splitext(basefile)
    extension = extension.split('.')[-1]
    return (base, extension)


def has_method(obj, method):
    """Return true of this oject has a callbale attribute on it that matches
    the supplied name
    """
    return hasattr(obj, method) and callable(getattr(obj, method))


# possibly doesn't belong here
def fullname(sitefile):
    """sitefile is relative to the site_root, not absolute"""
    content_root = current_app.config['YAWT_CONTENT_FOLDER']
    if not sitefile.startswith(content_root):
        return None
    rel_filename = re.sub('^%s/' % (content_root), '', sitefile)
    name, ext = os.path.splitext(rel_filename)
    ext = ext[1:]
    if ext not in current_app.config['YAWT_ARTICLE_EXTENSIONS']:
        return None
    return name
