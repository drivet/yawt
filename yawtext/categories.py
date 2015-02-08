from flask import current_app
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every
from yawtext.collections import CollectionView, yawtwhoosh


class CategoryView(CollectionView):
    def query(self, category):
        if category:
            qp = QueryParser('categories', schema=yawtwhoosh().schema())
            return qp.parse(unicode(category))
        else:
            return Every()

    def get_template_name(self):
        return current_app.config['YAWT_CATEGORY_TEMPLATE']


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
        if fullname != index_file and not fullname.endswith('/' + index_file):
            # this doesn't look like an index file fullname
            return False

        category = ''
        if fullname.endswith('/' + index_file):
            category = fullname.rsplit('/', 1)[0]

        view_func = CategoryView.as_view('category_path')
        return view_func(category, flavour)
