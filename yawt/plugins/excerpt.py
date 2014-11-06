from flask import current_app

def _config(key):
    return current_app.config[key]

class ExcerptPlugin(object):
    def init_app(self, app):
        app.config.setdefault('YAWT_EXCERPT_WORDCOUNT', 50)

    def on_article_fetch(self, article):
        article.info.summary = excerpt(article, _config('YAWT_EXCERPT_WORDCOUNT'))
        return article

def excerpt(article, word_count):
    words = article.content.split()[0:word_count]
    words.append("[...]")
    return " ".join(words)
