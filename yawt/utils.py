import os

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
