#pylint: skip-file
import unittest

from flask import Markup

from yawt import create_app
from yawt.article import Article, ArticleInfo
from yawtext.excerpt import YawtExcerpt


class TestYawtExcerpt(unittest.TestCase):
    def setUp(self):
        self.plugin = YawtExcerpt()
        self.app = create_app('/tmp', extension_info = extension_info(self.plugin))

    def test_default_word_count_is_50(self):
        self.assertEqual(50, self.app.config['YAWT_EXCERPT_WORDCOUNT'])

    def test_text_summary_attribute_set_correctly(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'md'
            article = Article()
            article.info = info
            article.content = 'stuff blah hello dude the east market'
            self.app.config['YAWT_EXCERPT_WORDCOUNT'] = 5
            article = self.plugin.on_article_fetch(article)
        self.assertEqual('stuff blah hello dude the [...]', article.info.summary)

 
    def test_html_summary_attribute_set_correctly(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            info = ArticleInfo()
            info.extension = 'md'
            article = Article()
            article.info = info
            article.content = '<p>stuff</p><p>blah hello</p><p>dude the</p><p>east market</p>'
            self.app.config['YAWT_EXCERPT_WORDCOUNT'] = 5
            article = self.plugin.on_article_fetch(article)
        self.assertEqual(Markup('<p>stuff</p><p>blah hello</p><p>dude the</p>'), article.info.summary)


    def tearDown(self):
        pass

def extension_info(plugin):
    return ({'yawtext.excerpt.YawtExcerpt': plugin}, 
            [plugin])
