from flask import current_app, g, Blueprint, url_for, request, \
      redirect, abort, make_response, render_template
from jinja2 import TemplatesNotFound
import time
import re
import os
from yawt.article import FileBasedSiteManager
from yawt.site_manager import YawtSiteManager


def _config(key):
    return current_app.config[key]

yawtbp = Blueprint('yawt', __name__)

@yawtbp.route('/')
def home():
    return handle_path('/')
    
@yawtbp.route('/<path:path>')
def generic_path(path):
    return handle_path(path) 

@yawtbp.errorhandler(404)
def page_not_found(error):
#    current_app.logger.debug('running error handler for 404')
    # TODO: figure out what the flavour in the request was
    template_name = '404.'+current_app.config['YAWT_DEFAULT_FLAVOUR']
#    current_app.logger.debug('rendering template ' + template_name)
    return render_template(template_name), 404

# filter for date and time formatting
@yawtbp.app_template_filter('dateformat')
def date_format(value, ft='%H:%M / %d-%m-%Y'):
    return time.strftime(ft, value)

# make a usable url out of a site relative one
@yawtbp.app_template_filter('url')
def url(relative_url):
    base_url = current_app.config['YAWT_BASE_URL'] or request.url_root
    url_val = base_url.rstrip('/') + '/' + relative_url.lstrip('/')
    return url_val

@yawtbp.app_template_filter('static')
def static(filename):
    return url_for('static', filename=filename)

@yawtbp.before_request
def before_request():
    config = current_app.config
#    current_app.logger.debug('creating article store with path ' +  
#                             path_to_articles + ' and extensions '+ 
#                             str(config['YAWT_ARTICLE_EXTENSIONS']))
    g.store = FileBasedSiteManager(current_app.yawt_root_dir,
                                   config['YAWT_DRAFT_FOLDER'],
                                   config['YAWT_CONTENT_FOLDER'], 
                                   config['YAWT_TEMPLATE_FOLDER'],
                                   config['YAWT_ARTICLE_EXTENSIONS'])

    g.site = YawtSiteManager(g.store)

def handle_path(path):
    """Returns template source corresponding to path
    """
#    current_app.logger.debug('handling path ' + path)
    config = current_app.config

    fullname = None
    flavour = config['YAWT_DEFAULT_FLAVOUR']

    path = path.lstrip('/')
        
    if path == '' or path.endswith('/'):
        # user asked for a category page, without an index.  
        # Supply index file.
        fullname = path + config['YAWT_INDEX_FILE']
    else:
        p = re.compile(r'^(.*?)\.([^/.]+)$')
        m = p.match(path)
        if (m):
            # we have a flavour ending path, which means the user is 
            # requesting a file with particular flavour
            fullname = m.group(1)
            flavour = m.group(2)
        elif g.store.is_category(path):
            return redirect('/' + path + '/')
        else:
            fullname = path

#    current_app.logger.debug('fullname: ' + fullname)
#    current_app.logger.debug('flavour: ' + flavour)
    
    article = g.site.fetch_article(fullname)
    if article is None:
#        current_app.logger.debug('no article found at ' + fullname + ', aborting with 404')
        abort(404)
    else:
        content_type = None
        if flavour in current_app.content_types:
            content_type = current_app.content_types[flavour]
        try:
            return render(fullname, flavour, {'article' : article}, content_type)
        except TemplatesNotFound:
            abort(404)

def render(fullname, flavour, template_variables, content_type):
    if flavour is None:
        flavour = current_app.config['YAWT_DEFAULT_FLAVOUR']
    template_names = get_possible_templates(fullname, flavour)
#    current_app.logger.debug('will look for these templates '+str(template_names))
    
    if (content_type is not None):
        response = make_response(render_template(template_names, **template_variables))
        response.headers['Content-Type'] = content_type
        return response
    else:
        return render_template(template_names, **template_variables)

def get_possible_templates(fullname, flavour):
    """return a lits of the fullname as a template, followed by the templates
    up the folder tree.
    """
    templates = [fullname + '.' + flavour]

    article_template_base = current_app.config['YAWT_ARTICLE_TEMPLATE'] + '.' + flavour
    current_category = os.path.dirname(fullname)
    while current_category:
        article_template = os.path.join(current_category, article_template_base)
        templates.append(article_template)
        current_category = os.path.dirname(current_category)
    templates.append(article_template_base)
    return templates
