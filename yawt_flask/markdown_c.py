from flask import Markup
import markdown

def init(app):
    pass

class MarkdownArticle(object):
    def __init__(self, article):
        self._article = article

    @property
    def content(self):
        md = markdown.Markdown()
        return Markup(md.convert(self._article._article_content.content))
       
    def __getattr__(self, attrname):
        return getattr(self._article, attrname)
    
def on_article_fetch(config, article):
    return MarkdownArticle(article)
