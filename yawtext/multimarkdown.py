import markdown
from flask import Markup, current_app

class YawtMarkdown(object):
    def __init__(self,app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_MULTIMARKDOWN_FILE_EXTENSIONS', ['md'])
        app.config.setdefault('YAWT_MULTIMARKDOWN_EXTENSIONS', ['meta'])

    def on_article_fetch(self, article):
        if article.info.extension in current_app.config['YAWT_MULTIMARKDOWN_FILE_EXTENSIONS']:
            meta, markup = load_markdown(article.content)
            article.content = markup
            if not hasattr(article.info, 'indexed') or not article.info.indexed:
                self._set_attributes(article.info, meta)
        return article
 
    def _set_attributes(self, article_info, meta):
        for key in meta.keys():
            setattr(article_info, key, '\n'.join(meta[key]))

def load_markdown(file_contents):
    """Returns a tuple, where the first part is a dictionary of the metadata,
    and the second part is the contents of the markdown file in HTML.
    """
    md = markdown.Markdown(extensions = current_app.config['YAWT_MULTIMARKDOWN_EXTENSIONS'])
    markup = Markup(md.convert(file_contents))
    meta = {}
    if hasattr(md, 'Meta') and md.Meta is not None:
        meta = md.Meta
    return (meta, markup)

