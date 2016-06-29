"""The basic YAWT excerpt extension"""
from __future__ import absolute_import

from BeautifulSoup import BeautifulSoup
from flask import current_app, Markup

from yawtext import Plugin


class YawtExcerpt(Plugin):
    """YAWT excerpt extension.  Sets an excerpt into the article summary
    attribute, based on the configured word count"""
    def __init__(self, app=None):
        super(YawtExcerpt, self).__init__(app)

    def init_app(self, app):
        """Set up the default word count"""
        app.config.setdefault('YAWT_EXCERPT_WORDCOUNT', 50)

    def on_article_fetch(self, article):
        """Set the article summary"""
        max_word_count = current_app.config['YAWT_EXCERPT_WORDCOUNT']
        soup = BeautifulSoup(article.content)
        summary = ''
        word_count = 0
        for child in soup.findAll(recursive=False):
            summary += str(child)
            word_count += _count_words(child)
            if word_count >= max_word_count:
                break

        if summary:
            article.info.summary = Markup(unicode(summary, 'utf-8'))
        else:
            words = article.content.split()[0:max_word_count]
            words.append("[...]")
            article.info.summary = unicode(" ".join(words), 'utf-8')

        return article


def _count_words(soup):
    rawtext = _striptags(soup)
    return len(rawtext.split())


def _striptags(soup):
    return ''.join([e for e in soup.recursiveChildGenerator() if isinstance(e, unicode)])
