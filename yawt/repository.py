import subprocess
import os
from yawt.fileutils import save_string, ensure_path, join, exists, isdir

class RepoException(Exception):
    pass


class Repository:
    def __init__(self, root):
        self.root = root

    def initialize(self, repotype="hg", files=None):
        """
        repotype is either hg or git
        files must be relative to the root
        """
        if exists(self.root):
            raise RepoException("repotype directory already exists: " + self.root)

        repoimpl = get_repo_impl(repotype)
        repoimpl.init(self.root)
        if files is not None:
            self._add_files(files, repoimpl)
            repoimpl.commit(self.root, "initial commit")

    def add_contents(self, files):
        repoimpl = detect_repo_impl(self.root)
        if files is not None:
            self._add_files(files, repoimpl)
            
    def commit_contents(self, files):
        repoimpl = detect_repo_impl(self.root)
        if files is not None:
            self._add_files(files, repoimpl)
            repoimpl.commit(self.root, "initial commit")

    def save(self, message):
        repoimpl = detect_repo_impl(self.root)
        repoimpl.commit(self.root, message)

    def move(self, draftfile, postfile, move_msg):
        repoimpl = detect_repo_impl(self.root)
        repoimpl.move(self.root, draftfile, postfile)
        repoimpl.commit(self.root, move_msg)

    def _add_files(self, files, repoimpl):
        for f in files:
            path_to_file = join(self.root, f)
            if path_to_file.endswith('/'):
                ensure_path(path_to_file)
            else:
                save_string(path_to_file, files[f])
        repoimpl.add(self.root, files.keys())
                    

def get_repo_impl(repotype):
    if repotype is "hg":
        return HgRepo()
    elif repotype is "git":
        return GitRepo()
    else:
        raise RepoException("unknown repotype: " + repotype)

def detect_repo_impl(rootdir):
    if isdir(rootdir + "/.hg"):
        return HgRepo()
    elif isdir(rootdir + "/.git"):
        return GitRepo()
    else:
        raise RepoException("unable to detect repository at: " + rootdir)

class HgRepo:
    def __init__(self):
        pass

    def init(self, rootdir):
        if subprocess.call(['hg', 'init', rootdir]) is not 0:
            raise RepoException("repo init failed")

    def add(self, rootdir, files):
        """
        files must be relative to the rootdir
        """
        args = ['hg', '--cwd', rootdir, 'add']
        args.extend(files)
        if subprocess.call(args) is not 0:
            raise RepoException("repo add failed with " + str(args))
        
    def commit(self, rootdir, message):
        if subprocess.call(['hg', '--cwd', rootdir, 'ci', '-m', message]) is not 0:
            raise RepoException("repo commit failed")
            
    def move(self, rootdir, draftfile, postfile):
        if subprocess.call(['hg', '--cwd', rootdir, 'mv', draftfile, postfile]) is not 0:
            raise RepoException("repo commit failed")

class GitRepo:
    def __init__(self):
        pass
        
    def init(self, rootdir):
        if subprocess.call(['git', 'init', '-q', rootdir]) is not 0:
            raise RepoException("repo init failed")

    def add(self, rootdir, files):
        """
        files must be relative to the rootdir
        """
        cwd = os.getcwd()
        os.chdir(rootdir)
        try:
            args = ['git', 'add']
            args.extend(files)
            if subprocess.call(args) is not 0:
                raise RepoException("repo add failed with " + str(args))
        finally:
            os.chdir(cwd)

    def commit(self, rootdir, message):
        cwd = os.getcwd()
        os.chdir(rootdir)
        try: 
            if subprocess.call(['git', 'commit', '-q', '-a', '-m', message]) is not 0:
                raise RepoException("repo commit failed")
        finally:
            os.chdir(cwd)
 
    def move(self, rootdir, draftfile, postfile):
        cwd = os.getcwd()
        os.chdir(rootdir)
        try:  
            print str(rootdir)
            print str(['git', 'mv', draftfile, postfile])
            ensure_path(os.path.dirname(postfile))
            if subprocess.call(['git', 'mv', draftfile, postfile]) is not 0:
                raise RepoException("repo commit failed")
        finally:
            os.chdir(cwd)
