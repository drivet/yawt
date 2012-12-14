import unittest
import yawt
import yaml
import tempfile
import shutil
import os

config = """
YAWT_LANG: en,
YAWT_BASE_URL: "http://www.desmondrivet.net/blog"
YAWT_PAGE_SIZE: 10
YAWT_PATH_TO_ARTICLES: content
YAWT_PATH_TO_TEMPLATES: templates
YAWT_PATH_TO_STATIC: static
YAWT_STATIC_URL: /static
YAWT_EXT: txt
YAWT_META_EXT: md
YAWT_CONTENT_TYPES_RSS: "application/rss+xml"
"""

# mixture of articles, meant to to test various features
# - same slug (slug_01) appears in two categories
# - two items in category_01 and the root category
# - sub category in category_02
# - two line content in slug_05
articles = [{'category': '',
             'slug': 'slug_00',
             'title': 'title 01',
             'ctime': 0,
             'content': ['content 01']},
            
            {'category': '',
             'slug': 'slug_05',
             'title': 'title 07',
             'ctime': 3,
             'content': ['content 07', 'content 07_02']},
            
            {'category': 'category_01',
             'slug': 'slug_01',
             'title': 'title 02',
             'ctime': 4,
             'content': ['content 02']},
            
            {'category': 'category_01',
             'slug': 'slug_02',
             'title': 'title 03',
             'ctime': 7,
             'content': ['content 03']},
            
            {'category': 'category_02',
             'slug': 'slug_01',
             'title': 'title 04',
             'ctime': 1,
             'content': ['content 04']},
            
            {'category': 'category_02/subcategory 02',
             'slug': 'slug_03',
             'title': 'title 05',
             'ctime': 6,
             'content': ['content 05']},
            
            {'category': 'category_03',
             'slug': 'slug_04',
             'title': 'title 06',
             'ctime': 2,
             'content': ['content 06']},
            
            {'category': 'category_04',
             'slug': 'index',
             'title': 'title 08',
             'ctime': 5,
             'content': ['content 08']},
           ]

article_list_tmpl = """
type: COLLECTION
collection_title: {{collection_title}}
articles: {% for a in articles: %}
-
    fullname: {{a.fullname}}
    title: {{a.title}}
    ctime: {{a.ctime}}
    mtime: {{a.mtime}}
    content: {{a.content}}
{% endfor %}
"""

article_tmpl = """
type: ARTICLE
fullname: {{article.fullname}}
title: {{article.title}}
ctime: {{article.ctime}}
mtime: {{article.mtime}}
content: {{article.content}}
"""

not_found_tmpl = """
Article not found
"""

article_list_tmpl_flav1 = """
type: COLLECTION_FLAV1
collection_title: {{collection_title}}
articles: {% for a in articles: %}
-
    fullname: {{a.fullname}}
    title: {{a.title}}
    ctime: {{a.ctime}}
    mtime: {{a.mtime}}
    content: {{a.content}}
{% endfor %}
"""

article_tmpl_flav1 = """
type: ARTICLE_FLAV1
fullname: {{article.fullname}}
title: {{article.title}}
ctime: {{article.ctime}}
mtime: {{article.mtime}}
content: {{article.content}}
"""

not_found_tmpl_flav1 = """
Article not found (flav1)
"""

def load_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.load(f)

class TestYawt(unittest.TestCase):
    def setUp(self):
        self.blog_dir = tempfile.mkdtemp()
        assert self.blog_dir.startswith('/tmp/')

        # copy config over
        self._save_file(os.path.join(self.blog_dir, 'config.yaml'), config)
            
        # copy templates over
        self.template_dir = os.path.join(self.blog_dir, 'templates')
        os.makedirs(self.template_dir)
        self._save_file(os.path.join(self.template_dir, 'article_list.html'), article_list_tmpl)
        self._save_file(os.path.join(self.template_dir, 'article.html'), article_tmpl)
        self._save_file(os.path.join(self.template_dir, '404.html'), not_found_tmpl)

        self._save_file(os.path.join(self.template_dir, 'article_list.flav1'), article_list_tmpl_flav1)
        self._save_file(os.path.join(self.template_dir, 'article.flav1'), article_tmpl_flav1)
        self._save_file(os.path.join(self.template_dir, '404.flav1'), not_found_tmpl_flav1)
        
        self.app = yawt.create_app(self.blog_dir)
        self.app.config['DEBUG'] = True
        self.app.config['YAWT_BLOGPATH'] = self.blog_dir
        self.client = self.app.test_client()

    def test_empty_blog(self):
        rv = self.client.get("/")
        assert 'Article not found' in rv.data
              
    def test_categorized_single_article(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("/category_01/slug_01").data
        self.assertArticle(rdata, {'type': 'ARTICLE', 'title': 'title 02'})
              
    def test_uncategorized_single_article(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("slug_05").data
        self.assertArticle(rdata, {'type': 'ARTICLE', 'title': 'title 07'})
        
    def test_uncategorized_single_article_with_flavour(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("slug_05.flav1").data
        self.assertArticle(rdata, {'type': 'ARTICLE_FLAV1', 'title': 'title 07'})
    
    def test_root(self):
        self._save_blog_articles(articles)
        rdata = self.client.get('/').data
        self.assertCollection(rdata, 'COLLECTION', 'title',
                              'title 03', 'title 05', 'title 02', 'title 07',
                              'title 06', 'title 04', 'title 01')
        
    def test_root_index(self):
        self._save_blog_articles(articles)
        rdata = self.client.get('/index').data
        self.assertCollection(rdata, 'COLLECTION', 'title',
                              'title 03', 'title 05', 'title 02', 'title 07',
                              'title 06', 'title 04', 'title 01')
 
    def test_root_index_with_flavour(self):
        self._save_blog_articles(articles) 
        rdata = self.client.get('/index.flav1').data
        self.assertCollection(rdata, 'COLLECTION_FLAV1', 'title',
                              'title 03', 'title 05', 'title 02', 'title 07',
                              'title 06', 'title 04', 'title 01')
        
    def test_category(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("/category_01/").data
        self.assertCollection(rdata, 'COLLECTION', 'title', 'title 03', 'title 02')
        rdata = self.client.get("/category_01/index").data
        self.assertCollection(rdata, 'COLLECTION', 'title', 'title 03', 'title 02')
      
    def test_category_with_flavour(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("/category_01/index.flav1").data
        self.assertCollection(rdata, 'COLLECTION_FLAV1', 'title', 'title 03', 'title 02')
        
    def test_category_with_index_file(self):
        self._save_blog_articles(articles)
        
        rdata = self.client.get("/category_04/index").data
        self.assertArticle(rdata, {'type': 'ARTICLE', 'title': 'title 08'})
       
        rdata = self.client.get("/category_04/").data
        self.assertArticle(rdata, {'type': 'ARTICLE', 'title': 'title 08'})

    def test_category_with_index_file_and_flavour(self):
        self._save_blog_articles(articles)
        rdata = self.client.get("/category_04/index.flav1").data
        self.assertArticle(rdata, {'type': 'ARTICLE_FLAV1', 'title': 'title 08'})
   
    def _save_blog_articles(self, articles):
        ext = self.app.config['YAWT_EXT']
        meta_ext = self.app.config['YAWT_META_EXT']
        content_path = self.app.config['YAWT_PATH_TO_ARTICLES']
        
        for a in articles:
            category_dir = os.path.join(self.blog_dir, content_path, a['category'])
            if not os.path.isdir(category_dir):
                os.makedirs(category_dir)
            filename = os.path.join(category_dir, a['slug'] + '.' + ext)
            f = open(filename, 'w')
            f.write(a['title'] + '\n\n')
            f.writelines(a['content'])
            f.close()

            filename = os.path.join(category_dir, a['slug'] + '.' + meta_ext)
            f = open(filename, 'w')
            f.write('ctime: ' + str(a['ctime']))
            f.close()

    def _save_file(self, filename, contents):
        f = open(filename, 'w')
        f.write(contents)
        f.close()
        
    def assertCollection(self, rdata, type, field, *args):
        ydata = yaml.load(rdata)
        self.assertEquals(ydata['type'], type)
        self.assertEquals(len(ydata['articles']), len(args))
        self.assertEquals([a[field] for a in ydata['articles']], list(args))
        
    def assertArticle(self, rdata, fields):
        ydata = yaml.load(rdata)
        for k in fields.keys():
            self.assertEquals(ydata[k], fields[k])
            
    def tearDown(self):
        assert self.blog_dir.startswith('/tmp/')
        shutil.rmtree(self.blog_dir)
        
if __name__ == '__main__':
    unittest.main()
