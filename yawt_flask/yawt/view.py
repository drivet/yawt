from flask import render_template, g, make_response
from flask.views import View
import yawt.util

class YawtView(View):
    def __init__(self):
        self._plugins = g.plugins
        self._global_md = g.yawtconfig['metadata']
        self._content_types = g.yawtconfig['content_types']
    
    def handle_missing_resource(self):
        return render_template("404.html")
    
    def collect_vars(self, template_vars):
        for p in self._plugins.keys():
            if yawt.util.has_method(self._plugins[p], 'template_vars'):
                template_vars[p] = self._plugins[p].template_vars()
        return template_vars

    def render_collection(self, flavour, articles, title):
        template_vars = {}
        template_vars['articles'] = articles
        template_vars['title'] = title
        template_vars['flavour'] = flavour
        template_vars['global_metadata'] = self._global_md
        template_vars = self.collect_vars(template_vars)
        return self._render(flavour, "article_list." + flavour, template_vars)
    
    def render_article(self, flavour, article):
        template_vars = {}
        template_vars['article'] = article
        template_vars['flavour'] = flavour
        template_vars['global_metadata'] = self._global_md
        template_vars = self.collect_vars(template_vars)
        return self._render(flavour, "article." + flavour, template_vars)
       
    def _render(self, flavour, template, template_vars):
        content_type = self._content_types.get(flavour, None)
        if (content_type is not None):
            return make_response(render_template(template, **template_vars), 200, None, None, 'application/rss+xml')
        else:
            return render_template(template, **template_vars)
