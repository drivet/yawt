import re
import os
import time
import fnmatch
import markdown
import yaml
from flask import Flask, render_template, url_for, redirect, Markup, request
from werkzeug.utils import cached_property

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser

app = Flask(__name__)

f = open('config.yaml', 'r')
config = yaml.load(f)
            
# Article URLs
# I believe this is the only semi-ambiguous URL.  Really, it means article,
# but it can also mean category if there is no such article.
@app.route('/<path:category>/<slug>')
def post(category, slug):
    return PageDispatcher(ArticleStore.get_store(), None).article(category, slug )

@app.route('/<path:category>/<slug>.<flav>')
def post_flav(category, slug, flav):
    return PageDispatcher(ArticleStore.get_store(), flav).article(category, slug )

# Permalinks
@app.route('/<int:year>/<int:month>/<int:day>/<slug>')
def permalink(year, month, day, slug):
    return PageDispatcher(ArticleStore.get_store(), None).permalink(year, month, day, slug )

@app.route('/<int:year>/<int:month>/<int:day>/<slug>.<flav>')
def permalink_flav(year, month, day, slug, flav):
    return PageDispatcher(ArticleStore.get_store(), flav).permalink(year, month, day, slug )

# Date URLs
@app.route('/<int:year>/')
@app.route('/<int:year>/<int:month>/')
@app.route('/<int:year>/<int:month>/<int:day>/')
def archive(year, month=None, day=None):
    return PageDispatcher(ArticleStore.get_store(), None).archive(year, month, day)

@app.route('/<int:year>/index')
@app.route('/<int:year>/<int:month>/index')
@app.route('/<int:year>/<int:month>/<int:day>/index')
def archive_index(year, month=None, day=None):
    return PageDispatcher(ArticleStore.get_store(), None).archive(year, month, day)

@app.route('/<int:year>/index.<flav>')
@app.route('/<int:year>/<int:month>/index.<flav>')
@app.route('/<int:year>/<int:month>/<int:day>/index.<flav>')
def archive_index_flav(year, month=None, day=None, flav=None):
    return PageDispatcher(ArticleStore.get_store(), flav).archive(year, month, day)

# Category URLs
@app.route('/')
def home():
    return PageDispatcher(ArticleStore.get_store(), None).category('')

@app.route('/<path:category>/')
def category_canonical(category):
    return PageDispatcher(ArticleStore.get_store(), None).category(category)
    
@app.route('/<path:category>/index')
def category_index(category):
    return PageDispatcher(ArticleStore.get_store(), None).category(category)
    
@app.route('/<path:category>/index.<flav>')
def category_index_flav(category,flav):
    return PageDispatcher(ArticleStore.get_store(), None).category(category)

# Tag URLs
@app.route('/tags/<tag>/')
def tag_canonical(tag):
    return PageDispatcher(ArticleStore.get_store(), None).tag(tag)

@app.route('/tags/<tag>/index')
def tag_index(tag):
    return PageDispatcher(ArticleStore.get_store(), None).tag(tag)

@app.route('/tags/<tag>/index.<flav>')
def tag_index_flav(tag, flav):
    return PageDispatcher(ArticleStore.get_store(), flav).tag(tag)

# Search URL
@app.route('/search/', methods=['POST', 'GET'])
def full_text_search():
    return _full_text_search(request, None)

@app.route('/search/index', methods=['POST', 'GET'])
def full_text_search_index():
    return _full_text_search(request,None)

@app.route('/search/index.<flav>', methods=['POST', 'GET'])
def full_text_search_index():
    return _full_text_search(request, flav)

def _full_text_search(request, flav):
    search_text = request.args.get('searchtext','')
    return PageDispatcher(ArticleStore.get_store(), flav).search(search_text)

# filter for date and time formatting
@app.template_filter('dateformat')
def date_format(value, format='%H:%M / %d-%m-%Y'):
    return time.strftime(format, value)

class Date(object):
    def __init__(self, year, month, day):
        self.year = year;
        self.month = month
        self.day = day
        
    def __str__(self):
        dl = [str(self.year)]
        if self.month is not None: dl.append(str(self.month))
        if self.day is not None: dl.append(str(self.day))
        return '/'.join(dl)

class PageDispatcher(object):
    def __init__(self, article_store, flavour):
        self._store = article_store

        self._flavour = flavour
        if self._flavour is None:
            self._flavour = 'html'

    def article(self,  category, slug):
        article = self._store.fetch_article_by_category_slug(category, slug)
        if article is None:
            # no article by that name, but there might be a category
            fullname = category + '/' + slug
            if self._store.category_exists(fullname):
                # Normally flask handles this, but I don't think it can in this case
                return redirect(url_for('category_canonical', category = fullname))
            else:
                return self._handleMissingResource()
        else:
            return self._render_article(article, False)

    def permalink(self, year, month, day, slug):
        article_infos = self._store.fetch_dated_articles(year, month, day, slug)
        if len(article_infos) < 1:
            return self._handleMissingResource()
        else:
            date = Date(year, month, day)
            article = article_infos[0]
            return self._render_article(article, True)

    # Could render a category article, or if not then
    # defaults to a list of posts
    def category(self, category):
        category_article = category + '/index'
        if self._store.article_exists(category_article):
            article = self._store.fetch_article_by_fullname(category_article)
            # index file exists
            return self._render_article(article, False)
        else:
            # no index file.  Render an article list template with
            # all the articles in the category sent to the template
            articles =  self._store.fetch_articles_by_category(category)
            if len(articles) < 1:
                return self._handleMissingResource()
            else:
                return self._render_collection(articles, self._category_title(category))

    def archive(self, year, month, day):
        articles =  self._store.fetch_dated_articles(year, month, day)
        if len(articles) < 1:
            return self._handleMissingResource()
        else:
            date = Date(year, month, day)
            return self._render_collection(articles, self._archive_title(date))
        
    def tag(self, tag):
        articles =  self._store.fetch_tagged_articles(tag)
        if len(articles) < 1:
            return self._handleMissingResource()
        else:
            return self._render_collection(articles, self._tag_title(tag))
        
    def search(self, search_text):
        articles = self._store.fetch_articles_by_text(search_text)
        if len(articles) < 1:
            return self._handleMissingResource()
        else:
            return self._render_collection(articles, self._search_title(search_text))
    
    def _archive_title(self, date):
        return 'Archives for %s' % str(date)

    def _tag_title(self, tag):
        return 'Tag: %s' % tag

    def _search_title(self, search_text):
        return 'Search results for: %s' % search_text

    def _category_title(self, category):
        if category is None or len(category) == 0:
            return ''
        return 'Category: %s' % category
        
    def _render_collection(self, articles, title):
        return render_template("article_list." + self._flavour,
                               articles = articles,
                               title = title,
                               flavour = self._flavour)

    def _render_article(self, article, permalink):
        return render_template("article." + self._flavour,
                               article = article,
                               permalink = permalink,
                               flavour = self._flavour)
    
    def _handleMissingResource(self):
        return render_template("404.html")

class Article(object):
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
    def _article_content(self):
        return self.loader.load_article(self)
    
    @cached_property
    def category(self):
        pieces = self.fullname.rsplit('/', 2)
        if pieces > 1:
            return pieces[0]
        else:
            return ''

    @cached_property
    def slug(self):
        pieces = self.fullname.rsplit('/', 2)
        if pieces > 1:
            return pieces[1]
        else:
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
    
    @cached_property
    def tags(self):
        tags = self._get_metadata('tags')
        if tags is not None:
            return ', '.join(tags)
        else:
            return ''
    
    def date_match(self, year, month, day, slug):
        current_slug = os.path.split(self.fullname)[1]
        return self.ctime_tm.tm_year == year and \
               (month is None or month == self.ctime_tm.tm_mon) and \
               (day is None or day == self.ctime_tm.tm_mday) and \
               (slug is None or slug == current_slug)

    def tag_match(self, tag):
        tags = self._get_metadata('tags')
        if tags is None:
            return False
        return tag in tags
     
    @property
    def title(self):
        return self._article_content.title

    @property
    def content(self):
        return self._article_content.content()

    def _get_metadata(self, key):
        if self.metadata is not None:
            return self.metadata.get(key, None)
        else:
            return None
    
class ArticleContent(object):
    def __init__(self, title, raw_content):
        self.title = title
        self._raw_content = raw_content

    def content(self):
        md = markdown.Markdown();
        return Markup(md.convert(self._raw_content))

class ArticleStore(object):
    def __init__(self, hg_article_store, root_dir, ext, meta_ext):
        self.hg_article_store = hg_article_store
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext

    # factory method to fetch an article store
    @staticmethod
    def get_store():
        repopath = config['repopath']
        contentpath = config['contentpath']
        path_to_articles = repopath + '/' + contentpath
        return ArticleStore(HgArticleStore(repopath, contentpath, 'txt'),
                            path_to_articles, 'txt', 'md')
     
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
    
    def fetch_tagged_articles(self, tag):
        """
        Fetch articles by tag.  Returns a list of article infos.
        """
        results = []
        for af in self._locate_article_files(os.path.join(self.root_dir)):
            info = self._fetch_info_by_filename(af)
            if info.tag_match(tag):
                results.append(info)
        return sorted(results, key = lambda info: info.ctime, reverse=True) 

    def fetch_articles_by_text(self, searchtext):
        """
        Fetch articles by searchtext.  Returns a list of article infos.
        """
        ix = open_dir("whoosh_index", indexname = 'fulltextsearch')

        search_results = None
        searcher = None
        results = []
        with ix.searcher() as searcher:
            qp = QueryParser('content', schema = ix.schema)
            q = qp.parse(unicode(searchtext))
            search_results = searcher.search(q, limit=None)    
            if search_results is not None:
                for sr in search_results:
                    article = self._fetch_info_by_fullname(sr['fullname'])
                    results.append(article)
        return results
        
    def fetch_article_by_category_slug(self, category, slug):
        fullname = os.path.join(category, slug)
        return self.fetch_article_by_fullname(fullname)

    def fetch_article_by_fullname(self, fullname):
        """
        Fetch single article info by fullname.  Returns None if no article exists
        with that name or the article if it does
        """
        filename = self._name2file(fullname)
        if not os.path.exists(filename):
            return None
        return self._fetch_info_by_fullname(fullname)
                                   
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

    def _fetch_info_by_fullname(self, fullname):
        md = self._fetch_metadata(fullname)
        times = self._get_times(fullname)
        return Article(self, fullname, times[0], times[1], md)

    def _fetch_info_by_filename(self, filename):
        fullname = self._file2name(filename)
        md = self._fetch_metadata(fullname)
        times = self._get_times(fullname) 
        return Article(self, fullname, times[0], times[1], md)

    def _get_times(self, fullname):
        sr = os.stat(self._name2file(fullname))
        mtime = sr.st_mtime
        
        hg = self.hg_article_store.fetch_hg_info(fullname)
        if hg is None or hg[0] is None:
            ctime = sr.st_mtime
        else:
            ctime = hg[0]
        return (ctime, mtime)
           
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
        
    def _locate_article_files(self, root_dir):
        """
        iterates over files in root_dir.  Yields full, absolute filenames
        """
        for path, dirs, files in os.walk(root_dir):
            for filename in [os.path.abspath(os.path.join(path, filename))
                             for filename in files if self._article_file(filename)]:
                yield filename
                
    def _article_file(self, slug):
        indexfile = 'index.'+self.ext
        return fnmatch.fnmatch(slug, "*."+self.ext) and slug != indexfile
    
from mercurial import hg, ui, cmdutil
class HgArticleStore(object):
    def __init__(self, repopath, contentpath, ext):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        
        self._revision_id = None # uncommitted stuff
        self._repo_init = False
        self._revision = None
        self._repo = None
        
    def _init_repo(self):
        if self._repo_init == False:
            self.repopath = cmdutil.findrepo(self.repopath)
            if self.repopath is not None:
                self._repo = hg.repository(ui.ui(), self.repopath)
                # whole working directory I guess, since revision_id is None?
                self._revision = self._repo[self._revision_id]
            self._repo_init = True

    def fetch_hg_info(self, fullname):
        self._init_repo()
        if self._repo is None:
            return None

        repofile = self.contentpath + '/' + fullname + '.' + self.ext
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesets = list(filelog)
        
        ctime = None
        author = None
        if len(changesets) > 0:
            # at least one changeset
            first_changeset = self._repo[filelog.linkrev(0)]
            ctime = int(first_changeset.date()[0])
            author = first_changeset.user()

        return (ctime, author)

class FullTextIndexer(object):
    def __init__(self, store, index_root, index_name, content_root):
        self._store = store
        self._index_root = index_root
        self._index_name = index_name
        self._content_root = content_root
        
    def _init_index(self):
        schema = Schema(fullname=ID(stored=True),
                        mtime=STORED,
                        title=TEXT(stored=True),
                        content=TEXT)
        
        if not os.path.exists(self._index_root):
            os.mkdir(self._index_root)

        if not exists_in(self._index_root, indexname = self._index_name):
            ix = create_in(self._index_root,
                           schema = schema,
                           indexname = self._index_name)
        else:
            ix = open_dir(self._index_root, indexname = self._index_name)
        return ix

    def clean_index(self):
        ix = self._init_index()
        writer = ix.writer()
        for af in self._store._locate_article_files(self._content_root):
            article = self._store._fetch_info_by_filename(af)
            mtime = os.path.getmtime(af)
            writer.add_document(fullname = unicode(article.fullname),
                                mtime = mtime,
                                title = unicode(article.title),
                                content = unicode(article.content))
        writer.commit()

    def incremental_index(self):
        ix = self._init_index()
        searcher = ix.searcher()
        writer = ix.writer()

        # The set of all paths in the index
        indexed_paths = set()
        
        # The set of all paths we need to re-index
        to_index = set()
        
        # Loop over the stored fields in the index
        for fields in searcher.all_stored_fields():
             indexed_name = fields['fullname']
             path = self._store._name2file(indexed_name)
             indexed_paths.add(path)
             
             if not os.path.exists(path):
                 # This file was deleted since it was indexed
                 writer.delete_by_term('fullname', indexed_name)
             else:
                 # Check if this file was changed since it
                 # was indexed
                 indexed_time = fields['mtime']
                 mtime = os.path.getmtime(path)
                 if mtime > indexed_time:
                     # The file has changed, delete it and add it to the list of
                     # files to reindex
                     writer.delete_by_term('fullname', indexed_name)
                     to_index.add(path)
        
        for af in self._store._locate_article_files(self._content_root):
            if af in to_index or af not in indexed_paths:
                # This is either a file that's changed, or a new file
                # that wasn't indexed before. So index it!
                article = self._store._fetch_info_by_filename(af)
                writer.add_document(fullname = unicode(article.fullname),
                                    mtime = mtime,
                                    title = unicode(article.title),
                                    content = unicode(article.content))
        writer.commit()
                   
if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-c", "--clean-index", action="store_true", dest="clean_index", default=False,
                      help="create/re-create index from scratch")
    parser.add_option("-i", "--incremental-index", action="store_true", dest="inc_index", default=False,
                      help="incrementally update index")
    (options, args) = parser.parse_args()
    if options.clean_index is True:
        fti = FullTextIndexer(ArticleStore.get_store(), "whoosh_index", "fulltextsearch", "entries" )
        fti.clean_index()
    elif options.inc_index is True:
        fti = FullTextIndexer(ArticleStore.get_store(), "whoosh_index", "fulltextsearch", "entries" )
        fti.incremental_index()
    else:
        app.run(debug=True)
