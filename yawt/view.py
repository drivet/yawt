import os
from flask import current_app, make_response, render_template

def render(fullname, flavour, template_variables, content_type):
    if flavour is None:
        flavour = current_app.config['YAWT_DEFAULT_FLAVOUR']
    template_names = get_possible_templates(fullname, flavour)
    # current_app.logger.debug('will look for these templates '+str(template_names))
    
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
