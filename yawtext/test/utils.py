#pylint: skip-file

def generate_collection_template(single_info, plural_info, info_fields=None):
    """generate a Jinga2 template that displays the given info fields, one on
    each line, like this:

    field1:value1
    """
    if not info_fields:
        info_field = []

    template = '{%% for %s in %s: %%}\n' % (single_info, plural_info)
    for info_field in info_fields:
        template += '%s:' % (info_field)
        template += '{{%s.%s}}\n' % (single_info, info_field)
    template += '\n'
    template += '{% endfor %}'
    return template
