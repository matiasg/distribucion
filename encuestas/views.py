from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.forms import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.core.validators import EmailValidator

from materias.models import Turno, Docente, Cargos, CargoDedicacion, TipoTurno, Cuatrimestres, TipoDocentes
from materias.misc import Mapeos
from encuestas.models import (PreferenciasDocente, OtrosDatos, CargasPedidas, EncuestasHabilitadas,
                              GrupoCuatrimestral, telefono_validator)
from encuestas.forms import HabilitacionDeEncuestaForm

from locale import strxfrm
from collections import Counter, namedtuple
from enum import Enum
import logging
import logging.config
logger = logging.getLogger(__name__)


@login_required
@permission_required('dborrador.add_asignacion')
def index(request):
    return render(request, 'encuestas/administrar.html')


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_habilitadas(request):
    context = {
        'habilitadas': EncuestasHabilitadas.objects.all(),
    }
    return render(request, 'encuestas/administrar_habilitadas.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def borrar_habilitacion(request, habilitacion_id):
    EncuestasHabilitadas.objects.get(pk=habilitacion_id).delete()
    return HttpResponseRedirect(reverse('encuestas:administrar_habilitadas'))


@login_required
@permission_required('dborrador.add_asignacion')
def agregar_habilitacion(request):
    now = timezone.now()
    nueva_habilitacion = EncuestasHabilitadas.objects.create(anno=now.year, desde=now, hasta=now)
    return HttpResponseRedirect(reverse('encuestas:cambiar_habilitacion', args=(nueva_habilitacion.id,)))


@login_required
@permission_required('dborrador.add_asignacion')
def cambiar_habilitacion(request, habilitacion_id):
    habilitacion =  EncuestasHabilitadas.objects.get(pk=habilitacion_id)
    if request.method == 'POST':
        form = HabilitacionDeEncuestaForm(request.POST, instance=habilitacion)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('encuestas:administrar_habilitadas'))
        else:
            logger.error(form.errors)

    else:
        form = HabilitacionDeEncuestaForm(instance=habilitacion)

    context = {'form': form, 'habilitacion': habilitacion}
    return render(request, 'encuestas/cambiar_habilitacion.html', context)


def _turnos_minimos_por_cuatrimestre(cuatrimestre, docente):
    minimos = {
        Cuatrimestres.V.name: 2,
        Cuatrimestres.P.name: 4,
        Cuatrimestres.S.name: 4
    }
    # TODO: queremos que dependa del docente?
    return minimos[cuatrimestre]

def _nombre_cuat_error(cuatrimestre):
    nombres = {
        Cuatrimestres.V.name: 'de verano',
        Cuatrimestres.P.name: '1',
        Cuatrimestres.S.name: '2'
    }
    return nombres[cuatrimestre]

def checkear_y_salvar(datos, anno, cuatrimestres):
    fecha_encuesta = timezone.now()
    docente = Docente.objects.get(pk=datos['docente'])

    # chequeos
    for c in cuatrimestres:
        cuenta = Counter(datos.get(f'opcion{c}{o}', '-1')
                         for o in range(1, 6))
        cuenta.pop('-1', None)  # descarto opciones no completadas
        if any(v > 1 for v in cuenta.values()):
            raise ValidationError('Hay turnos repetidos', code='invalid')

        cargas = int(datos[f'cargas{c}'])
        minimo = _turnos_minimos_por_cuatrimestre(c, docente)
        if cargas > 0 and sum(cuenta.values()) < minimo:
            raise ValidationError(f'La cantidad mínima de turnos para el cuatrimestre {_nombre_cuat_error(c)} es {minimo}')

    email = datos['email']
    telefono = datos['telefono']

    email_validator = EmailValidator(message='La dirección de email es incorrecta')
    email_validator(email)
    telefono_validator(telefono)

    # OtrosDatos
    otros_datos, _ = OtrosDatos.objects.get_or_create(docente=docente, anno=anno, cuatrimestre=cuatrimestres[0],
                                                      defaults={'fecha_encuesta': fecha_encuesta, 'comentario': ''})
    otros_datos.fecha_encuesta = fecha_encuesta
    otros_datos.email = email
    otros_datos.telefono = telefono
    otros_datos.comentario = datos['comentario']
    otros_datos.save()


    #  PreferenciasDocente
    opciones = {}
    for cuatrimestre in cuatrimestres:
        # CargasPedidas
        cargas = int(datos[f'cargas{cuatrimestre}'])
        cargas_pedidas, _ = CargasPedidas.objects.get_or_create(docente=docente, anno=anno, cuatrimestre=cuatrimestre,
                                                                defaults={'fecha_encuesta': fecha_encuesta, 'cargas': 1})
        cargas_pedidas.cargas = cargas
        cargas_pedidas.save()

        opciones_cuat = []
        for opcion in range(1, 6):
            opcion_id = int(datos[f'opcion{cuatrimestre}{opcion}'])
            if opcion_id >= 0:
                turno = Turno.objects.get(pk=opcion_id)
                peso = float(datos[f'peso{cuatrimestre}{opcion}'])
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
                opciones_cuat.append(pref)
        opciones[Cuatrimestres[cuatrimestre]] = opciones_cuat
    return opciones, otros_datos


DocenteParaEncuesta = namedtuple('DocenteParaEncuesta', ['id', 'nombre'])
TurnoParaEncuesta = namedtuple('TurnoParaEncuesta', ['id', 'texto', 'dificil_de_cubrir'])
OpcionesParaEncuesta = namedtuple('OpcionesParaEncuesta', ['numero', 'lista_corta', 'turno_elegido', 'peso'])
OpcionesPorCuatrimestre = namedtuple('OpcionesPorCuatrimestre', ['opciones', 'turnos'])


def _generar_docentes(anno, tipo_docente):
    tipo = TipoDocentes[tipo_docente]
    docentes = [DocenteParaEncuesta(-1, '')]
    docentes += [DocenteParaEncuesta(docente.id, docente.nombre)
                 for docente in sorted(Mapeos.docentes_de_tipo(tipo, anno),
                                       key=lambda d: d.nombre)]
    return docentes


def _generar_contexto(anno, cuatrimestre, tipo_docente):
    tipo = TipoDocentes[tipo_docente]
    turnos_ac = Mapeos.encuesta_tipo_turno(tipo).filter(anno=anno, cuatrimestre=cuatrimestre)

    turnos = [TurnoParaEncuesta(-1, '', True)]
    turnos += [TurnoParaEncuesta(turno.id, f'{turno} ({turno.horarios_info().diayhora})', turno.dificil_de_cubrir)
               for turno in sorted(turnos_ac, key=lambda t: (strxfrm(t.materia.nombre), t.numero))]

    opciones = [OpcionesParaEncuesta(i, i <= 2, -1, 1)
                for i in range(1, 6)]  # las opciones 1 y 2 tienen que ser de las difíciles


    return OpcionesPorCuatrimestre(opciones, turnos)


def _modificar_contexto_con_datos_request(context, datos):
    nuevas_opciones_turnos = {}
    for cuatrimestre, opciones_turnos_cuat in context['opciones_por_cuatrimestre'].items():
        opciones_cuatrimestre = []
        for opcion, dificil, _, _ in opciones_turnos_cuat.opciones:
            elegido = int(datos[f'opcion{cuatrimestre.name}{opcion}'])
            peso = datos[f'peso{cuatrimestre.name}{opcion}']
            opciones_cuatrimestre.append(OpcionesParaEncuesta(opcion, dificil, elegido, peso))
        nuevas_opciones_turnos[cuatrimestre] = OpcionesPorCuatrimestre(opciones_cuatrimestre,
                                                                       opciones_turnos_cuat.turnos)
    context['opciones_por_cuatrimestre'] = nuevas_opciones_turnos

    cargas_cuatrimestre = [f'cargas{c.name}' for c in context['opciones_por_cuatrimestre']]
    for campo in ['email', 'telefono', 'comentario', *cargas_cuatrimestre]:
        context[campo] = datos[campo]

    context['docente_selected'] = int(datos['docente'])


def _encuesta_con_mensaje_de_error(request, context, mensaje):
        messages.error(request, mensaje)
        _modificar_contexto_con_datos_request(context, request.POST)
        return render(request, 'encuestas/encuesta.html', context)


def encuesta(request, anno, cuatrimestres, tipo_docente):
    if not EncuestasHabilitadas.esta_habilitada(anno, cuatrimestres, tipo_docente, timezone.now()):
        return HttpResponse(status=403, content="La encuesta que querés llenar no está habilitada.")

    opciones_por_cuatrimestre = {Cuatrimestres[cuatri]: _generar_contexto(anno, cuatri, tipo_docente)
                                 for cuatri in cuatrimestres}

    context = {
        'docentes': _generar_docentes(anno, tipo_docente),
        'opciones_por_cuatrimestre': opciones_por_cuatrimestre,
        'anno': anno,
        'cuatrimestres': cuatrimestres,
        'tipo_docente': tipo_docente,
        'maximo_peso': 20,
        'email': '', 'telefono': '', 'comentario': '',
        'docente_selected': -1,
        f'cargas{Cuatrimestres.V.name}': 0,
        f'cargas{Cuatrimestres.P.name}': 1,
        f'cargas{Cuatrimestres.S.name}': 1,
    }

    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError):
        return render(request, 'encuestas/encuesta.html', context)
    except Docente.DoesNotExist:
        return _encuesta_con_mensaje_de_error(request, context, "No me dijiste quién sos")
    try:
        opciones, otros_datos = checkear_y_salvar(request.POST, anno, cuatrimestres)
        return render(request,
                      'encuestas/final.html',
                      context={'opciones': opciones, 'docente': docente,
                               'email': otros_datos.email,
                               'telefono': otros_datos.telefono,
                               'comentario': otros_datos.comentario})
    except ValidationError as e:
        return _encuesta_con_mensaje_de_error(request, context, e.message)
