import unittest
from yawt.plugins.excerpt import ExcerptPlugin
from yawt.article import Article, ArticleInfo
from mock import patch

class FakeApp(object):
    def __init__(self):
        self.config = {}

class TestExcerptPlugin(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.patcher = patch('yawt.plugins.excerpt.current_app', self.app)
        self.patcher.start()
        self.plugin = ExcerptPlugin()
        self.plugin.init(self.app)

    def test_default_word_count_is_50(self):
        self.assertEqual(50, self.app.config['YAWT_EXCERPT_WORDCOUNT'])

    def test_summary_attribute_set_correctly(self):
        info = ArticleInfo()
        info.extension = 'md'
        article = Article()
        article.info = info
        article.content = 'stuff blah hello dude the east market'
        self.app.config['YAWT_EXCERPT_WORDCOUNT'] = 5
        article = self.plugin.on_article_fetch(article)
        self.assertEqual('stuff blah hello dude the [...]', article.info.summary)
  
    def tearDown(self):
        self.patcher.stop()
