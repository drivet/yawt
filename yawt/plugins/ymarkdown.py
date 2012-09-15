from flask import Markup
import markdown

class MarkdownPlugin(object):
    def init(self, app, modname):
        self.app = app
        self.name = modname
        
        @app.template_filter('markdown_content')
        def markdown_content(article):
            md = markdown.Markdown()
            return Markup(md.convert(article._article_content.content))

        @app.template_filter('markdown')
        def markdown_str(str):
            md = markdown.Markdown()
            return Markup(md.convert(str))

def create_plugin():
    return MarkdownPlugin()
