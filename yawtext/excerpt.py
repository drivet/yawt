"""The basic YAWT excerpt extension"""
from __future__ import absolute_import

from flask import current_app


class YawtExcerpt(object):
    """YAWT excerpt extension.  Sets an excerpt into the article summary
    attribute, based on the configured word count"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Set up the default word count"""
        app.config.setdefault('YAWT_EXCERPT_WORDCOUNT', 50)

    def on_article_fetch(self, article):
        """Set the article summary"""
        word_count = current_app.config['YAWT_EXCERPT_WORDCOUNT']
        words = article.content.split()[0:word_count]
        words.append("[...]")
        article.info.summary = " ".join(words)
        return article
