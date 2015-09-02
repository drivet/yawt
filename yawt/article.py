"""Most things relating to article definitions reside here"""
from __future__ import absolute_import

import os

import frontmatter
import pytz

from yawt.utils import base_and_ext, ReprMixin, EqMixin
from datetime import datetime


def _set_attributes(article_info, meta, meta_types):
    for key in meta.keys():
        mtype = None
        if key in meta_types:
            mtype = meta_types[key]
        setattr(article_info, key, _convert(mtype, meta[key]))


def _convert(mtype, value):
    if mtype == 'list':
        return [unicode(x.strip()) for x in value.split(',')]
    elif mtype == 'iso8601':
        epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
        return int((value-epoch).total_seconds())
    else:
        return unicode(value)


def _load_post(filename, article, meta_types):
    post = frontmatter.load(filename)
    for key in post.keys():
        if isinstance(post[key], datetime) and not post[key].tzinfo:
            # no timezone means UTC
            post[key] = pytz.utc.localize(post[key])
    article.content = post.content
    _set_attributes(article.info, post.metadata, meta_types)


def _fetch_file_metadata(filename):
    stat = os.stat(filename)
    mtime = ctime = stat.st_mtime  # epoch time in seconds
    return {'create_time': ctime, 'modified_time': mtime}


def make_article(fullname, filename, meta_types=None):
    """Construct an Article instance.  Fullname and filename are
    self-evident.  Metatypes directs how to convert certain pieces
    of metadata"""
    info = ArticleInfo()
    info.fullname = unicode(fullname)
    info.category = unicode(os.path.dirname(fullname))
    info.slug = unicode(os.path.basename(fullname))
    info.extension = unicode(base_and_ext(filename)[1])

    file_metadata = _fetch_file_metadata(filename)
    info.create_time = file_metadata['create_time']
    info.modified_time = file_metadata['modified_time']

    article = Article()
    article.info = info
    _load_post(filename, article, meta_types or {})
    return article


class ArticleInfo(ReprMixin, EqMixin):
    """Basically an Article header.  Carries information about the article
    without the content
    """
    def __init__(self, **kwargs):
        self.fullname = kwargs.get('fullname', '')
        self.category = kwargs.get('category', '')
        self.slug = kwargs.get('slug', '')
        self.extension = kwargs.get('extension', '')
        self.create_time = kwargs.get('create_time')
        self.modified_time = kwargs.get('modified_time')

    def under(self, base):
        """Return True if the article is filed under base"""
        return self.fullname.startswith(base)


class Article(ReprMixin, EqMixin):
    """The main article class, basically just conbining an info instance and
    content
    """
    def __init__(self):
        self.info = ArticleInfo()
        self.content = ""
