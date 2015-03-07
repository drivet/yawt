from flask import current_app

class YawtSmartAttributes(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_SMART_ATTRIBUTES', {})

    def on_article_fetch(self, article):
        smart_attributes = current_app.config['YAWT_SMART_ATTRIBUTES']
        for smart_attr in smart_attributes:
            choices = smart_attributes[smart_attr]
            for c in choices:
                attr = getattr(article.info, c, None)
                if attr:
                    setattr(article.info, smart_attr, attr)
                    break
        return article
