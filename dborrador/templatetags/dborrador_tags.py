from django import template

register = template.Library()

@register.filter
def bien_o_mal(a, b):
    if a == b:
        return "bien"
    if a > b:
        return "maso"
    return "mal"
