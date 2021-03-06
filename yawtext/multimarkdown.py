"""The YAWT markdown plugin

This plugin will read a markdown file and a) convert the content to HTML
and b) convert the metadata to article attributes.
"""
import markdown
from flask import Markup, current_app

from yawtext import Plugin


def _load_markdown(file_contents):
    extensions = current_app.config['YAWT_MULTIMARKDOWN_EXTENSIONS']
    mdown = markdown.Markdown(extensions=extensions)
    markup = Markup(mdown.convert(file_contents))
    return markup


class YawtMarkdown(Plugin):
    """The YAWT Markdown plugin"""

    def __init__(self, app=None):
        super(YawtMarkdown, self).__init__(app)

    def init_app(self, app):
        """Sets some defaule values"""
        app.config.setdefault('YAWT_MULTIMARKDOWN_FILE_EXTENSIONS', ['md'])
        app.config.setdefault('YAWT_MULTIMARKDOWN_EXTENSIONS', [])

    def on_article_fetch(self, article):
        """when we fetch the article, we will set the attributes on the article
        according to the markdown attributes
        """
        extensions = current_app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS']
        if article.info.extension in extensions:
            markup = _load_markdown(article.content)
            article.content = markup
        return article
