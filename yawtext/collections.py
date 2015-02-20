from flask import current_app, g, request, Blueprint, abort
from flask.views import View
from yawt.view import render
from jinja2 import TemplatesNotFound
from math import ceil

pagingbp = Blueprint('paging', __name__)

@pagingbp.before_app_request
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
        g.pagelen = 10
    except KeyError:
        g.pagelen = 10

class YawtPaging(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app): 
        app.register_blueprint(pagingbp)


class CollectionView(View):
    def dispatch_request(self, category='', flav=None, *args, **kwargs): 
        query = self.query(category, *args, **kwargs)
        ainfos, total = yawtwhoosh().search(query, 'create_time', g.page, g.pagelen, True)
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
    return current_app.extension_info[0]['yawtwhoosh']
