from __future__ import absolute_import

import os
from flask import current_app, g
from flask_script import Command, Option

import frontmatter
from yawt.utils import save_file, \
    find_new_renames, content_folder, fullname
from yawtext.base import Plugin


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


def _add_tags_for_article(abs_article_file, searcher):
    post = frontmatter.load(abs_article_file)
    if 'tags' not in post.metadata:
        keywords = [keyword for keyword, _
                    in searcher.key_terms_from_text("content", post.content,
                                                    numterms=3)]
        keyword_str = ",".join(keywords)
        usertags = raw_input('Enter tags (default '+keyword_str+'): ')
        tags = usertags or keyword_str
        post['tags'] = tags
        save_file(abs_article_file, frontmatter.dumps(post))


def _add_tags(root_dir, changed):
    searcher = _whoosh().searcher
    files = changed.added + find_new_renames(changed.renamed)
    for new_file in files:
        if new_file.startswith(content_folder()):
            _add_tags_for_article(os.path.join(root_dir, new_file), searcher)


def _add_tags_for_indexed_article(root_dir, indexed_file, edit):
    if not indexed_file.startswith(content_folder()):
        print "file must be in content folder"
        return

    searcher = _whoosh().searcher
    docnums = searcher.document_numbers(fullname=fullname(indexed_file))
    keywords = [keyword for keyword, _
                in searcher.key_terms(docnums, "content", numterms=3)]
    keyword_str = ",".join(keywords)
    print "Tags: "+keyword_str
    if edit:
        abs_article_file = os.path.join(root_dir, indexed_file)
        post = frontmatter.load(abs_article_file)
        post['tags'] = keyword_str
        save_file(abs_article_file, frontmatter.dumps(post))


class Autotag(Command):
    """Autotag command"""
    def __init__(self):
        super(Autotag, self).__init__()

    def get_options(self):
        return [Option('--edit', '-e', action='store_true'),
                Option('article')]

    def run(self, edit, article):
        current_app.preprocess_request()
        _add_tags_for_indexed_article(g.site.root_dir, article, edit)


class YawtAutotags(Plugin):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        super(YawtAutotags, self).__init__(app)

    def init_app(self, app):
        pass

    def on_pre_sync(self, root_dir, changed):
        """add tags to new files about to be synced"""
        _add_tags(root_dir, changed)

    def on_cli_init(self, manager):
        """add the command to the CLI manager"""
        manager.add_command('autotag', Autotag())
