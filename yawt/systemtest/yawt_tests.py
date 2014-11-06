import unittest
import yawt
import tempfile
import shutil
import os
from urlparse import urlparse

config = """
YAWT_BASE_URL = 'http://www.awesome.net/blog'
YAWT_DEFAULT_FLAVOUR = 'vanilla'
YAWT_INDEX_FILE = 'stuff'
YAWT_ARTICLE_TEMPLATE = 'post'
YAWT_ARTICLE_EXTENSIONS = ['md']
"""

article_tmpl = """type: ARTICLE
fullname: {{article.info.fullname}}
category: {{article.info.category}}
slug: {{article.info.slug}}
extension: {{article.info.extension}}
create_time: {{article.info.create_time}}
modified_time: {{article.info.modified_time}}

{{article.content}}
"""

madras_tmpl = """type: MADRAS
fullname: {{article.info.fullname}}
category: {{article.info.category}}
slug: {{article.info.slug}}
extension: {{article.info.extension}}
create_time: {{article.info.create_time}}
modified_time: {{article.info.modified_time}}

{{article.content}}
"""

index_tmpl = """type: INDEX
fullname: {{article.info.fullname}}
category: {{article.info.category}}
slug: {{article.info.slug}}
extension: {{article.info.extension}}
create_time: {{article.info.create_time}}
modified_time: {{article.info.modified_time}}

{{article.content}}
"""

article_tmpl_flav1 = """type: ARTICLE_FLAV1
fullname: {{article.info.fullname}}
category: {{article.info.category}}
slug: {{article.info.slug}}
extension: {{article.info.extension}}
create_time: {{article.info.create_time}}
modified_time: {{article.info.modified_time}}

{{article.content}}
"""

foo_article_tmpl = """type: ARTICLE
foo: {{article.info.foo}}
"""

not_found_tmpl = """Article not found"""
not_found_tmpl_flav1 = """Article not found (flav1)"""

class SomeConfig(object):
    YAWT_DEFAULT_FLAVOUR = 'chocolate'
    YAWT_INDEX_FILE = 'foo'
    YAWT_ARTICLE_TEMPLATE = 'entry'
    YAWT_ARTICLE_EXTENSIONS = ['rst']

class ConfigFlav1(object):
    YAWT_CONTENT_TYPE_FLAV1 = 'text/x-markdown'

class Plugin1Config(object):
    YAWT_PLUGINS = [('plugin1','yawt.systemtest.yawt_tests.Plugin1')]

class CombinedPluginConfig(object):
    YAWT_PLUGINS = [('plugin1','yawt.systemtest.yawt_tests.Plugin1'),
                    ('plugin2','yawt.systemtest.yawt_tests.Plugin2')]

class Plugin1(object):
    def init_app(self, app):
        pass

    def on_article_fetch(self, article):
        article.info.foo = 1
        return article

class Plugin2(object):
    def init_app(self, app):
        pass

    def on_article_fetch(self, article):
        article.info.foo = 2
        return article

class YawtSystemLevelTests(unittest.TestCase):
    """
    YAWT system level tests
    """
    def setUp(self):  
        self.app = None
        self.client = None
        
        self.root_dir = tempfile.mkdtemp()
        assert self.root_dir.startswith('/tmp/')
            
        # copy templates over
        self.template_dir = os.path.join(self.root_dir, 'templates')
        os.makedirs(self.template_dir)
        self._save_file(os.path.join(self.template_dir, '404.html'), not_found_tmpl)
        
        self.content_dir = os.path.join(self.root_dir, 'content')
        os.makedirs(self.content_dir)

    def _setup_client(self):
        self.app = yawt.create_app(self.root_dir, config = None)
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()

    def test_yawt_has_global_config_with_defaults(self):
        self.app = yawt.create_app(self.root_dir, config = None)
        self.app.config['DEBUG'] = True
        self.assertEquals('content', self.app.config['YAWT_CONTENT_FOLDER'])
        self.assertEquals('article', self.app.config['YAWT_ARTICLE_TEMPLATE'])
        self.assertEquals('html', self.app.config['YAWT_DEFAULT_FLAVOUR'])
        self.assertEquals('index', self.app.config['YAWT_INDEX_FILE'])
        self.assertEquals(['txt'], self.app.config['YAWT_ARTICLE_EXTENSIONS'])        
        self.assertEquals('templates', self.app.yawt_template_folder)
        self.assertEquals('static', self.app.yawt_static_folder)
        self.assertEquals(self.root_dir, self.app.yawt_root_dir)

    def test_config_in_site_folder_overrides_defaults(self):
        self._save_file(os.path.join(self.root_dir, 'config.py'), config)
        self.app = yawt.create_app(self.root_dir, config = None)
        self.app.config['DEBUG'] = True
        self.assertEquals('stuff', self.app.config['YAWT_INDEX_FILE'])
        self.assertEquals(['md'], self.app.config['YAWT_ARTICLE_EXTENSIONS'])
        self.assertEquals('vanilla', self.app.config['YAWT_DEFAULT_FLAVOUR'])
        self.assertEquals('post', self.app.config['YAWT_ARTICLE_TEMPLATE'])

    def test_supplied_config_overrides_all(self):
        self._save_file(os.path.join(self.root_dir, 'config.py'), config)
        self.app = yawt.create_app(self.root_dir, config = SomeConfig())
        self.app.config['DEBUG'] = True
        self.assertEquals('foo', self.app.config['YAWT_INDEX_FILE'])
        self.assertEquals(['rst'], self.app.config['YAWT_ARTICLE_EXTENSIONS'])
        self.assertEquals('chocolate', self.app.config['YAWT_DEFAULT_FLAVOUR'])
        self.assertEquals('entry', self.app.config['YAWT_ARTICLE_TEMPLATE'])

    def test_missing_root_page_results_in_404(self):
        self._setup_client()
        rv = self.client.get("/")
        assert 'Article not found' in rv.data
        self.assertEqual(rv.status_code, 404)

    def test_missing_category_page_results_in_404(self): 
        self._setup_client()
        rv = self.client.get("random/blah")
        assert 'Article not found' in rv.data
        self.assertEqual(rv.status_code, 404)

    def test_root_page_is_accessible_with_article_template(self):
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('index.txt', 'hello everyone')
        rv = self.client.get("/")
        assert 'hello everyone' in rv.data
        assert 'ARTICLE' in rv.data

    def test_root_page_is_accessible_with_index_template(self):
        self._setup_client()
        self._save_template('index.html', index_tmpl)
        # shadowed by the index template
        self._save_template('article.html', article_tmpl)
        self._save_content('index.txt', 'hello everyone')
        rv = self.client.get("/")
        assert 'hello everyone' in rv.data
        assert 'INDEX' in rv.data
 
    def test_page_is_accessible_with_page_specific_template(self): 
        self._setup_client()
        self._save_template('cooking/madras.html', madras_tmpl)
        # shadowed by the specific template
        self._save_template('cooking/article.html', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras')
        assert 'this is very spicy' in rv.data
        assert 'MADRAS' in rv.data

    def test_page_is_accessible_with_category_specific_template(self): 
        self._setup_client()
        self._save_template('cooking/article.html', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras')
        assert 'this is very spicy' in rv.data
        assert 'ARTICLE' in rv.data

    def test_page_is_accessible_with_root_template(self): 
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras')
        assert 'this is very spicy' in rv.data
        assert 'ARTICLE' in rv.data

    def test_category_page_with_no_index_article_gives_404(self): 
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')
        rv = self.client.get('/cooking/')
        assert 'Article not found' in rv.data
        self.assertEqual(rv.status_code, 404)

    def test_category_url_with_no_slash_redirects_to_slash(self):
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/index.txt', 'this is all about cooking')
        rv = self.client.get('/cooking')
        self.assertEqual(rv.status_code, 302)
        assert 'Location' in rv.headers
        self.assertEquals( '/cooking/', urlparse(rv.headers['Location']).path )

    def test_category_page_with_index_article_is_accessible(self): 
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/index.txt', 'this is all about cooking')
        rv = self.client.get('/cooking/')
        assert 'this is all about cooking' in rv.data
        assert 'ARTICLE' in rv.data

    def test_page_is_accessible_with_flavoured_root_template(self): 
        self._setup_client()
        self._save_template('article.flav1', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras.flav1')
        assert 'this is very spicy' in rv.data
        assert 'ARTICLE' in rv.data

    def test_request_for_non_existent_flavour_gives_404(self): 
        self._setup_client()
        self._save_template('article.html', madras_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras.flav1')
        assert 'Article not found' in rv.data
        self.assertEqual(rv.status_code, 404)

    def test_configured_content_type_is_sent_in_response(self):
        self.app = yawt.create_app(self.root_dir, config = ConfigFlav1())
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()
        self._save_template('article.flav1', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras.flav1')
        assert 'Content-Type' in rv.headers
        self.assertEquals( 'text/x-markdown', rv.headers['Content-Type'] )
 
    def test_article_info_is_loaded(self):
        self._setup_client()
        self._save_template('article.html', article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')

        rv = self.client.get('/cooking/madras')
        assert 'fullname: cooking/madra' in rv.data
        assert 'category: cooking' in rv.data
        assert 'slug: madras' in rv.data
        assert 'extension: txt' in rv.data
        self.assertRegexpMatches(rv.data, 'create_time: .+')
        self.assertRegexpMatches(rv.data, 'modified_time: .+')

    def test_plugin_run_when_article_fetched(self):
        self.app = yawt.create_app(self.root_dir, config = Plugin1Config())
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()
        self._save_template('article.html', foo_article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')
        rv = self.client.get('/cooking/madras')
        assert 'foo: 1' in rv.data
 
    def test_last_plugin_wins_when_article_fetched(self):
        self.app = yawt.create_app(self.root_dir, config = CombinedPluginConfig())
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()
        self._save_template('article.html', foo_article_tmpl)
        self._save_content('cooking/madras.txt', 'this is very spicy')
        rv = self.client.get('/cooking/madras')
        assert 'foo: 2' in rv.data

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
        
if __name__ == '__main__':
    unittest.main()
