from flask import request
import re

class BreadcrumbsPlugin(object):
    """
    plugin is activated when path matches any re in matchpaths or
    matchpaths is empty.  If negate is True, then plugin is activately when
    path does not match any re in matchpaths.
    """
    def __init__(self):
        self.default_config = { 'MATCHPATHS_RE': [], 'NEGATE': 'false'}
        self.app = None
        self.name = ""
        
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name
     
    def template_vars(self):
        negate = self._plugin_config()['NEGATE']
        matchpaths_re = self._plugin_config()['MATCHPATHS_RE']

        if len(matchpaths_re) == 0:
            return {'breadcrumbs': self._breadcrumbs()}
        elif negate:
            for matchpath in matchpaths_re:
                p = re.compile(matchpath)
                m = p.match(request.path)
                if m:
                    return {}
            return {'breadcrumbs': self._breadcrumbs()}
        else:
            for matchpath in matchpaths_re:
                p = re.compile(matchpath)
                m = p.match(request.path)
                if m:
                    return {'breadcrumbs': self._breadcrumbs()}
            return {}

    def _breadcrumbs(self):
        path = request.path

        if path.startswith('/'):
            path = path[1:]        

        pathurl = ''
        breadcrumbs = []
        for piece in path.split('/'):
            pathurl += '/' + piece
            breadcrumbs.append({'crumb': piece, 'url': pathurl})
        return breadcrumbs
    
    def _plugin_config(self):
        return self.app.config[self.name]

def create_plugin():
    return BreadcrumbsPlugin()
