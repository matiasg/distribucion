from django import template

register = template.Library()

@register.filter(name='restantes_hasta')
def restantes_hasta(it, cantidad):
    return range(len(it), cantidad)
