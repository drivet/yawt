from flask import render_template, g, make_response, request
import yawt.util

class YawtView(object):
    def __init__(self):
        self._plugins = g.plugins
        self._global_md = g.yawtconfig['metadata']
        self._content_types = g.yawtconfig['content_types']
        self._page_size = g.yawtconfig['page_size']
        
        try:
            self._page = int(request.args.get('page', '1'))
        except ValueError:
            self._page = 1
        
        self._base_url = request.base_url
   
    def render_collection(self, flavour, articles, collection_title):
        template_vars = {}
        (start, end, total_pages) = self._get_range_info(articles)
        template_vars['articles'] = articles[start:end]
        template_vars['total_pages'] = total_pages
        template_vars['page'] = self._page

        if self._page < total_pages:
            print self._paged_url(self._page + 1)
            template_vars['nextpage'] = self._paged_url(self._page + 1)
            
        if self._page > 1:
            template_vars['prevpage'] = self._paged_url(self._page - 1)
        
        template_vars['collection_title'] = collection_title
        template_vars['flavour'] = flavour
        template_vars['global'] = self._global_md
        template_vars = self._collect_vars(template_vars)
        return self._render(flavour, "article_list." + flavour, template_vars)
    
    def render_article(self, flavour, article):
        template_vars = {}
        template_vars['article'] = article
        template_vars['flavour'] = flavour
        template_vars['global'] = self._global_md
        template_vars = self._collect_vars(template_vars)
        return self._render(flavour, "article." + flavour, template_vars)
          
    def handle_missing_resource(self):
        return render_template("404.html")

    def _paged_url(self, page):
        return self._base_url + "?page=" + str(page)
        
    def _get_range_info(self, articles):
        start = (self._page - 1) * self._page_size
        end = start + self._page_size
        total_pages = len(articles) / self._page_size
        if len(articles) % self._page_size is not 0:
            total_pages = total_pages + 1
        return (start, end, total_pages)
        
    def _collect_vars(self, template_vars):
        for p in self._plugins.keys():
            if yawt.util.has_method(self._plugins[p], 'template_vars'):
                template_vars[p] = self._plugins[p].template_vars()
        return template_vars
    
    def _render(self, flavour, template, template_vars):
        content_type = self._content_types.get(flavour, None)
        if (content_type is not None):
            return make_response(render_template(template, **template_vars),
                                 200, None, None, 'application/rss+xml')
        else:
            return render_template(template, **template_vars)
