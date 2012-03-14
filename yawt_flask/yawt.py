ENTRY_ROOT = '/home/dcr/entries'

from flask import Flask, render_template

app = Flask(__name__)

# date URLs
@app.route('/<int:year>/')
@app.route('/<int:year>/<int:month>/')
@app.route('/<int:year>/<int:month>/<int:day>/')
def archive(year,month=None,day=None): return _archive(year,month,day,None)

@app.route('/<int:year>/index')
@app.route('/<int:year>/<int:month>/index')
@app.route('/<int:year>/<int:month>/<int:day>/index')
def archive_index(year,month=None,day=None): return _archive(year,month,day,None)

@app.route('/<int:year>/index.<flav>')
@app.route('/<int:year>/<int:month>/index.<flav>')
@app.route('/<int:year>/<int:month>/<int:day>/index.<flav>')
def archive_index(year,month=None,day=None,flav=None): return _archive(year,month,day,flav)

# Category URLs
@app.route('/<path:category>/')
def canonical_category(category): return _category(category,None)
	
@app.route('/<path:category>/index')
def index_category(category): return _category(category,None)
	
@app.route('/<path:category>/index.<flav>')
def index_category_flav(category,flav): return  _category(category,flav)

# Article URLs
@app.route('/<path:category>/<slug>')
def post(category,slug): return _post(category,slug,None)

@app.route('/<path:category>/<slug>.<flav>')
def post_flav(category,slug,flav): return _post(category,slug,flav)

# Permalinks
@app.route('/<int:year>/<int:month>/<int:day>/<slug>')
def permalink(year,month,day,slug): return _permalink(year,month,day,slug,None)

@app.route('/<int:year>/<int:month>/<int:day>/<slug>.<flav>')
def permalink_flav(year, month, day, slug, flav): return _permalink(year, month, day, slug, flav)

# supposed to render one article
def _permalink(year, month, day, slug, flav):
    article_infos = store.fetch_dated_articles(year, month, day, slug)
    article = article_infos[0]
    date = Date(year, month, day)
	return render_template("entry.html",
                           article,
						   category=None, date = date,
                           permalink = True,
                           slug=slug, flav=_flav(flav))

# supposed to render one article
def _post(category, slug, flav):
    article = store.fetch_article_by_category_slug(category, slug)
    return render_template("entry.html",
                           article, category=category, Date(), slug,
                           permalink = False,
						   flav=_flav(flav))

# supposed to render several articles
def _archive(year,month,day,flav):
    article_infos = store.fetch_dated_articles(year, month, day)
    date = Date(year, month, day) 
	return render_template("entry_list.html",
                           article_infos,
						   category=None, Date(year, month, day),
						   flav=_flav(flav))

# supposed to render several articles
def _category(category,flav):
    article_infos = store.fetch_articles_in_category(category)
	return render_template("entry_list.html",
                           article_infos,
						   category=category, Date(),
                           flav=_flav(flav))

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
    reading its contents.  Mostly, this kind of stuff can be gleaned from
    reading the file's metadata.
    """
    def __init__(self, fullname, ctime, mtime):
        """
        fullname is the category + slug of the article.  No root path infomation.
        Like this: cooking/indian/madras
        """
        self.fullname = fullname

        # from the stat function, or maybe loaded from a DB
        self.ctime = ctime
        self.mtime = mtime
        
        self._mtime_tm = time.localtime(self.mtime)
        self._ctime_tm = time.localtime(self.ctime)

    def __eq__(self, other):
        """
        for sorting
        """
        return self is other or (isinstance(other, ArticleInfo) and \
                                 self.fullname == other.fullname and \
                                 self.mtime == other.mtime)

    def date_match(self,year, month, day, slug):
        current_slug = os.path.split(self.fullname)[1]
        return self._ctime_tm.tm_year == year and \
				   (month is None or month == info._ctime_tm.tm_mon) and \
				   (day is None or day == info._ctime_tm.tm_mday) and \
				   (plug is None or plug == current_slug):	
    
class Article(object):
    def __init__(self, info):
        self.info = info
        self.title = ''
        self.content = ''

class FileSystemArticleStore(object):
	def __init__(self, path_system, root_dir, ext):
		self.path_system = path_system
		self.root_dir = root_dir
		self.ext = ext
	
	def find_dated_articles(self, year, month=None, day=None, slug=None):
        """
        Finds article infos by create time and slug.  Only year is required.
        If you specify everything, this becomes a permalink, and only
        one entry should be returned (but in a list)
        """
		results = []
		for af in self._locate_article_files(self.root_dir):
			info = self._fetch_info(af)
            if info.date_match(year, month, day, slug):
                results.append(info)
		return sorted(results, key = lambda info: info.ctime, reverse=True)
	
	def find_articles_by_category(self, category):
        """
        Fetch articles by category.  Returns a list of article infos.
        """
        results = []
        for af in self._locate_article_files(os.path.join(self.root_dir, category)):
            info = self._fetch_info(af)
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
	
	def _fetch_info(self, filename):
		sr = self.path_system._os_stat(filename)
		return ArticleInfo(self._file2name(filename), sr.st_mtime, sr.st_mtime)

    def _fetch_info_by_fullname(self, fullname):
        filename = self.name2file(fullname)
        sr = self.path_system._os_stat(filename)
        return ArticleInfo(fullname, sr.st_mtime, sr.st_mtime)

	def _name2file(self, fullname):
		return os.path.join(self.root_dir, fullname + "." + self.ext)

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

class TemplateStore(object):
    def __init__(self, root_dir):
        self.root_dir

        
if __name__ == '__main__':
    app.run(debug=True)
