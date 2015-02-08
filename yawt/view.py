from flask import current_app, make_response, render_template, abort
from jinja2 import TemplatesNotFound

def render(template, category, flavour, template_variables):
    if flavour is None:
        flavour = current_app.config['YAWT_DEFAULT_FLAVOUR']

    content_type = None
    if flavour in current_app.content_types:
        content_type = current_app.content_types[flavour]

    template_names = get_possible_templates(template, category, flavour)
    # current_app.logger.debug('will look for these templates '+str(template_names))

    try:
        if content_type:
            response = make_response(render_template(template_names, **template_variables))
            response.headers['Content-Type'] = content_type
            return response
        else:
            return render_template(template_names, **template_variables)           
    except TemplatesNotFound:
        abort(404)

def get_possible_templates(template, category, flavour):
    """start at category and return all templates up the chain.
    """
    template_base = template + '.' + flavour
    templates = [category + '/' + template_base]
    current_category = category.rsplit('/', 1)[0]
    while current_category:
        article_template = current_category + '/' + template_base
        templates.append(article_template)
        current_category = current_category.rsplit('/', 1)[0]
    templates.append(template_base)
    return templates
