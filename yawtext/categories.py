from flask import current_app, g, abort
from yawt.view import render
from jinja2 import TemplatesNotFound
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every

class YawtCategories(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_CATEGORY_TEMPLATE', 'article_collection')
 
    def on_article_fetch(self, article):
        category = article.info.category
        categories = [category]
        while('/' in category):
            category = category.rsplit('/', 1)[0]
            categories.append(category)
        article.info.categories = categories
        return article

    def on_404(self, fullname, flavour):
        """auto generate the index page if one was requested""" 
        index_file = current_app.config['YAWT_INDEX_FILE']
        if fullname != index_file and not fullname.endswith('/'+index_file):
            return False

        (page, pagelen) = self.paging_info()
        article_infos = self.yawtwhoosh().search(self.query(fullname), 
                                                 'create_time', 
                                                 page, pagelen, 
                                                 True)

        content_type = None
        if flavour in current_app.content_types:
            content_type = current_app.content_types[flavour]

        try:
            return render(fullname, flavour, {'article_infos' : article_infos}, content_type)
        except TemplatesNotFound:
            abort(404)

    def paging_info(self):
        page = 1
        if hasattr(g, 'page'):
            page = g.page 

        pagelen = 10
        if hasattr(g, 'pagelen'):
            pagelen = g.pagelen

        return (page, pagelen)

    def query(self, fullname):
        category = ''
        if '/' in fullname: 
            category = fullname.rsplit('/', 1)[0] # strip off article (index) name
        qp = QueryParser('categories', schema=self.yawtwhoosh().schema())
        if category:
            return qp.parse(unicode(category))
        else:
            return Every()
        
    def yawtwhoosh(self):
        return current_app.extension_info[0]['yawtwhoosh']
