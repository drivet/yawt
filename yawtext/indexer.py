from flask import current_app, g
from whoosh.fields import STORED, KEYWORD, IDLIST, ID, TEXT, DATETIME
import jsonpickle
import re
import os

def _config(key):
    return current_app.config[key]

def fullname(repofile):
    content_root = _config('YAWT_CONTENT_FOLDER')
    if not repofile.startswith(content_root):
        return None
    rel_filename = re.sub('^%s/' % (content_root), '', repofile) 
    name, ext = os.path.splitext(rel_filename)
    ext = ext[1:]
    if ext not in _config('YAWT_ARTICLE_EXTENSIONS'):
        return None 
    return name


class BadFieldType(Exception):
    pass


class YawtWhoosh(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('YAWT_WHOOSH_ARTICLE_INFO_FIELDS', {'create_time': DATETIME})
        app.config.setdefault('YAWT_WHOOSH_ARTICLE_FIELDS', {'content': TEXT})
    
    def on_new_site(self, files):
        self.whoosh().init_index(self.schema())

    def on_pre_walk(self):
        self.whoosh().init_index(self.schema(), clear=True)

    def on_visit_article(self, article):
        doc = self.field_values(article)
        self.whoosh().writer.add_document(**doc)

    def on_post_walk(self):
        self.whoosh().writer.commit()

    def on_files_changed(self, files_modified, files_added, files_removed):
        for f in  files_removed + files_modified: 
            name = fullname(f)
            if name:
                self.whoosh().writer.delete_by_term('fullname', name)

        for f in files_modified + files_added:
            name = fullname(f)
            if name: 
                article = g.site.fetch_article(name)
                doc = self.field_values(article)
                self.whoosh().writer.add_document(**doc)

        self.whoosh().writer.commit()

    def search(self, query, sortedby, page, pagelen, reverse=False):
        searcher = self.whoosh().searcher
        results = searcher.search_page(query, page, pagelen, sortedby=sortedby, reverse=reverse)
        article_infos = []
        for result in results:
            article_infos.append(jsonpickle.decode(result['article_info_json']))
        return article_infos

    def schema(self):
        fields = {}
        fields.update(_config('YAWT_WHOOSH_ARTICLE_INFO_FIELDS'))
        fields.update(_config('YAWT_WHOOSH_ARTICLE_FIELDS'))
        fields['article_info_json'] = STORED
        fields['fullname'] = ID # add (or override) whatever is in config
        return fields

    def field_values(self, article):
        schema = self.schema()
        values = {}
        for field in _config('YAWT_WHOOSH_ARTICLE_FIELDS'):
            if hasattr(article, field):
                values[field] = self.value(getattr(article, field), schema[field])

        info = article.info
        for field in _config('YAWT_WHOOSH_ARTICLE_INFO_FIELDS'):
            if hasattr(info, field):
                values[field] = self.value(getattr(info, field), schema[field])
    
        values['fullname'] = article.info.fullname
        values['article_info_json'] = jsonpickle.encode(article.info)
        return values

    def value(self, field_value, field_type):
        if type(field_value) is list:
            if field_type == KEYWORD or field_type == IDLIST:
                return ','.join(field_value)
            else:
                raise BadFieldType()
        else:
            return field_value
        
    def whoosh(self):
        return current_app.extension_info[0]['whoosh']
