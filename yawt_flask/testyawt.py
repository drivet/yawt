import unittest
import yawt
import yaml
import tempfile
import shutil
import os

config = """metadata: {
    blogtitle: Desmond's Soapbox, 
    blogdescription: Musings from a Anglo-Quebecer,
    bloglang: en,
    blogurl: \"http://www.desmondrivet.net/blog\"
}

content_types: {
    rss: application/rss+xml
}

page_size: 10
path_to_articles: /tmp
path_to_templates: /tmp/templates
ext: txt
meta_ext: md
"""

# mixture of articles, meant to to test various features
# - same slug (slug_01) appears in two categories
# - two items in category_01 and the root category
# - sub category in category_02
# - two line content in slug_05
articles = [{'category': '', 'slug': 'slug_00', 'title': 'title 01', 'content': ['content 01']},
            {'category': 'category_01', 'slug': 'slug_01', 'title': 'title 02', 'content': ['content 02']},
            {'category': 'category_01', 'slug': 'slug_02', 'title': 'title 03', 'content': ['content 03']},
            {'category': 'category_02', 'slug': 'slug_01', 'title': 'title 04', 'content': ['content 04']},
            {'category': 'category_02/subcategory 02', 'slug': 'slug_03', 'title': 'title 05', 'content': ['content 05']},
            {'category': 'category_03', 'slug': 'slug_04', 'title': 'title 06', 'content': ['content 06']},
            {'category': '','slug': 'slug_05', 'title': 'title 07', 'content': ['content 07','content 07_02']},
           ]

article_list_tmpl = """{{global.blogtitle}}
{{collection_title}}
{% for a in articles: %} 
{{a.title}}
{{a.fullname}}
{{a.ctime_tm|dateformat('%Y/%m/%d %H:%M')}}
{{a.mtime_tm|dateformat('%Y/%m/%d %H:%M')}}
{{a.content}}
{% endfor %}
"""

article_tmpl = """{{article.title}}
{{article.ctime_tm|dateformat('%Y/%m/%d %H:%M')}}
{{article.fullname}}
{{article.mtime_tm|dateformat('%Y/%m/%d %H:%M')}}
{{article.content}}
"""

not_found_tmpl = """
Article not found
"""

class TestYawt(unittest.TestCase):
    def setUp(self):
        self.blog_dir = tempfile.mkdtemp()
        assert self.blog_dir.startswith('/tmp/')

        # copy templates over
        self.template_dir = os.path.join(self.blog_dir, 'templates')
        os.makedirs(self.template_dir)
        self._save_file(os.path.join(self.template_dir, 'article_list.html'), article_list_tmpl)
        self._save_file(os.path.join(self.template_dir, 'article.html'), article_tmpl)
        self._save_file(os.path.join(self.template_dir, '404.html'), not_found_tmpl)
        
        yawtconfig = yaml.load(config)
        yawtconfig['path_to_articles'] = self.blog_dir
        yawtconfig['path_to_templates'] = self.template_dir
         
        self.app = yawt.create_app(yawtconfig)
        self.app.config['DEBUG'] = True
        self.client = self.app.test_client()

    def test_empty_blog(self):
        rv = self.client.get("/")
        assert 'Article not found' in rv.data

    def test_view_single_article(self):
        ext = self.app.yawtconfig['ext']
        meta_ext = self.app.yawtconfig['meta_ext']
        self._save_blog_articles(ext, meta_ext, articles)

        rdata = self.client.get("/category_01/slug_01").data

        assert 'title 02' in rdata
        assert 'title 01' not in rdata
        assert 'title 03' not in rdata
       
    def test_view_article_list(self):
        ext = self.app.yawtconfig['ext']
        meta_ext = self.app.yawtconfig['meta_ext']
        self._save_blog_articles(ext, meta_ext, articles)
        
        rdata = self.client.get("/").data

        assert 'title 01' in rdata
        assert 'title 02' in rdata
        assert 'title 03' in rdata
        assert 'title 04' in rdata
        assert 'title 05' in rdata
        assert 'title 06' in rdata
        assert 'title 07' in rdata
        
    def _save_blog_articles(self, ext, meta_ext, articles):
        for a in articles:
            category_dir = os.path.join(self.blog_dir, a['category'])
            if not os.path.isdir(category_dir):
                os.makedirs(os.path.join(self.blog_dir, a['category']))
            filename = os.path.join(category_dir, a['slug'] + '.' + ext)
            f = open(filename, 'w')
            f.write(a['title'] + '\n\n')
            f.writelines(a['content'])
            f.close()

    def _save_file(self, filename, contents):
         f = open(filename, 'w')
         f.write(contents)
         f.close()
    
    def tearDown(self):
        assert self.blog_dir.startswith('/tmp/')
        shutil.rmtree(self.blog_dir)
        
if __name__ == '__main__':
    unittest.main()
