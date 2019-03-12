from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.forms import ValidationError

from materias.models import Turno, Docente, Cargos, TipoTurno, Cuatrimestres
from .models import PreferenciasDocente

from collections import Counter
from enum import Enum
import logging
import logging.config
logger = logging.getLogger(__name__)


class TipoDocentes(Enum):
    P = 'Profesores'
    J = 'JTP/Ay1'
    A = 'Ay2'


class Mapeos:
    '''Esta clase resuelve distintos tipos de mapeos'''

    @staticmethod
    def docentes(tipo):
        '''P: profesor, J: JTP y Ay1, A: Ay2'''
        el_mapa = {TipoDocentes.P.name: [Cargos.Tit.name, Cargos.Aso.name, Cargos.Adj.name],
                   TipoDocentes.J.name: [Cargos.JTP.name, Cargos.Ay1.name],
                   TipoDocentes.A.name: [Cargos.Ay2.name],
                   }
        cargos = el_mapa[tipo.upper()]
        return Docente.objects.filter(cargo__in=cargos)

    @staticmethod
    def encuesta_tipo_turno(tipo_docente):
        '''
        Para profesores: teóricas y teórico-prácticas.
        Para auxiliares: prácticas y teórico-prácticas.
        '''
        el_mapa = {TipoDocentes.P.name: [TipoTurno.T.name, TipoTurno.A.name],
                   TipoDocentes.J.name: [TipoTurno.P.name, TipoTurno.A.name],
                   TipoDocentes.A.name: [TipoTurno.P.name, TipoTurno.A.name],
                   }
        tipos = el_mapa[tipo_docente.upper()]
        return Turno.objects.filter(tipo__in=tipos)


def checkear_y_salvar(datos):
    cuenta = Counter(datos.get(f'opcion{o}', '') for o in range(1, 6))
    cuenta.pop('', None)  # descarto opciones no completadas
    if any(v > 1 for v in cuenta.values()):
        raise ValidationError(
                'Hay turnos repetidos', code='invalid')

    fecha_encuesta = timezone.now()
    docente = Docente.objects.get(pk=datos['docente'])
    opciones = []
    for opcion in range(1, 6):
        opcion_id_str = datos['opcion{}'.format(opcion)]
        if opcion_id_str:
            turno = Turno.objects.get(pk=opcion_id_str)
            peso = float(datos['peso{}'.format(opcion)])
            logger.debug('miro preferencia de docente: %s, turno: %s, peso: %s, fecha: %s',
                         docente, turno, peso, fecha_encuesta)
            
            pref, creada = PreferenciasDocente.objects.get_or_create(
                                                docente=docente,
                                                turno=turno,
                                                defaults={'peso': peso, 'fecha_encuesta': fecha_encuesta}
                                                )
            if creada:
                logger.info('Agrego preferencia de docente: %s, turno: %s, peso: %s, fecha: %s',
                            docente, turno, peso, fecha_encuesta)
            else:
                if pref.peso != peso:
                    logger.warning('Le cambio el peso a la preferencia de %s por %s. De %s a %s',
                                   docente, turno, pref.peso, peso)
                    pref.peso = peso
                    pref.fecha_encuesta = fecha_encuesta
                    pref.save()
            opciones.append(pref)
    return opciones


def index(request):
    raise Http404('Todavía no hay contenido para esta página')


def encuesta(request, anno, cuatrimestre, tipo_docente):
    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        cuatrimestre_value = Cuatrimestres[cuatrimestre].value
        turnos = Mapeos.encuesta_tipo_turno(tipo_docente).filter(anno=anno, cuatrimestre=cuatrimestre)
        context = {'turnos': turnos,
                   'docentes': Mapeos.docentes(tipo_docente),
                   'anno': anno,
                   'cuatrimestre': cuatrimestre_value,
                   'tipo_docente': tipo_docente,
                   'error_message': 'Esto esta mal, muy mal',
                   }
        return render(request, 'encuestas/encuesta.html', context)
    else:
        opciones = checkear_y_salvar(request.POST)
        return render(request,
                      'encuestas/final.html',
                      context={'opciones': opciones, 'docente': docente})


def final(request):
    return render(request, 'encuestas/final.html')
