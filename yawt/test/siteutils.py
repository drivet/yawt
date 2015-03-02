import tempfile
import os
import shutil
from yawt.utils import save_file, load_file, remove_file


# Manages a YAWT site in the /tmp folder
class TempSite(object):
   
    def __init__(self, content_root = 'content', 
                 template_root='templates',
                 draft_root='drafts',
                 state_root='_state'):
        self.site_root = None
        self.content_root = content_root
        self.template_root = template_root
        self.draft_root = draft_root
        self.state_root = state_root

    def initialize(self):
        self.site_root = tempfile.mkdtemp()
        os.makedirs(self.abs_content_root())
        os.makedirs(self.abs_template_root())
        os.makedirs(self.abs_draft_root())
        os.makedirs(self.abs_state_root())
        
    def abs_content_root(self):
        return os.path.join(self.site_root, self.content_root)

    def abs_template_root(self):
        return os.path.join(self.site_root, self.template_root)

    def abs_draft_root(self):
        return os.path.join(self.site_root, self.draft_root)

    def abs_state_root(self):
        return os.path.join(self.site_root, self.state_root)
 
    def mk_content_category(self, category):
        abs_content_category = os.path.join(self.abs_content_root(), category)
        os.makedirs(abs_content_category)

    def save_content(self, rel_filename, content=''):
        abs_content_file = os.path.join(self.abs_content_root(), rel_filename)
        save_file(abs_content_file, content)
  
    def remove_content(self, rel_filename):
        abs_content_file = os.path.join(self.abs_content_root(), rel_filename)
        remove_file(abs_content_file)
  
    def load_content(self, rel_filename):
        abs_content_file = os.path.join(self.abs_content_root(), rel_filename)
        return load_file(abs_content_file)
  
    def mk_template_category(self, category):
        abs_template_category = os.path.join(self.abs_template_root(), category)
        os.makedirs(abs_template_category)

    def save_template(self, rel_filename, template=''):
        abs_template_file = os.path.join(self.abs_template_root(), rel_filename)
        save_file(abs_template_file, template)

    def load_template(self, rel_filename):
        abs_template_file = os.path.join(self.abs_template_root(), rel_filename)
        return load_file(abs_template_file)

    def save_file(self, rel_filename, content=''):
        abs_file = os.path.join(self.site_root, rel_filename)
        save_file(abs_file, content)

    def load_file(self, rel_filename):
        abs_file = os.path.join(self.site_root, rel_filename)
        return load_file(abs_file)

    def save_state_file(self, rel_filename, content=''):
        abs_state_file = os.path.join(self.state_root, rel_filename)
        save_file(abs_state_file, content)
 
    def load_state_file(self, rel_filename):
        abs_state_file = os.path.join(self.state_root, rel_filename)
        return load_file(abs_state_file)

    def remove(self):
        assert self.site_root.startswith('/tmp/')
        if os.path.exists(self.site_root):
            shutil.rmtree(self.site_root)
