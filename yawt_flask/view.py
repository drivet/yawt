from flask import render_template, g
from flask.views import View
import util

class YawtView(View):
    def __init__(self):
        self._plugins = g.plugins
    
    def handle_missing_resource(self):
        return render_template("404.html")
    
    def collect_vars(self, template_vars):
        for p in self._plugins.keys():
            if util.has_method(self._plugins[p], 'template_vars'):
                template_vars[p] = self._plugins[p].template_vars()
        return template_vars

    def render_collection(self, flavour, articles, title):
        template_vars = {}
        template_vars['articles'] = articles
        template_vars['title'] = title
        template_vars['flavour'] = flavour
        template_vars = self.collect_vars(template_vars)
        return render_template("article_list." + flavour, **template_vars)

    def render_article(self, flavour, article):
        template_vars = {}
        template_vars['article'] = article
        template_vars['flavour'] = flavour
        template_vars = self.collect_vars(template_vars)
        return render_template("article." + flavour, **template_vars)
