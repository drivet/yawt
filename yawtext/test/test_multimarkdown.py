import unittest
from yawtext.multimarkdown import YawtMarkdown
from yawt.article import Article, ArticleInfo
from yawt import create_app
from flask import g

class TestYawtMarkdown(unittest.TestCase):
    def setUp(self):
        self.plugin = YawtMarkdown()
        self.app = create_app('/tmp', extension_info = extension_info(self.plugin))

    def test_default_extensions_are_set(self):
        self.assertEquals(['md'], self.app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS'])
        self.assertEquals(['meta'], self.app.config['YAWT_MULTIMARKDOWN_EXTENSIONS'])
        
    def test_plugin_skips_non_markdown_articles(self): 
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'html'
            article = Article()
            article.info = info
            article.content = '*stuff*'
            article = g.site._on_article_fetch(article)
            self.assertEqual('*stuff*', article.content)

    def test_plugin_processes_content_of_markdown_articles(self): 
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'md'
            article = Article()
            article.info = info
            article.content = '*stuff*'
            article = g.site._on_article_fetch(article)
            self.assertEqual('<p><em>stuff</em></p>', article.content)

    def test_markdown_metadata_overrides_article_attributes(self): 
        with self.app.test_request_context():
            self.app.preprocess_request()
            info = ArticleInfo()
            info.extension = 'md'
            info.title = 'okay title'
            info.author = 'john'
            article = Article()
            article.info = info
            article.content = 'title: awesome title\nauthor:desmond\n\n*stuff*'
            article = g.site._on_article_fetch(article)
            self.assertEqual('awesome title', article.info.title)
            self.assertEqual('desmond', article.info.author)

    def tearDown(self):
        pass

def extension_info(plugin):
    return ({'yawtmultimarkdown': plugin}, [plugin], lambda app: plugin.init_app(app))
