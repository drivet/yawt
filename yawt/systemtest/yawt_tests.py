#pylint: skip-file
import yawt
from yawt.test import template, TestCaseWithSite


config = """
YAWT_BASE_URL = 'http://www.hereitis.com'
YAWT_DRAFT_FOLDER = 'other_drafts'
"""

FILES = {
    # config
    'config.py': config,
    # templates
    'templates/article.html': template('ROOT'),
    'templates/article.flav': template('FLAV'),
    'templates/cooking/article.html': template('COOKING'),
    'templates/cooking/article.flav': template('FLAV COOKING'),
    'templates/specific.html': template('SPECIFIC'),
    'templates/404.html': template('MISSING'),
    # entries
    'content/index.txt': 'index text',
    'content/entry.txt': 'entry text',
    'content/cooking/index.txt': 'cooking index text',
    'content/cooking/madras.txt': 'madras text',
    'content/specific.txt': 'specific text',
    'content/reading/hyperion.txt': 'hyperion text'
}


class YawtConfigurationTests(TestCaseWithSite):
    """
    YAWT configuration tests
    """

    # config
    YAWT_BASE_URL = 'http://www.foobar.com'
    YAWT_DRAFT_FOLDER = 'yet_other_drafts'
    DEBUG = True
    TESTING = True

    files = FILES

    def test_configuration_is_read_from_site_file(self):
        app = yawt.create_app(self.site.site_root)
        self.assertEquals('other_drafts', app.config['YAWT_DRAFT_FOLDER'])
        self.assertEquals('http://www.hereitis.com',
                          app.config['YAWT_BASE_URL'])

    def test_supplied_config_overrides_site_file(self):
        app = yawt.create_app(self.site.site_root, config=self)
        self.assertEquals('yet_other_drafts', app.config['YAWT_DRAFT_FOLDER'])
        self.assertEquals('http://www.foobar.com',
                          app.config['YAWT_BASE_URL'])


class YawtSystemLevelTests(TestCaseWithSite):
    """
    YAWT system level tests
    """

    # config
    DEBUG = True
    TESTING = True

    files = FILES

    def test_missing_pages_result_in_404(self):
        rv = self.client.get("/random/blah")
        self.assert404(rv)
        assert 'MISSING' in rv.data

        rv = self.client.get("/reading/")
        self.assert404(rv)
        assert 'MISSING' in rv.data

    def test_root_url_loads_index_page(self):
        rv = self.client.get("/")
        self.assert200(rv)
        assert 'ROOT' in rv.data
        assert 'index text' in rv.data

    def test_uncategorized_page_rendered_with_root_template(self):
        rv = self.client.get("/entry")
        self.assert200(rv)
        assert 'ROOT' in rv.data
        assert 'entry text' in rv.data

    def test_root_template_used_as_fallback_for_categorized_page(self):
        rv = self.client.get("/reading/hyperion")
        self.assert200(rv)
        assert 'ROOT' in rv.data
        assert 'hyperion text' in rv.data

    def test_more_specific_template_wins(self):
        rv = self.client.get("/cooking/madras")
        self.assert200(rv)
        assert 'COOKING' in rv.data
        assert 'madras text' in rv.data

    def test_template_with_name_of_page_wins(self):
        rv = self.client.get("/specific")
        self.assert200(rv)
        assert 'SPECIFIC' in rv.data
        assert 'specific text' in rv.data

    def test_flavoured_root_template_chosen(self):
        rv = self.client.get('/entry.flav')
        self.assert200(rv)
        assert 'FLAV' in rv.data
        assert 'entry text' in rv.data

    def test_flavoured_categorized_template_chosen(self):
        rv = self.client.get('/cooking/madras.flav')
        self.assert200(rv)
        assert 'FLAV COOKING' in rv.data
        assert 'madras text' in rv.data

    def test_missing_flavour_results_in_404(self):
        rv = self.client.get('/cooking/madras.vanilla')
        self.assert404(rv)
        assert 'MISSING' in rv.data

    def test_category_url_with_no_slash_redirects_to_slash(self):
        rv = self.client.get('/cooking')
        self.assertRedirects(rv, '/cooking/')

    def test_category_url_loads_index_article(self):
        rv = self.client.get('/cooking/')
        self.assert200(rv)
        assert 'COOKING' in rv.data
        assert 'cooking index text' in rv.data
