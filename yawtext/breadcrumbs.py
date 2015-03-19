"""YAWT breadcrumb extension.

This extension registers a blueprint which provides a context processor
that will provide displayable breadcrumbs template list variable
"""
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
    """The actual YAWT breadcrumbs extension class"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """register the extension on the app"""
        app.register_blueprint(breadcrumbsbp)
