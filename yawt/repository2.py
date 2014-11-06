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
                    
