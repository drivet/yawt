import re
import os
import time
import fnmatch
import yaml
import sys
from flask import Flask, url_for, redirect, g
from flask.views import View
from werkzeug.utils import cached_property

import yawt.util
from  yawt.view import YawtView

class ArticleView(YawtView):
    def __init__(self, store):
        super(ArticleView, self).__init__()
        self._store = store
            
    def dispatch_request(self, flavour, category, slug):
        article = self._store.fetch_article_by_category_slug(category, slug)
        if article is None:
            # no article by that name, but there might be a category
            fullname = category + '/' + slug
            if self._store.category_exists(fullname):
                # Normally flask handles this, but I don't think it can in this case
                return redirect(url_for('category_canonical', category = fullname))
            else:
                return self.handle_missing_resource()
        else:
            if flavour is None:
                flavour = 'html'
            return self.render_article(flavour, article)

class CategoryView(YawtView):
    def __init__(self, store):
        super(CategoryView, self).__init__()
        self._store = store
        
    # Could render a category article, or if not then
    # defaults to a list of posts
    def dispatch_request(self, flavour, category):
        if flavour is None:
            flavour = 'html'
        category_article = category + '/index'
        if self._store.article_exists(category_article):
            article = self._store.fetch_article_by_fullname(category_article)
            # index file exists
            return self.render_article(flavour, article)
        else:
            # no index file.  Render an article list template with
            # all the articles in the category sent to the template
            articles =  self._store.fetch_articles_by_category(category)
            if len(articles) < 1:
                return self.handle_missing_resource()
            else:
                return self.render_collection(flavour, articles, self._category_title(category))
             
    def _category_title(self, category):
        if category is None or len(category) == 0:
            return ''
        return 'Categories - %s' % category
    
class Article(object):
    """
    This class hold basic information about an article without actually
    reading its contents (unless you ask).

    Reads the file's metadata without asking, because this is required for
    certain computations
    """       
    def __init__(self, loader, fullname, ctime, mtime, metadata):
        """
        fullname is the category + slug of the article.  No root path infomation.
        Like this: cooking/indian/madras
        """
        self._loader = loader
        self.fullname = fullname
        self.metadata = metadata

        # Could come from:
        #   - the stat function
        #   - a DB
        #   - repository metadata (like mercurial)
        self._mtime = mtime
        self._ctime = ctime
  
    @property
    def category(self):
        pieces = self.fullname.rsplit('/', 2)
        if pieces > 1:
            return pieces[0]
        else:
            return ''
        
    @property
    def slug(self):
        pieces = self.fullname.rsplit('/', 2)
        if pieces > 1:
            return pieces[1]
        else:
            return pieces[0]

    @property
    def ctime(self):
        """
        create time, in seconds since the Unix epoch.
        """
        ctime = self.get_metadata('ctime')
        if ctime is not None:
            return int(ctime)
        else:
            return self._ctime
        
    @property
    def mtime(self):
        """
        last modified time, in seconds since the Unix epoch.
        """
        mtime = self.get_metadata('mtime')
        if mtime is not None:
            return int(mtime)
        else:
            return self._mtime
        
    @property
    def ctime_tm(self):
        """
        create time, in tm struct form.
        tm_year, tm_mon, tm_day.
        """
        return time.localtime(self.ctime)
    
    @property
    def mtime_tm(self):
        """
        last modified time time, in tm struct form.
        tm_year, tm_mon, tm_day.
        """
        return time.localtime(self.mtime)
    
    @property
    def title(self):
        return self._article_content.title

    @property
    def content(self):
        return self._article_content.content
      
    def get_metadata(self, key):
        if self.metadata is not None:
            return self.metadata.get(key, None)
        else:
            return None
        
    @cached_property
    def _article_content(self):
        return self._loader.load_article(self)
    
class ArticleContent(object):
    def __init__(self, title, content):
        self.title = title
        self.content = content
    
class ArticleStore(object):
    def __init__(self, plugins, root_dir, ext, meta_ext):
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext
        self.plugins = plugins

    # factory method to fetch an article store
    @staticmethod
    def get(config, plugins):
        return ArticleStore(plugins, config['path_to_articles'], config['ext'], config['meta_ext'])
    
     
    def fetch_articles_by_category(self, category):
        """
        Fetch collection of articles by category.
        """
        results = []
        for af in self.walk_articles(category):
            article = self.fetch_article_by_fullname(af)
            results.append(article)
        return sorted(results, key = lambda article: article.ctime, reverse=True)

    def fetch_article_by_category_slug(self, category, slug):
        """
        Fetches a single article by category and slug, which together
        constitues the article's fullname.  Returns None if the article
        does not exist.
        """
        fullname = os.path.join(category, slug)
        return self.fetch_article_by_fullname(fullname)

    def fetch_article_by_fullname(self, fullname):
        """
        Fetch single article info by fullname.  Returns None if no article exists
        with that name.
        """
        filename = self._name2file(fullname)
        if not os.path.exists(filename):
            return None
        
        md = self._fetch_metadata(fullname)
        times = self._get_times(fullname)
        article = Article(self, fullname, times[0], times[1], md)

        for p in self.plugins.values():
            if util.has_method(p, 'on_article_fetch'):
                article = p.on_article_fetch(article)
        return article

    def _get_times(self, fullname):
        sr = os.stat(self._name2file(fullname))
        mtime = ctime = sr.st_mtime
        return (ctime, mtime)

    def load_article(self, info):
        filename = self._name2file(info.fullname)
        f = open(filename, 'r')
        title = f.readline().strip()
        f.readline()
        content = f.readlines()
        f.close()
        return ArticleContent(title, "".join(content))

    def article_exists(self, fullname):
        return os.path.isfile(self._name2file(fullname))

    def category_exists(self, fullname):
        return os.path.isdir(self._name2dir(fullname))

    def walk_articles(self, category=""):
        """
        iterates over articles in category.  Yields fullnames.
        """
        start_path = os.path.join(self.root_dir, category)
        for path, dirs, files in os.walk(start_path):
            for filename in [os.path.abspath(os.path.join(path, filename))
                             for filename in files if self._article_file(filename)]:
                yield self._file2name(filename)
       
    def _fetch_metadata(self, fullname):
        md = None
        md_filename = self._name2metadata_file(fullname)
        if os.path.isfile(md_filename):
            f = open(md_filename, 'r')
            md = yaml.load(f)
            f.close()
        return md
    
    def _name2file(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.ext)

    def _name2metadata_file(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.meta_ext)

    def _name2dir(self, name):
        return os.path.join(self.root_dir, name)
        
    def _file2name(self, filename):
        """
        Take a full absolute filename and extract the fullname of the article
        """
        rel_filename = re.sub('^%s/' % (self.root_dir), '', filename)
        fullname = os.path.splitext(rel_filename)[0]
        return fullname
                     
    def _article_file(self, slug):
        indexfile = 'index.'+self.ext
        return fnmatch.fnmatch(slug, "*."+self.ext) and slug != indexfile

def create_app():
    app = Flask(__name__)

    f = open('config.yaml', 'r')
    app.yawtconfig = yaml.load(f)
    f.close
    
    plugin_names = {'tagging': 'yawtplugins.tagging',
                    'archiving': 'yawtplugins.archiving',
                    'search': 'yawtplugins.search',
                    'hgctime': 'yawtplugins.hgctime',
                    'markdown_c': 'yawtplugins.markdown_c'}
    plugins = {}
    for name in plugin_names:
        modname = plugin_names[name]
        mod =  __import__(modname)
        plugins[name] = sys.modules[modname]
        plugins[name].init(app)

    app.yawtplugins = plugins

    # Article URLs
    # I believe this is the only semi-ambiguous URL.  Really, it means article,
    # but it can also mean category if there is no such article.
    @app.route('/<path:category>/<slug>')
    def post(category, slug):
        return ArticleView(g.store).dispatch_request(None, category, slug)
   
    @app.route('/<path:category>/<slug>.<flav>')
    def post_flav(category, slug, flav):
        return ArticleView(g.store).dispatch_request(flav, category, slug)
    
    # Category URLs
    @app.route('/')
    def home():
        return CategoryView(g.store).dispatch_request(None, '')

    @app.route('/index')
    def home_index():
        return CategoryView(g.store).dispatch_request(None, '')

    @app.route('/index.<flav>')
    def home_index_flav(flav):
        return CategoryView(g.store).dispatch_request(flav, '')
    
    @app.route('/<path:category>/')
    def category_canonical(category):
        return CategoryView(g.store).dispatch_request(None, category)
   
    @app.route('/<path:category>/index')
    def category_index(category):
        return CategoryView(g.store).dispatch_request(None, category)
    
    @app.route('/<path:category>/index.<flav>')
    def category_index_flav(category,flav):
        return CategoryView(g.store).dispatch_request(flav, category)
 
    # filter for date and time formatting
    @app.template_filter('dateformat')
    def date_format(value, format='%H:%M / %d-%m-%Y'):
        return time.strftime(format, value)

    # filter for date and time formatting
    @app.template_filter('excerpt')
    def excerpt(article, word_count=50):
        words = article.content.split()[0:word_count]
        words.append("[...]")
        return " ".join(words)

    @app.before_request
    def before_request():
        g.yawtconfig = app.yawtconfig
        g.plugins = app.yawtplugins
        g.store = ArticleStore.get(app.yawtconfig, app.yawtplugins)

    return app
