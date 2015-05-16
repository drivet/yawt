"""Basic rendering code"""

from __future__ import absolute_import

from flask import current_app, make_response, render_template


def render(template, category, base, flavour, template_variables):
    """The main YAWT render routine"""
    if flavour is None:
        flavour = current_app.config['YAWT_DEFAULT_FLAVOUR']

    content_type = None
    if flavour in current_app.content_types:
        content_type = current_app.content_types[flavour]

    template_names = get_possible_templates(template, category, base, flavour)

    if content_type:
        response = make_response(render_template(template_names, **template_variables))
        response.headers['Content-Type'] = content_type
        return response
    else:
        return render_template(template_names, **template_variables)


def get_possible_templates(template, category, base, flavour):
    """
    start at category and return all templates up the chain.
    """
    base_file = base + "." + flavour
    if category:
        base_file = category + '/' + base_file
    templates = [base_file]
    template_base = template + '.' + flavour
    current_category = category
    while current_category:
        article_template = current_category + '/' + template_base
        templates.append(article_template)
        current_category = _parent_category(current_category)
    templates.append(template_base)
    return templates


def _parent_category(category):
    if '/' in category:
        return category.rsplit('/', 1)[0]
    else:
        return ''
