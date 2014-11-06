from yawt.view import handle_path
from yawt.article import Article, create_store
from flask import g, request
import re

class MediaArticle(Article):
    """
    Used to represent a media entry, like a photo, or song.
    """
    pass


class MediaArticleFactory(object):
    def __init__(self, ext):
        self.ext = ext

    def create_article(self, fullname, external_meta, file_meta, vc_meta):
        return MediaArticle(fullname, self.ext, external_meta, file_meta, vc_meta)
           
class MediaManagerPlugin(object):
    """
    """
    def __init__(self):
        self.default_config = { 'MEDIASTREAM_URL_PREFIX': '/photos',
                                'MEDIASET_URL_PREFIX': '/albums',
                                'MEDIA_PATH': 'photos', 
                                'INCLUDE_PATHS': [],
                                'EXCLUDE_PATHS': [],
                                'EXTS': ['JPG'] }
    def init(self, app, plugin_name):
        self.app = app
        self.name = plugin_name

        #config = self._plugin_config()
        #prefix = config['MEDIASTREAM_URL_PREFIX']
        #app.add_url_rule(prefix, view_func=handle_path)
        #app.add_url_rule(prefix + '/<path:path>', view_func=handle_path)
        
    def before_request(self, app): 
        config = self._plugin_config()

        pattern_str =  "^" + config['MEDIASTREAM_URL_PREFIX'] + '/.*'
        p = re.compile( "^" + config['MEDIASTREAM_URL_PREFIX'] )
        m = p.match(request.path)
        if not m:
            return

        g.config['YAWT_PATH_TO_ARTICLES'] = config['MEDIA_PATH']
        g.config['YAWT_EXT'] = config['EXTS']
        g.config['YAWT_INCLUDE_PATHS'] = config['INCLUDE_PATHS']
        g.config['YAWT_EXCLUDE_PATHS'] = config['EXCLUDE_PATHS']
        
        g.store = create_store(g.config, g.plugins)
       
        for ext in config['EXTS']:
            factory = MediaArticleFactory(ext)
            g.store.add_article_factory(ext, factory)

    def _plugin_config(self):
        return self.app.config[self.name]

def create_plugin():
    return MediaManagerPlugin()
