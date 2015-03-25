#pylint: skip-file

def generate_collection_template(single_article, plural_article, info_fields=None):
    """generate a Jinga2 template that displays the given info fields, one on
    each line, like this:

    field1:value1
    """
    if not info_fields:
        info_field = []

    template = '{%% for %s in %s: %%}\n' % (single_article, plural_article)
    for info_field in info_fields:
        template += '%s:' % (info_field)
        template += '{{%s.%s}}\n' % (single_article, info_field)
    template += '\n'
    template += '{% endfor %}'
    return template
