import os
import re
import time
import fnmatch
import yaml
import yawt
from werkzeug.utils import cached_property
from collections import namedtuple

from flask import Markup
import markdown

from mercurial import hg, ui, cmdutil
import git

class Article(object):       
    def __init__(self, loader=None, fullname=None):
        """
        fullname is the catgeory + slug of the article.
        No root path infomation.
        Like this: cooking/indian/madras
        """ 
        self.fullname = fullname
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
        return self._loaded_article.get_metadata(key, default)

    @property
    def content(self):
        return self._loaded_article.content

    @cached_property
    def _loaded_article(self):
        return self._loader.load_article(self.fullname)

    
class LoadedArticle(object):
    def __init__(self, local_metadata = {}, external_metadata = {}, 
                 vc_metadata = {}, file_metadata = {}, content = None):
        self.content = content

        self._local_metadata = local_metadata
        self._external_metadata = external_metadata
        self._vc_metadata = vc_metadata
        self._file_metadata = file_metadata
 
    def get_metadata(self, key, default=None):
        if key in self._local_metadata:
            return "\n".join(self._local_metadata[key])
        elif key in self._external_metadata:
            return self._external_metadata[key]
        elif key in self._vc_metadata:
            return self._vc_metadata[key]
        elif key in self._file_metadata:
            return self._file_metadata[key]
        else:
            return default

class ArticleStore(object):
    """
    interface to stored articles
    """
    def __init__(self, plugins, vcstore, root_dir, ext, meta_ext):
        self.plugins = plugins
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext
        self.vcstore = vcstore
       
    # factory method to fetch an article store
    @staticmethod
    def get(config, plugins):
        blogpath = config['YAWT_BLOGPATH']
        article_root = yawt.util.get_abs_path(blogpath,
                                              config['YAWT_PATH_TO_ARTICLES'])

        repotype = config['YAWT_REPO_TYPE']
        vcstore = None
        if repotype is 'hg' or \
                (repotype is 'auto' and os.path.isdir(os.path.join(blogpath,'.hg'))):
            vcstore = HgStore(blogpath,
                              config['YAWT_PATH_TO_ARTICLES'],
                              config['YAWT_EXT'],
                              config['YAWT_USE_UNCOMMITTED'])
        elif repotype is 'git' or \
                (repotype is 'auto' and os.path.isdir(os.path.join(blogpath,'.git'))):
            vcstore = GitStore(blogpath,
                               config['YAWT_PATH_TO_ARTICLES'],
                               config['YAWT_EXT'],
                               config['YAWT_USE_UNCOMMITTED'])
        
        return ArticleStore(plugins,
                            vcstore,
                            article_root,
                            config['YAWT_EXT'],
                            config['YAWT_META_EXT'])
         
    def fetch_articles_by_category(self, category):
        """
        Fetch collection of articles by category.
        """
        results = []
        for af in self.walk_articles(category):
            article = self.fetch_article_by_fullname(af)
            results.append(article)
        return sorted(results, key=lambda article: article.ctime, reverse=True)

    def fetch_article_by_category_slug(self, category, slug):
        """
        Fetches a single article by category and slug, which together
        constitues the article's fullname.  Returns None if the article
        does not exist.
        """
        return self.fetch_article_by_fullname(os.path.join(category, slug))

    def fetch_article_by_fullname(self, fullname):
        """
        Fetch single article info by fullname.
        Returns None if no article exists
        with that name.
        """
        filename = self._name2file(fullname)
        if not os.path.exists(filename):
            return None
        
        article = Article(self, fullname)
        return self.plugins.on_article_fetch(article)

    def load_article(self, fullname):
        f = open(self._name2file(fullname), 'r')
        file_contents = f.read()
        f.close()
        
        md = markdown.Markdown(extensions = ['meta'])
        markup = Markup(md.convert(file_contents))
        local_meta = {}
        if hasattr(md, 'Meta') and md.Meta is not None:
            local_meta = md.Meta
        return LoadedArticle(local_meta,
                             self._fetch_external_metadata(fullname), 
                             self._fetch_vc_metadata(fullname),
                             self._fetch_file_metadata(fullname),
                             markup)

    def article_exists(self, fullname):
        return os.path.isfile(self._name2file(fullname))

    def category_exists(self, fullname):
        return os.path.isdir(self._name2dir(fullname))
      
    def walk_articles(self, category=""):
        """
        iterates over articles in category.  Yields fullnames.
        """
        start_path = os.path.join(self.root_dir, category)
        for dirpath, dirs, files in os.walk(start_path):
            for filename in self._articles_in_dirpath(dirpath, files):
                yield self._file2name(filename)

    def _articles_in_dirpath(self, dirpath, files):
        return [os.path.abspath(os.path.join(dirpath, filename))
                for filename in files if self._article_file(filename)]

    def _fetch_vc_metadata(self, fullname):
        if self.vcstore is None:
            return {}
        return self.vcstore.fetch_vc_info(fullname)
       
    def _fetch_file_metadata(self, fullname):
        sr = os.stat(self._name2file(fullname))
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
        indexfile = 'index.' + self.ext
        return fnmatch.fnmatch(slug, "*." + self.ext) and slug != indexfile


class HgStore(object):
    def __init__(self, repopath, contentpath, ext, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        self.use_uncommitted = use_uncommitted
 
        self._revision_id = None
        self._revision = None # revision of an entire working directory, aka change ctx
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname):
        self._init_repo()
        if self._repo is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + self.ext)
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
    def __init__(self, repopath, contentpath, ext, use_uncommitted):
        self.repopath = repopath
        self.contentpath = contentpath
        self.ext = ext
        self.use_uncommitted = use_uncommitted

        self._git = None
        self._repo = None
        self._repo_initialized = False

    def fetch_vc_info(self, fullname):
        self._init_repo()
        if self._repo is None or self._git is None:
            return {}

        repofile = os.path.join(self.contentpath, fullname + '.' + self.ext)
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
