"""The YAWT markdown plugin

This plugin will read a markdown file and a) convert the content to HTML
and b) convert the metadata to article attributes.
"""
from __future__ import absolute_import

import markdown
from flask import Markup, current_app
import dateutil.parser


class YawtMarkdown(object):
    """The YAWT Markdown plugin"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Sets some defaule values"""
        app.config.setdefault('YAWT_MULTIMARKDOWN_FILE_EXTENSIONS', ['md'])
        app.config.setdefault('YAWT_MULTIMARKDOWN_EXTENSIONS', ['meta'])
        app.config.setdefault('YAWT_MULTIMARKDOWN_TYPES', {})

    def on_article_fetch(self, article):
        """when we fetch the article, we will set the attributes on the article
        according to the markdown attributes
        """
        extensions = current_app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS']
        if article.info.extension in extensions:
            meta, markup = load_markdown(article.content)
            article.content = markup
            if not hasattr(article.info, 'indexed') or \
               not article.info.indexed:
                self._set_attributes(article.info, meta)
        return article

    def _set_attributes(self, article_info, meta):
        for key in meta.keys():
            mtypes = current_app.config['YAWT_MULTIMARKDOWN_TYPES']
            mtype = None
            if key in mtypes:
                mtype = mtypes[key]
            setattr(article_info, key, self._convert(mtype, '\n'.join(meta[key])))

    def _convert(self, mtype, value):
        if mtype == 'list':
            return [x.strip() for x in value.split(',')]
        elif mtype == 'long':
            return long(value)
        elif mtype == 'iso8601':
            d = dateutil.parser.parse(value)
            return int(d.strftime("%s"))
        else:
            return value


def load_markdown(file_contents):
    """Returns a tuple, where the first part is a dictionary of the metadata,
    and the second part is the contents of the markdown file in HTML.
    """
    extensions = current_app.config['YAWT_MULTIMARKDOWN_EXTENSIONS']
    mdown = markdown.Markdown(extensions=extensions)
    markup = Markup(mdown.convert(file_contents))
    meta = {}
    if hasattr(mdown, 'Meta') and mdown.Meta is not None:
        meta = mdown.Meta
    return (meta, markup)
