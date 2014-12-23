from flask import g, request, Blueprint

pagingbp = Blueprint('paging', __name__)

@pagingbp.before_request
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
        app.register_blueprint(pagingbp)
