import os

import frontmatter
from flask import current_app
from flask_script import Command, Option

from yawt.utils import save_file, content_folder, fullname
from yawtext import Plugin


def _whoosh():
    return current_app.extension_info[0]['flask_whoosh.Whoosh']


def _add_tags_for_article(repofile, searcher):
    abs_article_file = os.path.join(current_app.yawt_root_dir, repofile)
    post = frontmatter.load(abs_article_file)
    if 'tags' not in post.metadata:
        keywords = [keyword for keyword, _
                    in searcher.key_terms_from_text("content", post.content,
                                                    numterms=3)]
        keyword_str = ",".join(keywords)
        usertags = input('Enter tags (default '+keyword_str+'): ')
        tags = usertags or keyword_str
        post['tags'] = tags
        save_file(abs_article_file, frontmatter.dumps(post))


def _add_tags(changed):
    searcher = _whoosh().searcher
    for new_file in changed.content_changes().added:
        _add_tags_for_article(new_file, searcher)


# called from the Command
def _add_tags_for_indexed_article(indexed_file, edit):
    root_dir = current_app.yawt_root_dir
    if not indexed_file.startswith(content_folder()):
        print("file must be in content folder")
        return

    searcher = _whoosh().searcher
    docnums = searcher.document_numbers(fullname=fullname(indexed_file))
    keywords = [keyword for keyword, _
                in searcher.key_terms(docnums, "content", numterms=3)]
    keyword_str = ",".join(keywords)
    print("Tags: "+keyword_str)
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
        _add_tags_for_indexed_article(article, edit)


class YawtAutotags(Plugin):
    """Sync extension, allowing you to commit and optionally push"""
    def __init__(self, app=None):
        super(YawtAutotags, self).__init__(app)

    def init_app(self, app):
        pass

    def on_pre_sync(self, changed):
        """add tags to new files about to be synced"""
        _add_tags(changed)

    def on_cli_init(self, manager):
        """add the command to the CLI manager"""
        manager.add_command('autotag', Autotag())
