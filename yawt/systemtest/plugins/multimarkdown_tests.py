import tempfile
import shutil
import os
import unittest
import yawt

article_tmpl = """type: ARTICLE
fullname: {{article.info.fullname}}
category: {{article.info.category}}
slug: {{article.info.slug}}
extension: {{article.info.extension}}
create_time: {{article.info.create_time}}
modified_time: {{article.info.modified_time}}

Metadata:
stuff - {{article.info.stuff}}

{{article.content}}
"""
class SomeConfig(object):
    YAWT_ARTICLE_EXTENSIONS = ['md']
    YAWT_PLUGINS = [('markdown','yawt.plugins.multimarkdown.MarkdownPlugin')]

class MarkdownPluginIntegrationTests(unittest.TestCase):
    def setUp(self):  
        self.app = None
        self.client = None
        
        self.root_dir = tempfile.mkdtemp()
        assert self.root_dir.startswith('/tmp/')
            
        # copy templates over
        self.template_dir = os.path.join(self.root_dir, 'templates')
        os.makedirs(self.template_dir)

        self.content_dir = os.path.join(self.root_dir, 'content')
        os.makedirs(self.content_dir)

    def _setup_client(self):
        self.app = yawt.create_app(self.root_dir, config = SomeConfig())
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()

    def test_markdown_converts_content_to_html(self):
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/madras.md', '*this is very spicy*')

        rv = self.client.get('/cooking/madras')
        assert '<p><em>this is very spicy</em></p>' in rv.data
        
    def test_markdown_loads_metadata(self):
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/madras.md', 'stuff: hello\n\n*this is very spicy*')

        rv = self.client.get('/cooking/madras')
        assert 'stuff - hello' in rv.data
        
    def _save_file(self, filename, contents):
        f = open(filename, 'w')
        f.write(contents)
        f.close()

    def _save_relative_file(self, root_dir, relative_path, content):
        abspath = os.path.join( root_dir, relative_path)
        category_dir = os.path.split(abspath)[0]
        if not os.path.isdir(category_dir):
            os.makedirs(category_dir)
        self._save_file(abspath, content)

    def _save_content(self, relative_path, content):
        self._save_relative_file(self.content_dir, relative_path, content)

    def _save_template(self, relative_path, content):
        self._save_relative_file(self.template_dir, relative_path, content)
 
    def _save_category(self, category_dir):
        abspath = os.path.join(self.content_dir, category_dir)
        if not os.path.isdir(abspath):
            os.makedirs(abspath)

    def tearDown(self):  
        assert self.root_dir.startswith('/tmp/')
        shutil.rmtree(self.root_dir)
