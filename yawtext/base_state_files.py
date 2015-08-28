from __future__ import absolute_import

import os
import jsonpickle
from yawt.utils import load_file, abs_state_folder, cfg, single_dict_var


class StateFiles(object):
    def __init__(self, root_dir, statefile):
        self.root_dir = root_dir
        self.statefile = statefile

    def load_state_files(self, bases):
        statemap = {}
        for base in bases:
            abs_state_file = self.abs_state_file(base)
            if os.path.isfile(abs_state_file):
                stateobj = jsonpickle.decode(load_file(abs_state_file))
                statemap[base] = stateobj

    def abs_state_file(self, base):
        return os.path.join(self.root_dir, base, self.statefile)


def state_context_processor(statefile_cfg, bases_cfg, varname):
    statefiles = StateFiles(abs_state_folder(), cfg(statefile_cfg))
    stateobj = statefiles.load_state_files(cfg(bases_cfg))
    return single_dict_var(varname, stateobj)
