from __future__ import absolute_import

import os
from flask import current_app
import frontmatter
from yawt.utils import save_file


def _cfg(key):
    return current_app.config[key]


def _content_folder():
    return _cfg('YAWT_CONTENT_FOLDER')


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


def _add_tags_for_article(abs_article_file, searcher):
    post = frontmatter.load(abs_article_file)
    if 'tags' not in post.metadata:
        keywords = [keyword for keyword, _
                    in searcher.key_terms_from_text("content", post.content,
                                                    numterms=3)]
        keyword_str = ",".join(keywords)
        post['tags'] = keyword_str
        save_file(abs_article_file, frontmatter.dumps(post))


def _add_tags(root_dir, changed):
    searcher = _whoosh().searcher
    new_renames = []
    for old, new in changed.renamed.items():
        old_not_content = not old.startswith(_content_folder())
        new_is_content = new.startswith(_content_folder())
        if old_not_content and new_is_content:
            new_renames.append(new)

    for new_file in changed.added + new_renames:
        if new_file.startswith(_content_folder()):
            _add_tags_for_article(os.path.join(root_dir, new_file), searcher)


class YawtAutotags(object):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pass

    def on_pre_sync(self, root_dir, changed):
        """add tags to new files about to be synced"""
        _add_tags(root_dir, changed)
