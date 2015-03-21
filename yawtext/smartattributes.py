"""YAWT smart attributes plugin.

The idea here is that we choose between known attributes; the first non-blank
on wins.  Used, for example, to pick a proper create_time, to allow for
markdown metadata to override git data.
"""
from __future__ import absolute_import

from flask import current_app

class YawtSmartAttributes(object):
    """The actual YAWT smart attributes plugin class"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """By default, there are no smart attributes"""
        app.config.setdefault('YAWT_SMART_ATTRIBUTES', {})

    def on_article_fetch(self, article):
        """When we fetch the article, we'll fill in the smart attributes"""
        smart_attributes = current_app.config['YAWT_SMART_ATTRIBUTES']
        for smart_attr in smart_attributes:
            choices = smart_attributes[smart_attr]
            for c in choices:
                attr = getattr(article.info, c, None)
                if attr:
                    setattr(article.info, smart_attr, attr)
                    break
        return article
