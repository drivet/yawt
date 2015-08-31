"""Just a hodge podge of utility methods for use in various places in YAWT
"""
from __future__ import absolute_import

import os
import re
from datetime import date, datetime, time
from flask import current_app
import yawt


def load_file(filename):
    """Load file filename and return contents"""
    with open(filename, 'r') as f:
        file_contents = f.read()
    return unicode(file_contents)


def save_file(filename, contents):
    """Save contents to filename"""
    ensure_path(os.path.dirname(filename))
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


def extensions(app=None):
    """Returns the list of extension known to YAWT"""
    if not app:
        app = current_app
    if app.extension_info:
        return app.extension_info[1]
    else:
        return []


def call_plugins(method, *args, **kw):
    """Go through all known extensions and call the supplied method with the
    supplied args if present
    """
    for ext in extensions():
        if has_method(ext, method):
            getattr(ext, method)(*args, **kw)


def call_plugins_arg(method, arg):
    """Go through all known extensions and call the supplied method with the
    single arg, and pass the result along
    """
    for ext in extensions():
        if has_method(ext, method):
            arg = getattr(ext, method)(arg)
    return arg


def write_post(metadata, content, filename):
    """Quick and easy way to save a post with metadata"""
    with open(filename, 'w') as f:
        f.write(u'---\n')
        for key in metadata:
            f.write(u'%s: %s\n' % (key, metadata[key]))
        f.write(u'---\n')
        f.write(unicode(content))


def run_in_context(repo_path, func, *args, **kwargs):
    """run the function in a YAWT/Flask request context"""
    app = yawt.create_app(repo_path)
    with app.test_request_context():
        current_app.preprocess_request()
        func(*args, **kwargs)


def cfg(key):
    """Easy way to get access to the config object"""
    return current_app.config[key]


def content_folder():
    """"Easy way to get access to the content folder"""
    return cfg('YAWT_CONTENT_FOLDER')


def state_folder():
    """"Easy way to get access to the state folder"""
    return cfg('YAWT_STATE_FOLDER')


def abs_state_folder():
    """"Easy way to get access to the state folder"""
    return os.path.join(current_app.yawt_root_dir, state_folder())


def is_content_file(repofile, cfolder=None):
    """Return True if repofile is a content file,
    i.e. lives in the content folder"""
    return repofile.startswith(cfolder or content_folder())


def joinfile(rootdir, name, ext):
    """Join together rootdir, name and ext"""
    return os.path.join(rootdir, name + "." + ext)


def single_dict_var(varname, obj):
    """Return a dict with the single entry passed in, if it's Truthy"""
    return {k: v for (k, v) in [(varname, obj)] if obj}


def get_attributes(obj):
    """Fetch public, non-callable attributes on an object"""
    attributes = [(a, getattr(obj, a))
                  for a in set(dir(obj)).difference(dir(object))
                  if a[0] != "_"]
    return {a[0]: a[1] for a in attributes if not callable(a[1])}


def format_value(val):
    """format a value, using its __repr__"""
    if isinstance(val, (basestring, date, time, datetime)):
        val = "'%s'" % val
        return val.encode("utf-8", errors="ignore")
    else:
        return val

class ReprMixin(object):
    """Provide a standard __repr__ implementation that formats __dict__
    based classes."""
    def __repr__(self):
        attrstr =", ".join("%s=%s" % (k[0], format_value(k[1])) for k in get_attributes(self).items())
        return "%s(%s)" % (type(self).__name__, attrstr)


class EqMixin(object):
    """Provode a standard __eq__ for dict based classes"""
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False
