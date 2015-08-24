"""YAWT Indexing extension

The goal here is to index each article using Whoosh and the configured fields.
The indexing itself is done via the walk phase and the on_files_changed phase.
"""
from __future__ import absolute_import
from datetime import datetime

from flask import current_app, g
from whoosh.fields import STORED, KEYWORD, IDLIST, ID, TEXT, DATETIME
import jsonpickle

from yawt.utils import fullname, normalize_renames


def _config(key):
    return current_app.config[key]


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


def search(query, sortedby, page, pagelen, reverse=False):
    """Search the _whoosh index using the supplied query"""
    searcher = _whoosh().searcher
    results = searcher.search_page(query, page, pagelen, sortedby=sortedby,
                                   reverse=reverse)
    ainfos = []
    for result in results:
        ainfos.append(jsonpickle.decode(result['article_info_json']))
    return ainfos, len(results)


def schema():
    """returns whoosh schema for yawt articles"""
    fields = {}
    fields.update(_config('YAWT_WHOOSH_ARTICLE_INFO_FIELDS'))
    fields.update(_config('YAWT_WHOOSH_ARTICLE_FIELDS'))
    fields['article_info_json'] = STORED()
    fields['fullname'] = ID()  # add (or override) whatever is in config
    return fields


def _field_values(article):
    sch = schema()
    values = {}
    for field_name in _config('YAWT_WHOOSH_ARTICLE_FIELDS'):
        if hasattr(article, field_name):
            values[field_name] = _value(getattr(article, field_name),
                                        sch[field_name])
    info = article.info
    for field_name in _config('YAWT_WHOOSH_ARTICLE_INFO_FIELDS'):
        if hasattr(info, field_name):
            values[field_name] = _value(getattr(info, field_name),
                                        sch[field_name])

    article.info.indexed = True
    values['fullname'] = article.info.fullname
    values['article_info_json'] = jsonpickle.encode(article.info)
    return values


def _value(field_value, field_type):
    fvt = type(field_value)
    ftt = type(field_type)
    if fvt is list:
        if field_type == KEYWORD or ftt is KEYWORD or \
           field_type == IDLIST or ftt is IDLIST:
            return ' '.join(field_value)
        else:
            raise BadFieldType(field_type)
    elif (fvt is long or fvt is int or fvt is float) and ftt is DATETIME:
        return datetime.fromtimestamp(field_value)
    elif fvt is unicode and ftt is DATETIME:
        return datetime.fromtimestamp(long(field_value))
    else:
        return field_value


def update_index(added, modified, removed):
    """Delete all modified and removed files from the index.  Then index
    all the added files and re-index all the modifed files.
    """
    for f in removed + modified:
        name = fullname(f)
        if name:
            _whoosh().writer.delete_by_term('fullname', name)

    for f in modified + added:
        article = g.site.fetch_article_by_repofile(f)
        if article:
            doc = _field_values(article)
            _whoosh().writer.add_document(**doc)

    _whoosh().writer.commit()


class BadFieldType(Exception):
    """Simple Exception that is thrown when there is a problem mapping the
    article attribute to a whoosh datatype.
    """
    def __init__(self, field_type):
        super(BadFieldType, self).__init__()
        self.field_type = field_type

    def __str__(self):
        return repr(self.field_type)


class YawtWhoosh(object):
    """YAWT Whoosh extension class.  IMplement the walk and on_file_changed
    protocol.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Set up default config values.  By default we index content"""
        app.config.setdefault('YAWT_WHOOSH_ARTICLE_INFO_FIELDS', {})
        app.config.setdefault('YAWT_WHOOSH_ARTICLE_FIELDS', {'content': TEXT})

    def on_new_site(self, files):
        """Set up the index when we crate a new site"""
        _whoosh().init_index(schema())

    def on_pre_walk(self):
        """Clear the index"""
        _whoosh().init_index(schema(), clear=True)

    def on_visit_article(self, article):
        """Index this article"""
        doc = _field_values(article)
        _whoosh().writer.add_document(**doc)

    def on_post_walk(self):
        """Commit the index"""
        _whoosh().writer.commit()

    def on_files_changed(self, added, modified, deleted, renamed):
        added, modified, deleted = \
            normalize_renames(added, modified, deleted, renamed)
        update_index(added, modified, deleted)
