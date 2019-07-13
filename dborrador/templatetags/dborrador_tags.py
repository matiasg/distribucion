from django import template

from materias.templatetags.materias_tags import bien_o_mal

register = template.Library()
register.filter('bien_o_mal', bien_o_mal)
