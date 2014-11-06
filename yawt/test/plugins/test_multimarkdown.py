import unittest
from yawt.plugins.multimarkdown import MarkdownPlugin
from yawt.article import Article, ArticleInfo
from mock import patch

class FakeApp(object):
    def __init__(self):
        self.config = {}

class TestMultiMarkdownPlugin(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.patcher = patch('yawt.plugins.multimarkdown.current_app', self.app)
        self.patcher.start()
        self.plugin = MarkdownPlugin()
        self.plugin.init(self.app)

    def test_default_extensions_are_set(self):
        self.assertEquals(['md'], self.app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS'])
        self.assertEquals(['meta'], self.app.config['YAWT_MULTIMARKDOWN_EXTENSIONS'])
        
    def test_plugin_skips_non_markdown_articles(self):
        info = ArticleInfo()
        info.extension = 'html'
        article = Article()
        article.info = info
        article.content = '*stuff*'
        article = self.plugin.on_article_fetch(article)
        self.assertEqual('*stuff*', article.content)

    def test_plugin_processes_content_of_markdown_articles(self):
        info = ArticleInfo()
        info.extension = 'md'
        article = Article()
        article.info = info
        article.content = '*stuff*'
        article = self.plugin.on_article_fetch(article)
        self.assertEqual('<p><em>stuff</em></p>', article.content)

    def test_markdown_metadata_overrides_article_attributes(self):
        info = ArticleInfo()
        info.extension = 'md'
        info.title = 'okay title'
        info.author = 'john'
        article = Article()
        article.info = info
        article.content = 'title: awesome title\nauthor:desmond\n\n*stuff*'
        article = self.plugin.on_article_fetch(article)
        self.assertEqual('awesome title', article.info.title)
        self.assertEqual('desmond', article.info.author)

    def tearDown(self):
        self.patcher.stop()
