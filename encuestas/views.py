from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.forms import ValidationError
from django.contrib import messages
from django.core.validators import EmailValidator

from materias.models import Turno, Docente, Cargos, CargoDedicacion, TipoTurno, Cuatrimestres
from materias.misc import Mapeos, TipoDocentes
from encuestas.models import PreferenciasDocente, OtrosDatos, telefono_validator

from collections import Counter, namedtuple
from enum import Enum
import logging
import logging.config
logger = logging.getLogger(__name__)


def checkear_y_salvar(datos):
    fecha_encuesta = timezone.now()

    # chequeos
    cuenta = Counter(datos.get(f'opcion{o}', '') for o in range(1, 6))
    cuenta.pop('', None)  # descarto opciones no completadas
    if any(v > 1 for v in cuenta.values()):
        raise ValidationError('Hay turnos repetidos', code='invalid')

    email = datos['email']
    telefono = datos['telefono']

    email_validator = EmailValidator(message='La dirección de email es incorrecta')
    email_validator(email)
    telefono_validator(telefono)

    # OtrosDatos
    docente = Docente.objects.get(pk=datos['docente'])
    otros_datos, _ = OtrosDatos.objects.get_or_create(docente=docente,
                                                      defaults={'fecha_encuesta': fecha_encuesta,
                                                                'cargas': 0, 'comentario': ''})
    otros_datos.fecha_encuesta = fecha_encuesta
    otros_datos.cargas = datos['cargas']
    otros_datos.email = email
    otros_datos.telefono = telefono
    otros_datos.comentario = datos['comentario']
    otros_datos.save()

    #  PreferenciasDocente
    opciones = []
    for opcion in range(1, 6):
        opcion_id = int(datos['opcion{}'.format(opcion)])
        if opcion_id >= 0:
            turno = Turno.objects.get(pk=opcion_id)
            peso = float(datos['peso{}'.format(opcion)])
            logger.debug('miro preferencia de docente: %s, turno: %s, peso: %s, fecha: %s',
                         docente, turno, peso, fecha_encuesta)

            pref, creada = PreferenciasDocente.objects.get_or_create(docente=docente, turno=turno,
                                                                     defaults={'peso': peso,
                                                                               'fecha_encuesta': fecha_encuesta})
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
    return opciones, otros_datos


def index(request):
    raise Http404('Todavía no hay contenido para esta página')



DocenteParaEncuesta = namedtuple('DocenteParaEncuesta', ['id', 'nombre'])
TurnoParaEncuesta = namedtuple('TurnoParaEncuesta', ['id', 'texto', 'dificil_de_cubrir'])
OpcionesParaEncuesta = namedtuple('OpcionesParaEncuesta', ['numero', 'lista_corta', 'turno_elegido', 'peso'])


def _generar_contexto(anno, cuatrimestre, tipo_docente):
    tipo = TipoDocentes[tipo_docente]
    turnos_ac = Mapeos.encuesta_tipo_turno(tipo).filter(anno=anno, cuatrimestre=cuatrimestre)

    turnos = [TurnoParaEncuesta(-1, '', True)]
    turnos += [TurnoParaEncuesta(turno.id, f'{turno} ({turno.horarios_info().diayhora})', turno.dificil_de_cubrir)
               for turno in sorted(turnos_ac, key=lambda t: t.materia.nombre)]

    docentes = [DocenteParaEncuesta(-1, '')]
    docentes += [DocenteParaEncuesta(docente.id, docente.nombre)
                 for docente in sorted(Mapeos.docentes_de_tipo(tipo), key=lambda d: d.nombre)]

    opciones = [OpcionesParaEncuesta(i, i <= 2, -1, 1)
                for i in range(1, 6)]  # las opciones 1 y 2 tienen que ser de las difíciles
    context = {'opciones': opciones,
               'turnos': turnos,
               'docentes': docentes,
               'docente_selected': -1,
               'anno': anno,
               'cuatrimestre': cuatrimestre,
               'cuatrimestre_value': Cuatrimestres[cuatrimestre].value,
               'tipo_docente': tipo_docente,
               'maximo_peso': 20,
               'cargas': 1, 'email': '', 'telefono': '', 'comentario': ''
               }
    return context


def _modificar_contexto_con_datos_request(context, datos):
    nuevas_opciones = []
    for opcion, dificil, _, _ in context['opciones']:
        elegido = int(datos[f'opcion{opcion}'])
        peso = datos[f'peso{opcion}']
        nuevas_opciones.append(OpcionesParaEncuesta(opcion, dificil, elegido, peso))
    context['opciones'] = nuevas_opciones

    for campo in ['cargas', 'email', 'telefono', 'comentario']:
        context[campo] = datos[campo]

    context['docente_selected'] = int(datos['docente'])


def encuesta(request, anno, cuatrimestre, tipo_docente):
    context = _generar_contexto(anno, cuatrimestre, tipo_docente)
    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        return render(request, 'encuestas/encuesta.html', context)
    try:
        opciones, otros_datos = checkear_y_salvar(request.POST)
        return render(request,
                      'encuestas/final.html',
                      context={'opciones': opciones, 'docente': docente,
                               'email': otros_datos.email,
                               'telefono': otros_datos.telefono,
                               'comentario': otros_datos.comentario})
    except ValidationError as e:
        messages.error(request, e.message)
        _modificar_contexto_con_datos_request(context, request.POST)
        return render(request, 'encuestas/encuesta.html', context)
