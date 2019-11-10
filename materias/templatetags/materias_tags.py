from django import template
from django.template.defaultfilters import stringfilter

from materias.models import CargoDedicacion, Turno
from materias.misc import Mapeos

register = template.Library()

@register.filter(name='restantes_hasta')
def restantes_hasta(it, cantidad):
    return range(len(it), cantidad)

@register.filter
@stringfilter
def cargo_nombre_largo(cargo_dedicacion):
    cd = CargoDedicacion[cargo_dedicacion]
    return cd.value

@register.filter
def bien_o_mal(a, b):
    if a == b:
        return "bien"
    if a > b:
        return "maso"
    return "mal"

@register.filter
def ordenados(lista):
    return sorted(lista)

@register.filter
def cargas_ordenadas(turno):
    cargas = sorted(turno.carga_set.all(), key=Mapeos.key_orden_por_tipo_docente)
    return ' - '.join([f'{carga.docente.nombre}' for carga in cargas])
