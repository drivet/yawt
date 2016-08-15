"""Most things relating to article definitions reside here"""
import os
import re

import yawt.default_templates
from yawt.article import make_article
from yawt.utils import call_plugins, call_plugins_arg, save_file, \
    joinfile, ensure_path, base_and_ext, ReprMixin


class YawtSiteManager(object):
    """The default article store. Stores articles on disk. No plugins."""
    def __init__(self, **kwargs):
        self.root_dir = kwargs.pop('root_dir')
        self.content_folder = kwargs.get('content_folder', 'content')
        self.draft_folder = kwargs.get('draft_folder', 'drafts')
        self.template_folder = kwargs.get('template_folder', 'templates')
        self.file_extensions = kwargs.get('file_extensions')
        self.meta_types = kwargs.get('meta_types')

    def initialize(self):
        """Set up an empty blog folder"""
        if os.path.exists(self.root_dir):
            raise SiteExistsError(self.root_dir)

        ensure_path(self._content_root())
        ensure_path(self._draft_root())
        ensure_path(self._template_root())
        config_content = '# put configuration here'
        save_file(os.path.join(self.root_dir, 'config.py'), config_content)
        template_contents = yawt.default_templates.default_article_template
        self._save_template('article', 'html', template_contents)
        template_404_contents = yawt.default_templates.default_404_template
        self._save_template('404', 'html', template_404_contents)
        files = ['config.py', 'article.html', '404.html']
        return call_plugins_arg('on_new_site', files)

    def fetch_article_by_repofile(self, repofile):
        """Fetch single article info by repofile (path starting from root of
        repository). Returns None if no article exists with that name.
        """
        filename = os.path.join(self.root_dir, repofile)
        fullname = self._file2name(filename)
        if not self.exists(fullname):
            raise ArticleNotFoundError(fullname)
        article = make_article(fullname, filename, self.meta_types)
        return call_plugins_arg('on_article_fetch', article)

    def fetch_articles_by_repofiles(self, repofiles):
        """Fetches list of articles, calling plugins"""
        return [article for article in
                (self.fetch_article_by_repofile(rfile) for rfile in repofiles)
                if article]

    def fetch_article_by_info(self, article_info):
        """Fetches an article, calling all the plugins"""
        article = self._fetch_by_fullname(article_info.fullname)
        article.info = article_info
        return call_plugins_arg('on_article_fetch', article)

    def fetch_article(self, fullname):
        """Fetches an article, calling all the plugins"""
        article = self._fetch_by_fullname(fullname)
        return call_plugins_arg('on_article_fetch', article)

    def exists(self, fullname):
        """Return True if article exists"""
        return self._fullname2file(fullname) is not None

    def category_exists(self, fullname):
        """Return True if fullname refers to real, existing,
        category on disk"""
        return os.path.isdir(os.path.join(self._content_root(), fullname))

    def is_article(self, repofile):
        """Return True if repofile refers to an article file"""
        prefix = self.content_folder
        if not prefix.endswith('/'):
            prefix += '/'
        return repofile.startswith(prefix)

    def walk(self):
        """Perform a walk (i.e. visit each article in the store) and run the
        plugins to process the articles.
        """
        call_plugins('on_pre_walk')
        for fullname in self._walk():
            article = self.fetch_article(fullname)
            call_plugins('on_visit_article', article)
        call_plugins('on_post_walk')

    def _fetch_by_fullname(self, fullname):
        filename = self._fullname2file(fullname)
        if filename is None:
            raise ArticleNotFoundError(fullname)
        return make_article(fullname, filename, self.meta_types)

    def _walk(self, category=""):
        """Yields fullnames"""
        start_path = os.path.join(self._content_root(), category)
        for directory, basedirs, basefiles in os.walk(start_path):
            for filename in self._articles_in_directory(directory, basefiles):
                yield self._file2name(filename)

    def _articles_in_directory(self, directory, basefiles):
        return [os.path.abspath(os.path.join(directory, basefile))
                for basefile in basefiles if self._is_article_basefile(basefile)]

    def _is_article_basefile(self, basefile):
        base, extension = base_and_ext(basefile)
        return extension in self.file_extensions and base != 'index'

    def _fullname_ext2file(self, fullname, ext):
        return joinfile(self._content_root(), fullname, ext)

    def _template_ext2file(self, templatename, ext):
        return joinfile(self._template_root(), templatename, ext)

    def _save_template(self, name, flavour, contents):
        save_file(self._template_ext2file(name, flavour), contents)

    def _fullname2file(self, fullname):
        """Return None if name does not exist."""
        for ext in self.file_extensions:
            filename = self._fullname_ext2file(fullname, ext)
            if os.path.isfile(filename):
                return filename
        return None

    def _file2name(self, filename):
        """Take a full absolute filename (including repository root folder) and
        extract the fullname of the article
        """
        rel_filename = re.sub('^{0}/'.format(self._content_root()),
                              '', filename)
        fullname = os.path.splitext(rel_filename)[0]
        return fullname

    def _content_root(self):
        return os.path.join(self.root_dir, self.content_folder)

    def _draft_root(self):
        return os.path.join(self.root_dir, self.draft_folder)

    def _template_root(self):
        return os.path.join(self.root_dir, self.template_folder)


class SiteExistsError(Exception, ReprMixin):
    """Raised when we try to initialize a site over an existsing site"""
    def __init__(self, folder):
        super(SiteExistsError, self).__init__()
        self.folder = folder


class ArticleNotFoundError(Exception, ReprMixin):
    """Raised when we try to fetch an article that does not exist"""
    def __init__(self, fullname):
        super(ArticleNotFoundError, self).__init__()
        self.fullname = fullname
