from flask import Markup
import markdown

def init(app):
    @app.template_filter('markdown_content')
    def markdown_content(article):
        md = markdown.Markdown()
        return Markup(md.convert(article._article_content.content))

    @app.template_filter('markdown')
    def markdown_str(str):
        md = markdown.Markdown()
        return Markup(md.convert(str))
