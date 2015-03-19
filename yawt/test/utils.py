#pylint: skip-file

from mock import patch
from yawt.test import fake_filesystem

class FakeOs:
    def __init__(self, path_to_os_import):
        self.path_to_os_import = path_to_os_import
        self.fs = None
        self.os = None
        self.os_patcher = None
        self.os_path_patcher = None
        self.open_patcher = None

    def start(self):
        self.fs = fake_filesystem.FakeFilesystem()
        self.os = fake_filesystem.FakeOsModule(self.fs)
        self.os_patcher = patch(self.path_to_os_import + '.os', self.os)
        self.os_path_patcher = patch(self.path_to_os_import + '.os.path', self.os.path)
        self.open_patcher = patch('__builtin__.open', fake_filesystem.FakeFileOpen(self.fs))
        self.os_patcher.start() 
        self.os_path_patcher.start()
        self.open_patcher.start()

    def stop(self):
        self.os_patcher.stop()
        self.os_path_patcher.stop()
        self.open_patcher.stop()
