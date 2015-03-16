from flask import current_app, g, request, Blueprint, abort
from flask.views import View
from yawt.view import render
from jinja2 import TemplatesNotFound
from math import ceil

collectionsbp = Blueprint('paging', __name__)

@collectionsbp.before_app_request
def before_request():
    try:
        g.page = int(request.args.get('page', '1'))
    except ValueError:
        g.page = 1
    except KeyError:
        g.page = 1

    try:
        g.pagelen = int(request.args.get('pagelen', '10'))
    except ValueError:
        g.pagelen = current_app.config['YAWT_COLLECTIONS_DEFAULT_PAGELEN']
    except KeyError:
        g.pagelen = current_app.config['YAWT_COLLECTIONS_DEFAULT_PAGELEN']

class YawtCollections(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_COLLECTIONS_DEFAULT_PAGELEN', 10)
        app.config.setdefault('YAWT_COLLECTIONS_SORT_FIELD', 'create_time')
        app.register_blueprint(collectionsbp)


class CollectionView(View):
    def dispatch_request(self, category='', flav=None, *args, **kwargs): 
        query = self.query(category, *args, **kwargs)
        sortfield = current_app.config['YAWT_COLLECTIONS_SORT_FIELD']
        
        ainfos, total = yawtwhoosh().search(query=query, 
                                            sortedby=sortfield, 
                                            page=g.page, pagelen=g.pagelen, 
                                            reverse=True)
        g.total_results = total
        g.total_pages = int(ceil(float(g.total_results)/g.pagelen))
        g.has_prev_page = g.page > 1
        g.has_next_page = g.page < g.total_pages
        g.prev_page = g.page - 1
        g.next_page = g.page + 1

        try:
            return render(self.get_template_name(), category, 'index',
                          flav, {'article_infos': ainfos})
        except TemplatesNotFound:
            abort(404)

    def query(self, category, *args, **kwargs):
        """Always passed a category, and the rest varies by collection type"""
        raise NotImplementedError()

    def get_template_name(self):
        raise NotImplementedError()


def yawtwhoosh():
    return current_app.extension_info[0]['yawtext.indexer.YawtWhoosh']
