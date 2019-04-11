from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.forms import ValidationError
from django.contrib import messages

from materias.models import Turno, Docente, Cargos, CargoDedicacion, TipoTurno, Cuatrimestres
from materias.misc import Mapeos
from encuestas.models import PreferenciasDocente

from collections import Counter
from enum import Enum
import logging
import logging.config
logger = logging.getLogger(__name__)


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
    turnos = Mapeos.encuesta_tipo_turno(tipo_docente).filter(anno=anno, cuatrimestre=cuatrimestre)
    turnos = sorted(turnos, key=lambda t: t.materia.nombre)
    docentes = sorted(Mapeos.docentes(tipo_docente), key=lambda d: d.nombre)
    context = {'turnos': turnos,
               'docentes': docentes,
               'anno': anno,
               'cuatrimestre': cuatrimestre,
               'cuatrimestre_value': Cuatrimestres[cuatrimestre].value,
               'tipo_docente': tipo_docente,
               'maximo_peso': 20,
               }
    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        return render(request, 'encuestas/encuesta.html', context)
    try:
        opciones = checkear_y_salvar(request.POST)
        return render(request,
                      'encuestas/final.html',
                      context={'opciones': opciones, 'docente': docente})
    except ValidationError as e:
        messages.error(request, e.message)
        return render(request, 'encuestas/encuesta.html', context)


def final(request):
    return render(request, 'encuestas/final.html')
