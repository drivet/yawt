import os
import re
import time
import fnmatch
import yaml
import markdown
import git
import yawt

from werkzeug.utils import cached_property
from collections import namedtuple
from flask import Markup, g
from mercurial import hg, ui, cmdutil

      
class MarkdownArticle(object):       
    def __init__(self, loader=None, fullname=None, ext=None,
                 external_meta={}, file_meta={}, vc_meta={}):
        """
        fullname is the catgeory + slug of the article.
        No root path infomation.
        Like this: cooking/indian/madras
        """ 
        self.fullname = fullname
        self.ext = ext
        self.file_meta = file_meta
        self.vc_meta = vc_meta
        self.external_meta = external_meta
        self._loader = loader
        
    @property
    def categorized_url(self):
        return '/' + self.fullname
    
    @property
    def category(self):
        pieces = self.fullname.rsplit('/', 1)
        if len(pieces) > 1:
            return pieces[0]
        else:
            return ''
        
    @property
    def slug(self):
        pieces = self.fullname.rsplit('/', 1)
        if len(pieces) > 1:
            return pieces[1]
        else:
            return pieces[0]

    def is_in_category(self, category):
        category.strip()

        if not category:
            return True
       
        if not category.endswith('/'):
            category += '/'
            
        return self.fullname.startswith(category)

    @property
    def ctime(self):
        """
        create time, in seconds since the Unix epoch.
        """
        return int(self.get_metadata('ctime'))
       
    @property
    def mtime(self):
        """
        last modified time, in seconds since the Unix epoch.
        """
        return int(self.get_metadata('mtime'))

    @property
    def title(self):
        """
        title of article
        """
        return self.get_metadata('title', '')

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

    def get_metadata(self, key, default=None):
        if key in self._loaded_article.meta:
            return "\n".join(self._loaded_article.meta[key])
        elif key in self.external_meta:
            return self.external_meta[key]
        elif key in self.vc_meta:
            return self.vc_meta[key]
        elif key in self.file_meta:
            return self.file_meta[key]
        else:
            return default

    @property
    def content(self):
        return self._loaded_article.content

    @cached_property
    def _loaded_article(self):
        return self._loader.load_article(self.fullname)


class MarkdownArticleLoader(object):
    def __init__(self, root_dir, ext):
        self.root_dir = root_dir
        self.ext = ext

    def load_article(self, fullname):
        f = open(self._name2file(fullname), 'r')
        file_contents = f.read()
        f.close()
        
        md = markdown.Markdown(extensions = ['meta'])
        markup = Markup(md.convert(file_contents))
        local_meta = {}
        if hasattr(md, 'Meta') and md.Meta is not None:
            local_meta = md.Meta
        LoadedArticle = namedtuple('LoadedArticle', 'meta, content')
        return LoadedArticle(local_meta, markup) 

    def _name2file(self, fullname):
        return os.path.join(self.root_dir, fullname + "." + self.ext)


class MarkdownArticleFactory(object):
    def __init__(self, root_dir, ext):
        self.root_dir = root_dir
        self.ext = ext

    def create_article(self, fullname, external_meta, file_meta, vc_meta):
        return MarkdownArticle(MarkdownArticleLoader(self.root_dir, self.ext),
                               fullname, self.ext, external_meta, file_meta, vc_meta)
       
        
class ArticleStore(object):
    """
    interface to stored articles
    """
    def __init__(self, root_dir, exts, meta_ext,
                       plugins=yawt.util.Plugins({}),
                       vcstore=None):
       
        self.plugins = plugins
        self.root_dir = root_dir
        self.exts = exts
        self.meta_ext = meta_ext
        self.vcstore = vcstore

        self.article_factories = {}

        # the extensions passed in are specifically for Markdown Articles
        for ext in self.exts:
             self.article_factories[ext] = MarkdownArticleFactory(self.root_dir, ext)
       
    def add_article_factory(self, exts, factory):
        for ext in exts:
            self.article_factories[ext] = factory

    def fetch_article_by_fullname(self, fullname):
        """
        Fetch single article info by fullname. Returns None if no article
        exists with that name.
        """
        ext = self.article_exists(fullname)
        if ext is None:
            return None
        
        factory = self.article_factories[ext]
        article = factory.create_article(fullname,
                                         self._fetch_external_metadata(fullname),
                                         self._fetch_file_metadata(fullname, ext),
                                         self._fetch_vc_metadata(fullname,ext))
        return self.plugins.on_article_fetch(article)

    def fetch_article_by_category_slug(self, category, slug):
        """
        Fetches a single article by category and slug, which together
        constitues the article's fullname.  Returns None if the article
        does not exist.
        """
        return self.fetch_article_by_fullname(os.path.join(category, slug))
    
    def fetch_articles_by_category(self, category):
        """
        Fetch collection of articles by category.  Returns article objects,
        not just fullnames.
        """
        articles = []
        for af in self.walk_articles(category):
            article = self.fetch_article_by_fullname(af)
            articles.append(article)
        return sorted(articles, key=lambda article: article.ctime, reverse=True)
 
    def fetch_article_map_by_category(self, category):
        """
        Fetch collection of articles by category.  Returns article objects,
        not just fullnames, keyed by extension
        """
        articles = self.fetch_articles_by_category(category)

        results = {}
        for article in articles:
            if article.ext not in results:
                results[article.ext] = []
            results[article.ext].append(article)

        return results

    def walk_articles(self, category=""):
        """
        Iterates over articles in category.  Yields fullnames. Note that if
        you have the same file with different extensions, this will yield
        the same fullname more than once.
        """
        start_path = os.path.join(self.root_dir, category)
        for dirpath, dirs, files in os.walk(start_path):
            for filename in self._articles_in_dirpath(dirpath, files):
                yield self._file2name(filename)

    def article_exists(self, fullname):
        """
        Return the extention of the article if it exists, otherwise return None
        """
        for ext in self.exts:
            filename = self._name2file(fullname, ext)
            if os.path.isfile(filename):
                return ext
        return None

    def category_exists(self, fullname):
        return os.path.isdir(self._name2dir(fullname))

    def _articles_in_dirpath(self, dirpath, files):
        return [os.path.abspath(os.path.join(dirpath, filename))
                for filename in files if self._article_file(filename)]

    def _name2file(self, fullname, ext):
        return os.path.join(self.root_dir, fullname + "." + ext)
 
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
        for ext in self.exts:
            indexfile = 'index.' + ext
            if fnmatch.fnmatch(slug, "*." + ext) and slug != indexfile:
                return True
        return False

    def _fetch_vc_metadata(self, fullname, ext):
        if self.vcstore is None:
            return {}
        return self.vcstore.fetch_vc_info(fullname, ext)
       
    def _fetch_file_metadata(self, fullname, ext):
        sr = os.stat(self._name2file(fullname, ext))
        mtime = ctime = sr.st_mtime
        return {'ctime': ctime, 'mtime': mtime}

    def _fetch_external_metadata(self, fullname):
        md = {}
        md_filename = self._name2metadata_file(fullname)
        if os.path.isfile(md_filename):
            f = open(md_filename, 'r')
            md = yaml.load(f)
            f.close()
        return md


def create_store(config, plugins):
    article_root = yawt.util.get_abs_path(config['YAWT_BLOGPATH'], 
                                          config['YAWT_PATH_TO_ARTICLES'])
    vcstore = _create_vc_store(config)
    return ArticleStore(article_root,
                        config['YAWT_EXT'],
                        config['YAWT_META_EXT'],
                        plugins,
                        vcstore)
    
def _create_vc_store(config): 
    blogpath = config['YAWT_BLOGPATH']
    repotype = config['YAWT_REPO_TYPE']
    vcstore = None
    if repotype is 'hg' or \
            (repotype is 'auto' and os.path.isdir(os.path.join(blogpath,'.hg'))):
        vcstore = HgStore(blogpath,
                          config['YAWT_PATH_TO_ARTICLES'],
                          config['YAWT_USE_UNCOMMITTED'])
    elif repotype is 'git' or \
            (repotype is 'auto' and os.path.isdir(os.path.join(blogpath,'.git'))):
        vcstore = GitStore(blogpath,
                           config['YAWT_PATH_TO_ARTICLES'],
                           config['YAWT_USE_UNCOMMITTED'])
    return vcstore


class HgStore(object):
    def __init__(self, repopath, contentpath, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.use_uncommitted = use_uncommitted
 
        self._revision_id = None
        self._revision = None # revision of an entire working directory, aka change ctx
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname, ext):
        self._init_repo()
        if self._repo is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + ext)
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesetcount = len(list(filelog))
        if changesetcount <= 0:
            return {}
        
        # at least one changeset
        first_changeset = self._repo[filelog.linkrev(0)]
        ctime = int(first_changeset.date()[0])
        author = first_changeset.user()
        
        last_changeset = self._repo[filelog.linkrev(changesetcount-1)]
        mtime = int(last_changeset.date()[0])
        return {'ctime': ctime, 'mtime': mtime, 'author': author}

    def _init_repo(self):
        if not self._repo_initialized:
            self.repopath = cmdutil.findrepo(self.repopath)
            if self.repopath is not None:
                self._repo = hg.repository(ui.ui(), self.repopath)
                self._revision_id = self._get_revision_id()
                self._revision = self._repo[self._revision_id]
            self._repo_initialized = True
            
    def _get_revision_id(self):
        revision_id = None
        if not self.use_uncommitted:
            try:
                revision_id = self._repo.branchtags()['default']
            except KeyError:
                revision_id = None
        return revision_id


class GitStore(object):
    def __init__(self, repopath, contentpath, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.use_uncommitted = use_uncommitted

        self._git = None
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname, ext):
        self._init_repo()
        if self._repo is None or self._git is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + ext)
        hexshas = self._git.log('--pretty=%H','--follow','--', repofile).split('\n') 
        commits = [self._repo.rev_parse(c) for c in hexshas]

        changesetcount = len(commits)
        if changesetcount <= 0:
            return {}

        # at least one changeset
        first_commit = commits[changesetcount-1]
        ctime = first_commit.committed_date
        author = first_commit.author

        last_commit = commits[0]
        mtime = last_commit.committed_date

        return {'ctime': ctime, 'mtime': mtime, 'author': author}

    def _init_repo(self):
        if not self._repo_initialized:
            self._git = git.Git(self.repopath) 
            self._repo = git.Repo(self.repopath)
            self._repo_initialized = True
