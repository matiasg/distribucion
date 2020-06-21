from django import template

from materias.templatetags.materias_tags import bien_o_mal
from materias.models import TipoDocentes

register = template.Library()
register.filter('bien_o_mal', bien_o_mal)

@register.filter(name='sus_preferencias_en')
def preferencias_docentes(docente, preferencias):
    return preferencias.filter(preferencia__docente=docente)

@register.filter(name='tipo_docente_largo')
def preferencias_docentes(tipo):
    return TipoDocentes[tipo].value

@register.filter(name='de_este_anno')
def de_este_anno(queryset, anno):
    return queryset.filter(anno=anno)

@register.filter(name='de_este_cuatrimestre')
def de_este_cuatrimestre(queryset, cuatrimestre):
    return queryset.filter(cuatrimestre__contains=cuatrimestre)
