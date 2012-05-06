from flask import render_template, g, make_response, request, redirect, url_for
import yawt.util

class YawtView(object):
    def __init__(self):
        self._plugins = g.plugins
        self._global_md = g.config['metadata']
        self._content_types = g.config['content_types']
        self._page_size = g.config['page_size']
        
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

class ArticleView(YawtView):
    def __init__(self, store):
        super(ArticleView, self).__init__()
        self._store = store
            
    def dispatch_request(self, flavour, category, slug):
        article = self._store.fetch_article_by_category_slug(category, slug)
        if article is None:
            # no article by that name, but there might be a category
            fullname = category + '/' + slug
            if self._store.category_exists(fullname):
                # Normally flask handles this, but I don't think it
                # can in this case
                return redirect(url_for('category_canonical', category=fullname))
            else:
                return self.handle_missing_resource()
        else:
            if flavour is None:
                flavour = 'html'
            return self.render_article(flavour, article)

class CategoryView(YawtView):
    def __init__(self, store):
        super(CategoryView, self).__init__()
        self._store = store
        
    # Could render a category article, or if not then
    # defaults to a list of posts
    def dispatch_request(self, flavour, category):
        if flavour is None:
            flavour = 'html'
        category_article = category + '/index'
        if self._store.article_exists(category_article):
            article = self._store.fetch_article_by_fullname(category_article)
            # index file exists
            return self.render_article(flavour, article)
        else:
            # no index file.  Render an article list template with
            # all the articles in the category sent to the template
            articles = self._store.fetch_articles_by_category(category)
            if len(articles) < 1:
                return self.handle_missing_resource()
            else:
                return self.render_collection(flavour, articles, self._category_title(category))
             
    def _category_title(self, category):
        if category is None or len(category) == 0:
            return ''
        return 'Categories - %s' % category
