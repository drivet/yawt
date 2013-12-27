import os
import yaml


def ensure_path(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_abs_path_app(app, path):
    return get_abs_path(app.config['YAWT_BLOGPATH'], path)


def get_abs_path(blogpath, path):
    if os.path.isabs(path):
        return path
    else:
        return os.path.join(blogpath, path)


def load_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.load(f)

        
def load_string(filename):
    with open(filename, 'r') as f:
        return f.read()


def save_yaml(filename, obj):
    ensure_path(os.path.dirname(filename))
    with open(filename, 'w') as f:
        yaml.dump(obj, f)


def save_string(filename, s):
    ensure_path(os.path.dirname(filename))
    with open(filename, 'w') as f:
        f.write(s)

        
def chdir(path):
    os.chdir(path)

    
def join(*paths):
    return os.path.join(*paths)

    
def isfile(path):
    return os.path.isfile(path)    

    
def isdir(path):
    return os.path.isdir(path)


def exists(path):
    return os.path.exists(path)
