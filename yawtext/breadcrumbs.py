from flask import request, Blueprint

breadcrumbsbp = Blueprint('breadcrumbs', __name__)

@breadcrumbsbp.app_context_processor
def breadcrumbs_cp():
    return {'breadcrumbs': _breadcrumbs(request.path)}

def _breadcrumbs(path):
    if path.startswith('/'):
        path = path[1:]        

    pathurl = ''
    breadcrumbs = []
    for piece in path.split('/'):
        pathurl += '/' + piece
        breadcrumbs.append({'crumb': piece, 'url': pathurl})
    return breadcrumbs

    
class YawtBreadcrumbs(object):
    """
    plugin is activated when path matches any re in matchpaths or
    matchpaths is empty.  If negate is True, then plugin is activately when
    path does not match any re in matchpaths.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.register_blueprint(breadcrumbsbp)
