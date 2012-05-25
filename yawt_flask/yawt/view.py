from flask import render_template, g, make_response, request, redirect, url_for

default_article_template = """<html>
    <head>
        <title>{{ article.title }}</title>
    </head>
    <body>
        <h1>{{global.blogtitle}}</h1>
        <h2>{{global.blogdescription}}</h2>
        <h1>{{ article.title }}</h1>
        <p>Posted on {{article.ctime_tm|dateformat('%Y/%m/%d %H:%M')}} at {{article.fullname}}</p>
        <p>Last modified on {{article.mtime_tm|dateformat('%Y/%m/%d %H:%M')}}</p>
        <p>{{article}}</p>
    </body>
</html>
"""

default_article_list_template = """<html>
    <head>
        <title>{{global.blogtitle}} - {{collection_title}}</title>
    </head>
    <body>
    <h1>{{global.blogtitle}}</h1>
    <h2>{{global.blogdescription}}</h2>
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

def _render(template_base, template_vars={}, flavour=None, content_type=None):
    if flavour is None:
        flavour = 'html'
    template = template_base + "." + flavour
    if (content_type is not None):
        return make_response(render_template(template, **template_vars),
                             200, None, None, content_type)
    else:
        return render_template(template, **template_vars)
        
class PagingInfo(object):
    def __init__(self, page, page_size, total_count, base_url):
        self.page_size = page_size
        self.page = page
        self.base_url = base_url
        self.start = (self.page - 1) * self.page_size
        self.end = self.start + self.page_size
        
        self.total_count = total_count
        self.total_pages = self.total_count / self.page_size
        if self.total_count % self.page_size is not 0:
            self.total_pages = self.total_pages + 1

        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1

    def url(self, page):
        return self.base_url + "?page=" + str(page)
    
    @property
    def next_url(self):
        if not self.has_next:
            return None
        return self.url(self.page + 1)
    
    @property
    def prev_url(self):
        if not self.has_prev:
            return None
        return self.url(self.page - 1)

    def __eq__(self, other):
        return self.page == other.page and \
               self.page_size == other.page_size and \
               self.total_count == other.total_count and \
               self.base_url == other.base_url
        
class YawtView(object):
    def __init__(self, plugins, metadata, content_types):
        self._plugins = plugins
        self._global_md = metadata
        self._content_types = content_types
        
    def render_missing_resource(self):
        return render_template("404.html")

    def render_article(self, flavour, article):
        template_vars = {'article': article, 'global': self._global_md}
        template_vars = self._plugins.template_vars(template_vars)
        return _render('article', template_vars, flavour, self._content_type(flavour))
    
    def render_collection(self, flavour, articles, title, page_info):
        template_vars = {'articles': articles[page_info.start:page_info.end],
                         'total_pages': page_info.total_pages,
                         'page': page_info.page,
                         'nextpage':  page_info.next_url,
                         'prevpage': page_info.prev_url,
                         'collection_title': title,
                         'global': self._global_md}
        template_vars = self._plugins.template_vars(template_vars)
        return _render('article_list', template_vars, flavour, self._content_type(flavour))

    def _content_type(self, flavour):
        return self._content_types.get(flavour, None)

class ArticleView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
            
    def dispatch_request(self, flavour, category, slug):
        article = self._store.fetch_article_by_category_slug(category, slug)
        if article is None:
            # no article by that name, but there might be a category
            fullname = category + '/' + slug
            if self._store.category_exists(fullname):
                # Normally flask handles this, but I don't think it
                # can in this case
                # Basically, we have trouble figuring out if cooking/indian/madras
                # is an article or a category
                return redirect(url_for('category_canonical', category=fullname))
            else:
                return self._yawtview.render_missing_resource()
        else:
            return self._yawtview.render_article(flavour, article)

class CategoryView(object):
    def __init__(self, store, yawtview):
        self._yawtview = yawtview
        self._store = store
        
    # Could render a category article, or if not then
    # defaults to a list of posts
    def dispatch_request(self, flavour, category,
                         page=1, page_size=10, base_url='http://localhost'):
        category_article = category + '/index'
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
        return self._yawtview.render_collection(flavour, articles, title, page_info)
                                                      
    def _category_title(self, category):
        if category is None or len(category) == 0:
            return ''
        return 'Categories - %s' % category
    
def create_article_view():
    return ArticleView(g.store, YawtView(g.plugins,
                                         g.config['metadata'],
                                         g.config['content_types']))

def create_category_view():
    return CategoryView(g.store, YawtView(g.plugins,
                                          g.config['metadata'],
                                          g.config['content_types']))
