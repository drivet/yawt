import os
import re
import time
import fnmatch
import yaml
import yawt
from werkzeug.utils import cached_property


class Article(object):
    """
    This class hold basic information about an article without actually
    reading its contents (unless you ask).

    Reads the file's metadata without asking, because this is required for
    certain computations
    """       
    def __init__(self, loader, fullname, ctime, mtime, metadata):
        """
        fullname is the category + slug of the article.
        No root path infomation.
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
    """
    interface to stored articles
    """
    def __init__(self, plugins, root_dir, ext, meta_ext):
        self._plugins = plugins
        self.root_dir = root_dir
        self.ext = ext
        self.meta_ext = meta_ext
       
    # factory method to fetch an article store
    @staticmethod
    def get(config, plugins):
        article_root = yawt.util.get_abs_path(config['blogpath'], config['path_to_articles'])
        return ArticleStore(plugins,
                            article_root,
                            config['ext'],
                            config['meta_ext'])
         
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
        
        md = self._fetch_metadata(fullname)
        times = self._get_times(fullname)
        article = Article(self, fullname, times[0], times[1], md)

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
        
    def _get_times(self, fullname):
        sr = os.stat(self._name2file(fullname))
        mtime = ctime = sr.st_mtime
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
    
    def _article_file(self, slug):
        indexfile = 'index.' + self.ext
        return fnmatch.fnmatch(slug, "*." + self.ext) and slug != indexfile
