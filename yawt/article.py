import os
import re
import yawt.default_templates
from yawt.utils import ensure_path, save_file, move_file, base_and_ext, load_file

def fetch_file_metadata(filename):
    sr = os.stat(filename)
    mtime = ctime = sr.st_mtime # epoch time in seconds
    return {'create_time': ctime, 'modified_time': mtime}


class ArticleInfo(object):
    def __init__(self, fullname = '', category = '', slug = '', extension = '', 
                 create_time = None, modified_time = None):
        self.fullname = fullname
        self.category = category
        self.slug = slug
        self.extension = extension
        self.create_time = create_time
        self.modified_time = modified_time

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __str__(self):
        return "<" + self.fullname + ", " + self.category + ", " + self.slug + ", " + \
               self.extension + ">"

    def __repr__(self):
        return "<" + self.fullname + ", " + self.category + ", " + self.slug + ", " + \
               self.extension + ">"


class Article(object):
    def __init__(self):
        self.info = ArticleInfo()
        self.content = ""

    def __str__(self):
        return "Article: " + str(self.info)
 
    def __repr__(self):
        return "Article: " + repr(self.info)


class FileBasedSiteManager(object):
    """The default article store. Stores articles on disk. No plugins."""

    def __init__(self, root_dir, draft_folder, content_folder, 
                 template_folder, file_extensions):
        self.root_dir = root_dir
        self.content_folder = content_folder
        self.draft_folder = draft_folder
        self.template_folder = template_folder
        self.file_extensions = file_extensions

    def initialize(self):
        if os.path.exists(self.root_dir):
            raise SiteExistsError(self.root_dir)

        ensure_path(self._content_root())
        ensure_path(self._draft_root())
        ensure_path(self._template_root())
        save_file(os.path.join(self.root_dir,'config.py'),'# put configuration here')
        self.save_template('article', 'html', yawt.default_templates.default_article_template)
        self.save_template('404', 'html', yawt.default_templates.default_404_template)

        return ['config.py', 'article.html', '404.html']
 
    def fetch_article_by_repofile(self, repofile):
        """Fetch single article info by repofile (path starting from root of
        repository). Returns None if no article exists with that name.
        """
        if not self.is_article(repofile):
            return None
        filename = os.path.join(self.root_dir, repofile)
        return self.fetch_article_by_fullname(self._file2name(filename))

    def fetch_article_by_fullname(self, fullname):
        """Fetch single article info by fullname. Returns None if no article
        exists with that name.
        """
        filename = self.fullname2file(fullname)
        if filename is None:
            return None
        return self._make_article(fullname, filename)
  
    def fetch_draft_by_name(self, draftname):
        """Fetch single article info by fullname. Returns None if no article
        exists with that name.
        """
        filename = self.draft2file(draftname)
        if filename is None:
            return None
        return self._make_article(draftname, filename)

    def fetch_article_by_category_and_slug(self, category, slug):
        """Fetches a single article by category and slug, which together
        constitues the article's fullname.  Returns None if the article
        does not exist.
        """
        return self.fetch_article_by_fullname(os.path.join(category, slug))
 
    def save_template(self, name, flavour, contents):
        save_file(self._template_ext2file(name, flavour), contents)

    def save_draft(self, draftname, extension, draft_content):
        """Takes draft content and saves it in the draft folder.  Return True if
        this is a new draft, otherwise return False.
        """
        save_file(self._draft_ext2file(draftname, extension), draft_content)

    def save_article(self, fullname, extension, article_content):
        """Takes article content and saves it in the content folder.  Return True
        if this is a new article, otherwise return False.
        """
        save_file(self._fullname_ext2file(fullname, extension), article_content)

    def publish(self, draftname, fullname):
        """Saves article, and then deletes the draft as well.
        """
        if self.exists(fullname):
            raise ArticleExistsError()

        oldfile = self.draft2file(draftname)
        ext = os.path.splitext(oldfile)[1]
        newfile = os.path.join(self._content_root(), fullname + ext)
        move_file(oldfile, newfile)
                                
    def move_article(self, oldname, newname):
        """Saves article, and deletes the article at oldname as well.
        """
        if self.exists(newname):
            raise ArticleExistsError()

        oldfile = self.fullname2file(oldname)
        ext = os.path.splitext(oldfile)[1]
        newfile = os.path.join(self._content_root(), newname + ext)
        move_file(oldfile, newfile)
 
    def move_draft(self, oldname, newname):
        """Saves draft, and deletes the article at oldname as well.
        """
        if self.draft_exists(newname):
            raise ArticleExistsError()

        oldfile = self.draft2file(oldname)
        ext = os.path.splitext(oldfile)[1]
        newfile = os.path.join(self._draft_root(), newname + ext)
        move_file(oldfile, newfile)

    def delete_draft(self, draftname):
        os.remove(self.draft2file(draftname))

    def delete_article(self, articlename):
        os.remove(self.fullname2file(articlename))

    def exists(self, fullname):
        """Return True if article exists"""
        return self.fullname2file(fullname) != None

    def draft_exists(self, name):
        """Return True if draft exists"""
        return self.draft2file(name) != None
 
    def is_category(self, fullname):
        """Return True if fullname refers to category on disk"""
        return os.path.isdir(os.path.join(self._content_root(), fullname))

    def is_article(self, repofile):
        """Return True if repofile refers to an article file"""
        prefix = self.content_folder
        if not prefix.endswith('/'):
            prefix += '/'
        return repofile.startswith(prefix)
 
    def walk(self, category=""):
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

    def _make_article(self, fullname, filename):
        info = ArticleInfo()
        info.fullname = unicode(fullname)
        info.category = unicode(os.path.dirname(fullname))
        info.slug = unicode(os.path.basename(fullname))
        info.extension =  unicode(base_and_ext(filename)[1])

        file_metadata = fetch_file_metadata(filename)
        info.create_time = file_metadata['create_time']
        info.modified_time = file_metadata['modified_time']

        article = Article()
        article.info = info
        article.content = load_file(filename)
        return article

    def _fullname_ext2file(self, fullname, ext):
        return os.path.join(self._content_root(), fullname + "." + ext)

    def _draft_ext2file(self, draftname, ext):
        return os.path.join(self._draft_root(), draftname + "." + ext)
 
    def _template_ext2file(self, templatename, ext):
        return os.path.join(self._template_root(), templatename + "." + ext)
 
    def fullname2file(self, fullname):
        """Return None if name does not exist."""
        for ext in self.file_extensions:
            filename = self._fullname_ext2file(fullname, ext)
            if os.path.isfile(filename):
                return filename
        return None

    def draft2file(self, draftname):
        """Return None if name does not exist."""
        for ext in self.file_extensions:
            filename = self._draft_ext2file(draftname, ext)
            if os.path.isfile(filename):
                return filename
        return None

    def _file2name(self, filename):
        """Take a full absolute filename (including repository root folder) and
        extract the fullname of the article
        """
        rel_filename = re.sub('^%s/' % (self._content_root()), '', filename)
        fullname = os.path.splitext(rel_filename)[0]
        return fullname
    
    def _content_root(self):
        return os.path.join(self.root_dir, self.content_folder)

    def _draft_root(self):
        return os.path.join(self.root_dir, self.draft_folder)

    def _template_root(self):
        return os.path.join(self.root_dir, self.template_folder)


class ArticleExistsError(Exception):
    pass


class SiteExistsError(Exception):
    def __init__(self, folder): 
        super(SiteExistsError, self).__init__()
        self.folder = folder
    def __str__(self):
        return repr(self.folder)
