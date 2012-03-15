import re
import os
import time
import fnmatch
import markdown
import yaml
from flask import Flask, render_template, url_for, redirect, Markup
from werkzeug.utils import cached_property

app = Flask(__name__)

# Article URLs
# I believe this is the only semi-ambiguous URL.  Really, it means article,
# but it can also mean category if there is no such article.
@app.route('/<path:category>/<slug>')
def post(category,slug):
    return _article(category,slug,None)

@app.route('/<path:category>/<slug>.<flav>')
def post_flav(category,slug,flav):
    return _article(category,slug,flav)

# Permalinks
@app.route('/<int:year>/<int:month>/<int:day>/<slug>')
def permalink(year,month,day,slug):
    return _permalink(year,month,day,slug,None)

@app.route('/<int:year>/<int:month>/<int:day>/<slug>.<flav>')
def permalink_flav(year, month, day, slug, flav):
    return _permalink(year, month, day, slug, flav)

# Date URLs
@app.route('/<int:year>/')
@app.route('/<int:year>/<int:month>/')
@app.route('/<int:year>/<int:month>/<int:day>/')
def archive(year,month=None,day=None):
    return _archive(year,month,day,None)

@app.route('/<int:year>/index')
@app.route('/<int:year>/<int:month>/index')
@app.route('/<int:year>/<int:month>/<int:day>/index')
def archive_index(year,month=None,day=None):
    return _archive(year,month,day,None)

@app.route('/<int:year>/index.<flav>')
@app.route('/<int:year>/<int:month>/index.<flav>')
@app.route('/<int:year>/<int:month>/<int:day>/index.<flav>')
def archive_index_flav(year,month=None,day=None,flav=None):
    return _archive(year,month,day,flav)

# Category URLs
@app.route('/')
def home():
    return _category('',None)

@app.route('/<path:category>/')
def category_canonical(category):
    return _category(category,None)
    
@app.route('/<path:category>/index')
def category_index(category):
    return _category(category,None)
    
@app.route('/<path:category>/index.<flav>')
def category_index_flav(category,flav):
    return _category(category,flav)

# filter for date and time formatting
@app.template_filter('dateformat')
def date_format(value, format='%H:%M / %d-%m-%Y'):
    return time.strftime(format, value)

class Date(object):
    def __init__(self, year, month, day):
        self.year = year;
        self.month = month
        self.day = day
        
# supposed to render one article
def _article(category, slug, flav):
    store = FileSystemArticleStore(PathSystem(),
                                   '/home/dcr/repos/desmondrivet/yawt_flask/entries',
                                   'txt', 'md')
    article = store.fetch_article_by_category_slug(category, slug)
    if article is None:
        # no article by that name, but there might be a category
        fullname = category + '/' + slug
        if store.category_exists(fullname):
            # Normally flask handles this, but I don't think it can in this case
            return redirect(url_for('category_canonical', category = fullname))
        else:
            return handleMissingResource()
    else:
        flavour = _flav(flav)
        return render_template("article." + flavour,
                               article = article,
                               category = category,
                               slug = slug,
                               permalink = False,
                               flavour = flavour)

# supposed to render one article
def _permalink(year, month, day, slug, flav):
    store = FileSystemArticleStore(PathSystem(),
                                   '/home/dcr/repos/desmondrivet/yawt_flask/entries',
                                   'txt', 'md')
    article_infos = store.fetch_dated_articles(year, month, day, slug)
    if len(article_infos) < 1:
        return handleMissingResource()
    else:
        date = Date(year, month, day)
        flavour = _flav(flav)
        article = article_infos[0]
        return render_template("article." + flavour,
                               article = article,
                               category = article.category,
                               date = date,
                               permalink = True,
                               slug = slug,
                               flavour = flavour)

# Could render a category article, or if not then
# defaults to a list of posts
def _category(category, flav):
    store = FileSystemArticleStore(PathSystem(),
                                   '/home/dcr/repos/desmondrivet/yawt_flask/entries',
                                   'txt', 'md')
    flavour = _flav(flav)
    category_article = category + '/index'
    if store.article_exists(category_article):
        # index file exists
        return render_template("article." + flavour,
                               category_article,
                               category = category,
                               date = date,
                               permalink = False,
                               slug = slug,
                               flavour = flavour)
    else:
        # no index file.  Render an article list template with
        # all the articles in the category sent to the template
        article_infos = store.fetch_articles_by_category(category)
        if len(article_infos) < 1:
            return handleMissingResource()
        else:
            return render_template("article_list." + flavour,
                                   articles = article_infos,
                                   category = category,
                                   flavour = flavour)
        
# supposed to render several articles
def _archive(year,month,day,flav):
    store = FileSystemArticleStore(PathSystem(),
                                   '/home/dcr/repos/desmondrivet/yawt_flask/entries',
                                   'txt', 'md')
    article_infos = store.fetch_dated_articles(year, month, day)
    if len(article_infos) < 1:
        return handleMissingResource()
    else:
        date = Date(year, month, day)
        flavour = _flav(flav)
        return render_template("article_list." + flavour,
                               articles = article_infos,
                               date = date,
                               flavour = flavour)

def handleMissingResource():
    return render_template("404.html")

def _flav(flav):
    if flav is None:
        return 'html'
    else:
        return flav

class PathSystem:
    """simplifies unit testing"""
    def _os_walk(self, *args):
        return os.walk(*args)

    def _os_path_isfile(self, *args):
        return os.path.isfile(*args)

    def _os_path_isdir(self, *args):
        return os.path.isdir(*args)

    def _os_path_exists(self, *args):
        return os.path.exists(*args)
    
    def _os_stat(self, *args):
        return os.stat(*args)

    def _os_path_abspath(self, *args):
        return os.path.abspath(*args)

    def _open(self, *args):
        return open(*args)

class ArticleInfo(object):
    """
    This class hold basic information about an article without actually
    reading its contents (unless you ask).

    Reads the file's metadata, because this is required for certain
    computations
    """
    def __init__(self, loader, fullname, ctime, mtime, metadata):
        """
        fullname is the category + slug of the article.  No root path infomation.
        Like this: cooking/indian/madras
        """
        self.loader = loader
        self.fullname = fullname
        self.metadata = metadata

        # Could come from:
        #   - the stat function
        #   - a DB
        #   - repository metadata
        self._mtime = mtime
        self._ctime = ctime
        
        self._mtime_tm = time.localtime(self.mtime)
        self._ctime_tm = time.localtime(self.ctime)
        
    @cached_property
    def article(self):
        return self.loader.load_article(self)
    
    @cached_property
    def category(self):
        pieces = self.fullname.rsplit('/', 2)
        return pieces[0]
    
    @cached_property
    def ctime(self):
        ctime = self._get_metadata('ctime')
        if ctime is not None:
            return int(ctime)
        else:
            return self._ctime
      
    @cached_property
    def mtime(self):
        mtime = self._get_metadata('mtime')
        if mtime is not None:
            return int(mtime)
        else:
            return self._mtime

    @cached_property
    def ctime_tm(self):
        return time.localtime(self.ctime)

    @cached_property
    def mtime_tm(self):
        return time.localtime(self.mtime)
    
    def date_match(self, year, month, day, slug):
        current_slug = os.path.split(self.fullname)[1]
        print self.ctime_tm
        return self.ctime_tm.tm_year == year and \
               (month is None or month == self.ctime_tm.tm_mon) and \
               (day is None or day == self.ctime_tm.tm_mday) and \
               (slug is None or slug == current_slug)

    def _get_metadata(self, key):
        if self.metadata is not None:
            return self.metadata.get(key, None)
        else:
            return None
    
class Article(object):
    def __init__(self, info, title, raw_content):
        self.info = info
        self.title = title
        self._raw_content = raw_content

    @cached_property
    def content(self):
        md = markdown.Markdown();
        return Markup(md.convert(self._raw_content))

class FileSystemArticleStore(object):
    def __init__(self, path_system, root_dir, ext, meta_ext):
        self.path_system = path_system
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext
    
    def fetch_dated_articles(self, year, month=None, day=None, slug=None):
        """
        Finds article infos by create time and slug.  Only year is required.
        If you specify everything, this becomes a permalink, and only
        one entry should be returned (but in a list)
        """
        results = []
        for af in self._locate_article_files(self.root_dir):
            info = self._fetch_info_by_filename(af)
            if info.date_match(year, month, day, slug):
                results.append(info)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
    
    def fetch_articles_by_category(self, category):
        """
        Fetch articles by category.  Returns a list of article infos.
        """
        results = []
        for af in self._locate_article_files(os.path.join(self.root_dir, category)):
            info = self._fetch_info_by_filename(af)
            results.append(info)
        return sorted(results, key = lambda info: info.ctime, reverse=True)
        
    def fetch_article_by_category_slug(self, category, slug):
        fullname = os.path.join(category, slug)
        return self.fetch_article_by_fullname(fullname)

    def fetch_article_by_fullname(self, fullname):
        """
        Fetch single article info by fullname.  Returns None if no article exists
        with that name or the article if it does
        """
        filename = self._name2file(fullname)
        if not self.path_system._os_path_exists(filename):
            return None
        return self._fetch_info_by_fullname(fullname)
                                   
    def load_article(self, info):
        filename = self._name2file(info.fullname)
        f = self.path_system._open(filename, 'r')
        title = f.readline().strip()
        f.readline()
        content = f.readlines()
        f.close()
        return Article(info, title, "".join(content))
    
    def article_exists(self, fullname):
        return self.path_system._os_path_isfile(self._name2file(fullname))

    def category_exists(self, fullname):
        return self.path_system._os_path_isdir(self._name2dir(fullname))

    def _fetch_info_by_fullname(self, fullname):
        md = self._fetch_metadata(fullname)
        sr = self.path_system._os_stat(self._name2file(fullname))
        return ArticleInfo(self, fullname, sr.st_mtime, sr.st_mtime, md)

    def _fetch_info_by_filename(self, filename):
        sr = self.path_system._os_stat(filename)
        fullname = self._file2name(filename)
        md = self._fetch_metadata(fullname)
        return ArticleInfo(self, fullname, sr.st_mtime, sr.st_mtime, md)

    def _fetch_metadata(self, fullname):
        md = None
        md_filename = self._name2metadata_file(fullname)
        if self.path_system._os_path_isfile(md_filename):
            f = self.path_system._open(md_filename, 'r')
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
        
    def _locate_article_files(self, root_dir):
        """
        iterates over files in root_dir.  Yields full, absolute filenames
        """
        for path, dirs, files in self.path_system._os_walk(root_dir):
            for filename in [self.path_system._os_path_abspath(os.path.join(path, filename))
                             for filename in files if fnmatch.fnmatch(filename, "*."+self.ext)]:
                yield filename
        
if __name__ == '__main__':
    app.run(debug=True)
