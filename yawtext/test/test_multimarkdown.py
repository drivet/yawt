#pylint: skip-file
import unittest

from yawt import create_app
from yawt.article import Article, ArticleInfo
from yawtext.multimarkdown import YawtMarkdown


class TestYawtMarkdown(unittest.TestCase):
    def setUp(self):
        self.plugin = YawtMarkdown()
        self.app = create_app('/tmp', extension_info=extension_info(self.plugin))

    def test_default_extensions_are_set(self):
        self.assertEquals(['md'], self.app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS'])

    def test_plugin_skips_non_markdown_articles(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'html'
            article = Article()
            article.info = info
            article.content = '*stuff*'
            article = self.plugin.on_article_fetch(article)
            self.assertEqual('*stuff*', article.content)

    def test_plugin_processes_content_of_markdown_articles(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'md'
            article = Article()
            article.info = info
            article.content = '*stuff*'
            article = self.plugin.on_article_fetch(article)
            self.assertEqual('<p><em>stuff</em></p>', article.content)

    def tearDown(self):
        pass


def extension_info(plugin):
    return ({'yawtext.multimarkdown.YawtMarkdown': plugin},
            [plugin])
