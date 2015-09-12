from __future__ import absolute_import

import jsonpickle
from datetime import datetime
from flask import current_app
from whoosh.fields import STORED, KEYWORD, IDLIST, ID, DATETIME
from whoosh.qparser import QueryParser
from whoosh.query.qcore import Every

from yawt.utils import cfg, ReprMixin


# API IMPLEMENTATION

def init_index(clear=False):
    """Initialize whoosh index, optionally clearing it"""
    _whoosh().init_index(_schema(), clear)


def add_article(article):
    """Add article to whoosh index"""
    doc = _field_values(article)
    _whoosh().writer.add_document(**doc)


def search(query_str, sortedby=None, reverse=False):
    """Search the whoosh index, using specified query string,
    returning all results"""
    searcher = _whoosh().searcher
    results = searcher.search(_query(query_str),
                              sortedby=sortedby,
                              reverse=reverse)
    return [_decode(r) for r in results]


def search_page(query_str, sortedby, page, pagelen, reverse=False):
    """Search the _whoosh index using the supplied query string Return a tuple
    of article infos, and the length of the total result
    """
    searcher = _whoosh().searcher
    results = searcher.search_page(_query(query_str),
                                   page, pagelen,
                                   sortedby=sortedby,
                                   reverse=reverse)
    return [_decode(r) for r in results], len(results)


def remove_article(fname):
    """Remove th article at fullname from whoosh index"""
    _whoosh().writer.delete_by_term('fullname', fname)


def commit():
    """Commit the whoosh index changes"""
    _whoosh().writer.commit()

# END API


def _query(query_str):
    if query_str:
        qparser = QueryParser('categories', schema=_schema())
        return qparser.parse(unicode(query_str))
    else:
        return Every()


def _decode(result):
    return jsonpickle.decode(result['article_info_json'])


def _schema():
    """returns whoosh schema for yawt articles"""
    fields = {}
    fields.update(cfg('YAWT_INDEXER_WHOOSH_INFO_FIELDS'))
    fields.update(cfg('YAWT_INDEXER_WHOOSH_FIELDS'))
    fields['article_info_json'] = STORED()
    fields['fullname'] = ID()  # add (or override) whatever is in config
    return fields


def _field_values(article):
    values = {}
    _set_values(article, cfg('YAWT_INDEXER_WHOOSH_FIELDS'), values)
    _set_values(article.info, cfg('YAWT_INDEXER_WHOOSH_INFO_FIELDS'), values)
    article.info.indexed = True
    values['fullname'] = article.info.fullname
    values['article_info_json'] = jsonpickle.encode(article.info)
    return values


def _set_values(obj, fields, values):
    sch = _schema()
    for field_name in fields:
        if hasattr(obj, field_name):
            values[field_name] = _value(getattr(obj, field_name),
                                        sch[field_name])


def _value(field_value, field_type):
    fvt = type(field_value)
    ftt = type(field_type)
    if fvt is list:
        if field_type in [KEYWORD, IDLIST] or \
           ftt in [KEYWORD, IDLIST]:
            return ' '.join(field_value)
        else:
            raise BadFieldType(field_type)
    elif fvt in [long, int, float] and ftt is DATETIME:
        return datetime.fromtimestamp(field_value)
    elif fvt is unicode and ftt is DATETIME:
        return datetime.fromtimestamp(long(field_value))
    else:
        return field_value


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


class BadFieldType(Exception, ReprMixin):
    """Simple Exception that is thrown when there is a problem mapping the
    article attribute to a whoosh datatype.
    """
    def __init__(self, field_type):
        super(BadFieldType, self).__init__()
        self.field_type = field_type
