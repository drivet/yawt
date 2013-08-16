from flask import render_template, g, make_response, request, redirect, url_for
from jinja2.loaders import BaseLoader, TemplateNotFound
import os
import re
import yawt

default_article_template = """<html>
    <head>
        <title>{{ article.title }}</title>
    </head>
    <body>
        <h1>{{config.blogtitle}}</h1>
        <h2>{{config.blogdescription}}</h2>
        <h1>{{article.title}}</h1>
        <p>Posted on {{article.ctime_tm|dateformat('%Y/%m/%d %H:%M')}} at {{article.fullname}}</p>
        <p>Last modified on {{article.mtime_tm|dateformat('%Y/%m/%d %H:%M')}}</p>
        <p>{{article}}</p>
    </body>
</html>
"""

default_article_list_template = """<html>
    <head>
        <title>{{config.blogtitle}} - {{collection_title}}</title>
    </head>
    <body>
    <h1>{{config.blogtitle}}</h1>
    <h2>{{config.blogdescription}}</h2>
    <h1>{{collection_title}}</h1>

    {% if total_pages > 1 %} 
    <p>
       {% if prevpage %} <a href="{{prevpage}}">Prev</a> {% endif %}
       Page {{page}} of {{total_pages}}
       {% if nextpage %} <a href="{{nextpage}}">Next</a> {% endif %}
    </p>
    {% endif %}

    {% for a in articles: %} 
        <h1>{{ a.title }}</h1>
        <p>Posted on {{a.ctime_tm|dateformat('%Y/%m/%d %H:%M')}} at {{a.fullname}}</p>
        <p>Last modified on {{a.mtime_tm|dateformat('%Y/%m/%d %H:%M')}}</p>
        <p>{{a}}</p>
    {% endfor %}
    </body>
</html>
"""

default_404_template = """<html>
    <head>
        <title>Not found</title>
    </head>
    <body>  
	  <p>Not found</p>
    </body>
</html>
"""

class YawtLoader(BaseLoader):
    def __init__(self, root):
        self.root = root
        
    def get_source(self, environment, template):
        (current_category, template_base) = os.path.split(template)
        template_name = template
      
        while current_category and not self._exists(template_name):
            current_category = os.path.dirname(current_category)
            template_name = _join(current_category, template_base)
            
        if not self._exists(template_name):
            raise TemplateNotFound(template)

        template_file = self._file(template_name)
        mtime = os.path.getmtime(template_file)
        with file(template_file) as f:
            source = f.read().decode('utf-8')
        return source, template_file, lambda: mtime == os.path.getmtime(template_file)

    def _file(self, template_name):
        return os.path.join(self.root, template_name)
    
    def _exists(self, template_name):
        return os.path.exists(self._file(template_name))


def _render(template_base, flavour=None, template_vars={}, content_type=None, category=""):
    template_file = _join(category, template_base)
    if flavour is None:
        flavour = 'html'
    template_file = template_file + "." + flavour
    
    if (content_type is not None):
        response = make_response(render_template(template_file, **template_vars))
        response.headers['Content-Type'] = content_type
        return response
    else:
        return render_template(template_file, **template_vars)

def _join(category, slug):
    if category:
        return category + '/' + slug
    else:
        return slug


class Page(object):
    """
    page is 1 based
    """
    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url

    @property
    def url(self):
        return self.base_url + "?page=" + str(self.page)


class PagingInfo(object):
    """
    page is 1 based.  start and end are 0 based.
    """
    def __init__(self, page, page_size, total_count, base_url):
        self.page_size = page_size
        self.page = page
        self.start = (self.page - 1) * self.page_size
        self.end = self.start + self.page_size
        
        self.total_count = total_count
        self.total_pages = self.total_count / self.page_size
        if self.total_count % self.page_size is not 0:
            self.total_pages = self.total_pages + 1

        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1
        self.multi_page = self.total_pages > 1

        self.pages = []
        for page in range(self.total_pages):
            # page here is 0 based
            self.pages.append(Page(page+1, base_url))
    
        self.page_index = self.page - 1

    def __eq__(self, other):
        return self.page == other.page and \
               self.page_size == other.page_size and \
               self.total_count == other.total_count and \
               self.base_url == other.base_url


class YawtView(object):
    """
    Collection of utility methods for rendering YAWT views
    """
    def __init__(self, plugins, content_types):
        self._plugins = plugins
        self._content_types = content_types
        
    def render_missing_resource(self):
        return render_template("404.html")

    def render_article(self, flavour, article):
        template_vars = {'article': article}
        template_vars = self._plugins.template_vars(template_vars)
        return _render('article', flavour, template_vars, self._content_type(flavour),
                       article.category)
    
    def render_collection(self, flavour, articles, title, page_info, category=''):
        template_vars = {'articles': articles[page_info.start:page_info.end],
                         'page_info': page_info,
                         'collection_title': title}
        template_vars = self._plugins.template_vars(template_vars)
        return _render('article_list', flavour, template_vars,
                       self._content_type(flavour), category)

    def _content_type(self, flavour):
        return self._content_types.get(flavour, None)

    
class ArticleView(object):
    """
    Class for rendering YAWT article views, which are views meant
    to display just one entry on your blog or site.
    """
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
            
    def dispatch_request(self, flavour, category, slug):
        article = self._store.fetch_article_by_category_slug(category, slug)
        if article is None:
            # no article by that name, but there might be a category
            fullname = _join(category, slug)
            if self._store.category_exists(fullname):
                # Normally flask handles this, but I don't think it can in this case
                # Basically, we have trouble figuring out if cooking/indian/madras
                # is an article or a category
                return redirect('/' + fullname + '/')
            else:
                return self._yawtview.render_missing_resource()
        else:
            return self._yawtview.render_article(flavour, article)


def create_article_view():
    return ArticleView(g.store, YawtView(g.plugins, yawt.util.get_content_types()))

class CategoryView(object):
    """
    Class for rendering YAWT category view, which are views meant to display
    categories, which usually have a reverse time list of articles.
    """
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    # Could render a category article, or if not then
    # defaults to a list of posts
    def dispatch_request(self, flavour, category,
                         page=1, page_size=10, base_url='http://localhost'):
        category_article = _join(category, 'index')
        if self._store.article_exists(category_article):
            article = self._store.fetch_article_by_fullname(category_article)
            # index file exists
            return self._yawtview.render_article(flavour, article)
        else:
            # no index file.  Render an article list template with
            # all the articles in the category sent to the template
            articles = self._store.fetch_articles_by_category(category)
            if len(articles) < 1:
                return self._yawtview.render_missing_resource()
            else:
                page_info = PagingInfo(page, page_size, len(articles), base_url)
                return self._render_collection(flavour, articles, category, page_info)
                
    def _render_collection(self, flavour, articles, category, page_info):
        title = self._category_title(category)
        return self._yawtview.render_collection(flavour, articles, '',
                                                page_info, category)
                                                      
    def _category_title(self, category):
        if category is None or len(category) == 0:
            return ''
        return ' :: '.join(category.split('/'))


def create_category_view():
    return CategoryView(g.store, YawtView(g.plugins, yawt.util.get_content_types()))
