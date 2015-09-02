#pylint: skip-file

import unittest
import os.path
import shutil
from yawt.article import make_article
from yawt.utils import save_file


class TestArticle(unittest.TestCase):
    def test_make_article_fills_basic_info(self):
        save_file('/tmp/stuff/article_file.txt', 'blah')
        article = make_article('stuff/article_file',
                               '/tmp/stuff/article_file.txt')
        self.assertEquals('stuff/article_file', article.info.fullname)
        self.assertEquals('stuff', article.info.category)
        self.assertEquals('article_file', article.info.slug)
        self.assertEquals('txt', article.info.extension)
        self.assertEquals('blah', article.content)

    def test_make_article_loads_file_metadata(self):
        save_file('/tmp/stuff/article_file.txt', 'blah')
        article = make_article('stuff/article_file',
                               '/tmp/stuff/article_file.txt')
        self.assertTrue(isinstance(article.info.create_time, float))
        self.assertTrue(isinstance(article.info.modified_time, float))

    def test_make_article_loads_simple_metadata(self):
        article_text = """---
title: this is a title
count: 76
foo: [5, 'dd']
---

blah
"""
        save_file('/tmp/stuff/article_file.txt', article_text)
        article = make_article('stuff/article_file',
                               '/tmp/stuff/article_file.txt')
        self.assertTrue(article.info.title, 'this is a title')
        self.assertTrue(article.info.count, 76)
        self.assertTrue(article.info.foo, [5, 'dd'])

    def test_make_article_loads_list_typed_metadata(self):
        article_text = """---
tags: tag1,tag2,tag3
---

blah
"""
        save_file('/tmp/stuff/article_file.txt', article_text)
        article = make_article('stuff/article_file',
                               '/tmp/stuff/article_file.txt',
                               meta_types={'tags': 'list'})
        self.assertTrue(article.info.tags, ['tag1', 'tag2', 'tag3'])

    def test_make_article_loads_date_types_as_int(self):
        article_text = """---
date: 2015-05-16 01:52:57.906737
---

blah
"""
        save_file('/tmp/stuff/article_file.txt', article_text)
        article = make_article('stuff/article_file',
                               '/tmp/stuff/article_file.txt',
                               meta_types={'date': 'iso8601'})
        self.assertTrue(isinstance(article.info.date, int))
