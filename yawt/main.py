""" The main YAWT module, mostly implemented as a Blueprint.
"""
import re

from datetime import datetime
from flask import current_app, g, Blueprint, url_for, request, \
    redirect, abort, render_template
from jinja2 import TemplatesNotFound

from yawt.site_manager import YawtSiteManager, ArticleNotFoundError
from yawt.utils import has_method
from yawt.view import render


def _handle_404(fullname, flavour):
    extensions = []
    if current_app.extension_info:
        extensions = current_app.extension_info[1]
    for ext in extensions:
        if has_method(ext, 'on_404'):
            result = ext.on_404(fullname, flavour)
            if result:
                return result
    return None


yawtbp = Blueprint('yawt', __name__)


@yawtbp.route('/')
def _home():
    return _handle_path('/')


@yawtbp.route('/<path:path>')
def _generic_path(path):
    return _handle_path(path)


@yawtbp.errorhandler(404)
def _page_not_found(error):
    # TODO: figure out what the flavour in the request was
    template_name = '404.'+current_app.config['YAWT_DEFAULT_FLAVOUR']
    return render_template(template_name), 404


@yawtbp.app_template_filter('dateformat')
def date_format(value, ft='%H:%M / %d-%m-%Y'):
    """filter for date and time formatting"""

    v = datetime.fromtimestamp(value)
    return v.strftime(ft)


@yawtbp.app_template_filter('url')
def url(relative_url):
    """make a usable url out of a site relative one"""
    base_url = current_app.config['YAWT_BASE_URL'] or request.url_root
    url_val = base_url.rstrip('/') + '/' + relative_url.lstrip('/')
    return url_val


@yawtbp.app_template_filter('static')
def static(filename):
    """Generate static URLs"""
    return url_for('static', filename=filename)


@yawtbp.before_app_request
def _before_request():
    config = current_app.config
    g.site = YawtSiteManager(root_dir=current_app.yawt_root_dir,
                             draft_folder=config['YAWT_DRAFT_FOLDER'],
                             content_folder=config['YAWT_CONTENT_FOLDER'],
                             template_folder=config['YAWT_TEMPLATE_FOLDER'],
                             file_extensions=config['YAWT_ARTICLE_EXTENSIONS'],
                             meta_types=config['YAWT_META_TYPES'])


def _handle_path(path):
    """
    Returns template source corresponding to path
    """
    current_app.logger.debug('handling path: ' + path)
    config = current_app.config

    fullname = None
    flavour = config['YAWT_DEFAULT_FLAVOUR']

    path = path.lstrip('/')

    if path == '' or path.endswith('/'):
        # user asked for a category page, without an index.
        # Supply index file.
        fullname = path + config['YAWT_INDEX_FILE']
    else:
        pattern = re.compile(r'^(.*?)\.([^/.]+)$')
        match = pattern.match(path)
        if match:
            # we have a flavour ending path, which means the user is
            # requesting a file with particular flavour
            fullname = match.group(1)
            flavour = match.group(2)
        elif g.site.category_exists(path):
            return redirect('/' + path + '/')
        else:
            fullname = path

    current_app.logger.debug('fullname requested: ' + fullname)
    current_app.logger.debug('flavour requested: ' + flavour)

    try:
        article = g.site.fetch_article(fullname)
    except ArticleNotFoundError:
        current_app.logger.debug('no article found at ' + fullname +
                                 ', handling the 404')
        result = _handle_404(fullname, flavour)
        if not result:
            abort(404)
        else:
            return result
    else:
        try:
            return render('article',
                          article.info.category,
                          article.info.slug,
                          flavour, {'article': article})
        except TemplatesNotFound:
            current_app.logger.debug('could not find, aborting with 404')
            abort(404)
