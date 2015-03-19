import os
import re
from flask import current_app

def load_file(filename):
    with open(filename, 'r') as f:
        file_contents = f.read()
    return unicode(file_contents)

def save_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(unicode(contents))

def remove_file(filename):
    os.remove(filename)

def copy_file(oldfile, newfile):
    with open(oldfile, 'r') as f:
        contents = f.read()
    with open(newfile, 'w') as f:
        f.write(contents)

def move_file(oldfile, newfile):
    os.rename(oldfile, newfile)

def ensure_path(path):
    if not os.path.exists(path):
        os.makedirs(path)

def base_and_ext(basefile):
    base, extension = os.path.splitext(basefile)
    extension = extension.split('.')[-1]
    return (base, extension)

def has_method(obj, method):
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
