import os
import re

class ArticleInfo(object):
    def __init__(self):
        self.fullname = "" 
        self.category = "" 
        self.slug = ""
        self.extension = ""
        self.create_time = None
        self.modified_time = None


class Article(object):
    def __init__(self):
        self.info = ArticleInfo()
        self.content = ""


class FileBasedSiteManager(object):
    """The default article store.  Stores articles on disk. """

    def __init__(self, root_dir, file_extensions):
        self.root_dir = root_dir
        self.file_extensions = file_extensions

    def fetch_article_by_fullname(self, fullname):
        """Fetch single article info by fullname. Returns None if no article
        exists with that name.
        """
        filename = self._name2file(fullname)
        if filename is None:
            return None

        return self._make_article(fullname, filename)

    def fetch_article_by_category_and_slug(self, category, slug):
        """Fetches a single article by category and slug, which together
        constitues the article's fullname.  Returns None if the article
        does not exist.
        """
        return self.fetch_article_by_fullname(os.path.join(category, slug))

    def save_draft(self, article):
        """Takes an article instance and saves it in the draft folder.
        Return True if this is a new draft, otherwise return False.
        """
        pass

    def save_article(self, article):
        """Takes an article instance and saves it in the content folder.
        Return True if this is a new article, otherwise return False.
        """
        pass

    def publish(self, draft_name):
        """Moves a draft to the content folder
        """
        pass
    
    def exists(self, fullname):
        """Return True if article exists"""
        return self._name2file(fullname) != None
 
    def is_category(self, fullname):
        """Return True if fullname refers to category on disk"""
        return os.path.isdir(os.path.join(self.root_dir, fullname))

    def walk(self, category=""):
        """Yields fullnames. """
        start_path = os.path.join(self.root_dir, category)
        for directory, basedirs, basefiles in os.walk(start_path):
            for filename in self._articles_in_directory(directory, basefiles):
                yield self._file2name(filename)


    def _articles_in_directory(self, directory, basefiles):
        return [os.path.abspath(os.path.join(directory, basefile))
                for basefile in basefiles if self._is_article_basefile(basefile)]

    def _is_article_basefile(self, basefile):
        base, extension = _base_and_ext(basefile)
        return extension in self.file_extensions and base != 'index'

    def _make_article(self, fullname, filename):
        info = ArticleInfo()
        info.fullname = fullname
        info.category = os.path.dirname(fullname)
        info.slug = os.path.basename(fullname)
        info.extension =  _base_and_ext(filename)[1]

        file_metadata = fetch_file_metadata(filename)
        info.create_time = file_metadata['create_time']
        info.modified_time = file_metadata['modified_time']

        article = Article()
        article.info = info
        article.content = load_file(filename)
        return article

    def _name_ext2file(self, fullname, ext):
        return os.path.join(self.root_dir, fullname + "." + ext)
 
    def _name2file(self, fullname):
        """Return None if name does not exist."""
        for ext in self.file_extensions:
            filename = self._name_ext2file(fullname, ext)
            if os.path.isfile(filename):
                return filename
        return None

    def _file2name(self, filename):
        """
        Take a full absolute filename and extract the fullname of the article
        """
        rel_filename = re.sub('^%s/' % (self.root_dir), '', filename)
        fullname = os.path.splitext(rel_filename)[0]
        return fullname


def load_file(filename):
    f = open(filename, 'r')
    file_contents = f.read()
    f.close()
    return file_contents

def fetch_file_metadata(filename):
    sr = os.stat(filename)
    mtime = ctime = sr.st_mtime
    return {'create_time': ctime, 'modified_time': mtime}

def _base_and_ext(basefile):
    base, extension = os.path.splitext(basefile)
    extension = extension.split('.')[-1]
    return (base, extension)
