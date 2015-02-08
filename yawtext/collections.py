from flask import current_app, g, request, Blueprint
from flask.views import View
from yawt.view import render

collectionsbp = Blueprint('collections', __name__)

@collectionsbp.before_request
def before_request():
    try:
        g.page = int(request.args.get('page', '1'))
    except ValueError:
        g.page = 1

    try:
        g.pagelen = int(request.args.get('pagelen', '10'))
    except ValueError:
        g.pagelen = 10

class YawtPaging(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.register_blueprint(collectionsbp)


class CollectionView(View):
    def dispatch_request(self, category, flav, *args, **kwargs):
        article_infos = yawtwhoosh().search(self.query(category, args, kwargs),
                                            'create_time', 
                                            g.page, g.pagelen, 
                                            True)
        return render(self.get_template_name(), category, 
                      flav, {'article_infos': article_infos})

    def query(self, category, *args, **kwargs):
        """Always passed a category, and the rest varies by collection type"""
        raise NotImplementedError()

    def get_template_name(self):
        raise NotImplementedError()


def yawtwhoosh():
    return current_app.extension_info[0]['yawtwhoosh']
