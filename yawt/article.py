import os
import re
import time
import fnmatch
import yaml
import yawt
from werkzeug.utils import cached_property
from mercurial import hg, ui, cmdutil


class Article(object):
    """
    This class hold basic information about an article without actually
    reading its contents (unless you ask).

    Reads the file's metadata without asking, because this is required for
    certain computations
    """       
    def __init__(self, loader=None, fullname=None,
                 local_metadata={}, external_metadata={}, vc_metadata={}, file_metadata={}):
        """
        fullname is the category + slug of the article.
        No root path infomation.
        Like this: cooking/indian/madras
        """
        self._loader = loader
        self.fullname = fullname

        self._local_metadata = local_metadata
        self._external_metadata = external_metadata
        self._vc_metadata = vc_metadata
        self._file_metadata = file_metadata
        
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
        return self.get_metadata('ctime')
       
    @property
    def mtime(self):
        """
        last modified time, in seconds since the Unix epoch.
        """
        return self.get_metadata('mtime')
        
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
        
    def get_metadata(self, key, default=None):
        if key in self._local_metadata:
            return self._local_metadata[key]
        elif key in self._external_metadata:
            return self._external_metadata[key]
        elif key in self._vc_metadata:
            return self._vc_metadata[key]
        elif key in self._file_metadata:
            return self._file_metadata[key]
        else:
            return default
        
    @cached_property
    def _article_content(self):
        return self._loader.load_article(self)

    
class ArticleContent(object):
    def __init__(self, title, content):
        self.title = title
        self.content = content


class ArticleStore(object):
    """
    interface to stored articles
    """
    def __init__(self, plugins, vcstore, root_dir, ext, meta_ext):
        self._plugins = plugins
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext
        self.vcstore = vcstore
       
    # factory method to fetch an article store
    @staticmethod
    def get(config, plugins):
        article_root = yawt.util.get_abs_path(config['YAWT_BLOGPATH'],
                                              config['YAWT_PATH_TO_ARTICLES'])
        hgstore = HgStore(config['YAWT_BLOGPATH'],
                          config['YAWT_PATH_TO_ARTICLES'],
                          config['YAWT_EXT'],
                          config['YAWT_USE_UNCOMMITTED'])
        
        return ArticleStore(plugins,
                            hgstore,
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
        
        all_metadata = self._fetch_metadata(fullname)
        article = Article(self, fullname,
                          local_metadata = all_metadata[0],
                          external_metadata = all_metadata[1],
                          vc_metadata = all_metadata[2],
                          file_metadata = all_metadata[3])

        return self._plugins.on_article_fetch(article)

    def load_article(self, article):
        f = open(self._name2file(article.fullname), 'r')
        file_contents = f.read()
        f.close()

        m = re.compile('(.*)\n\n((.*\n)*(.+)?)').match(file_contents)
        if m and m.group() == file_contents:
            return ArticleContent(m.group(1).strip(), m.group(2))
        else:
            return ArticleContent('', file_contents)
      
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

    def _fetch_metadata(self, fullname):
        return (self._fetch_local_metadata(fullname),
                self._fetch_external_metadata(fullname),
                self._fetch_vc_metadata(fullname),
                self._fetch_file_metadata(fullname))

    def _fetch_local_metadata(self, fullname):
        return {}

    def _fetch_vc_metadata(self, fullname):
        vcinfo = self.vcstore.fetch_vc_info(fullname)
        return {'ctime': vcinfo[0],
                'mtime': vcinfo[1],
                'author': vcinfo[2]}
    
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
        self._revision = None # particular revision of a working directory
        self._repo = None

    def _get_revision_id(self):
        revision_id = None
        if self.use_uncommitted:
            try:
                revision_id = self._repo.branchtags()['default']
            except KeyError:
                revision_id = None
    
    def _init_repo(self):
        self.repopath = cmdutil.findrepo(self.repopath)
        if self.repopath is not None:
            self._repo = hg.repository(ui.ui(), self.repopath)
            self._revision_id = self._get_revision_id()
            self._revision = self._repo[self._revision_id]
            
    def fetch_vc_info(self, fullname):
        self._init_repo()
        if self._repo is None:
            return None

        repofile = os.path.join(self.contentpath, fullname + '.' + self.ext)
        fctx = self._revision[repofile]
        filelog = fctx.filelog()
        changesets = list(filelog)
        
        ctime = None
        author = None
        mtime = None
        if len(changesets) > 0:
            # at least one changeset
            first_changeset = self._repo[filelog.linkrev(0)]
            ctime = int(first_changeset.date()[0])
            author = first_changeset.user()
            
            last_changeset = self._repo[filelog.linkrev(len(changesets)-1)]
            mtime = int(last_changeset.date()[0])
            
        return (ctime, mtime, author)
