#pylint: skip-file
import subprocess

from yawt.test import TempFolder
from yawtext.git import _git_cmd


class TempGitFolder(TempFolder):
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
