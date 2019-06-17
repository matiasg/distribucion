import logging
from collections import defaultdict, namedtuple
from time import monotonic
from locale import strxfrm

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required


from .models import Preferencia, Asignacion, Comentario, Intento
from .misc import MapeosDistribucion, Distribucion
from materias.models import (Turno, Docente, Carga, Materia, Cuatrimestres, TipoMateria,
                             choice_enum, AnnoCuatrimestre, TipoDocentes,)
from materias.misc import Mapeos
from encuestas.models import PreferenciasDocente, OtrosDatos

from allocation import allocating


logger = logging.getLogger(__name__)


def copiar_anno_y_cuatrimestre(anno, cuatrimestre):
    '''devuelve: (prefs copiadas, prefs borradas) '''
    copiadas = 0
    borradas, _ = Preferencia.objects.filter(preferencia__turno__anno=anno,
                                               preferencia__turno__cuatrimestre=cuatrimestre).delete()

    docentes_con_encuesta = {od.docente for od in OtrosDatos.objects.all()}
    for docente in docentes_con_encuesta:
        prefs = PreferenciasDocente.objects.filter(turno__anno=anno,
                                                   turno__cuatrimestre=cuatrimestre,
                                                   docente=docente)
        peso_total = sum(pref.peso for pref in prefs)
        logger.debug('considerando %d prefs para %s. Peso total: %s',
                     prefs.count(), docente, peso_total)

        for pref in prefs:
            peso_normalizado = pref.peso / peso_total if peso_total else 1 / prefs.count()
            pref_copia = Preferencia.objects.create(preferencia=pref,
                                                    peso_normalizado=peso_normalizado)
            copiadas += 1
    return copiadas, borradas

def _anno_cuat_tipos_context():
    anno_actual = timezone.now().year
    context = {
        'annos': [anno_actual, anno_actual + 1],
        'cuatrimestres': [c for c in Cuatrimestres],
        'tipos': [t for t in TipoDocentes]}
    return context

def _anno_cuat_tipo_de_request(request):
    anno = request.POST['anno']
    cuatrimestre = request.POST['cuatrimestre']
    tipo_name = request.POST['tipo']
    tipo = TipoDocentes[tipo_name]
    return int(anno), cuatrimestre, tipo

@login_required
@permission_required('dborrador.add_asignacion')
def index(request):
    return render(request, 'dborrador/base.html', _anno_cuat_tipos_context())

@login_required
@permission_required('dborrador.add_asignacion')
def preparar(request, anno, cuatrimestre):
    logger.info('copiando preferencias para %s, cuatrimestre %s', anno, Cuatrimestres[cuatrimestre].value)
    copiadas, borradas = copiar_anno_y_cuatrimestre(anno, cuatrimestre)
    logger.info('copiadas: %d, borradas: %d', copiadas, borradas)
    intento = Intento.de_algoritmo(0)
    distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, intento.algoritmo, intento.manual))
    return HttpResponseRedirect(distribucion_url)


def _turno_tipo_obj_a_tipo_fun_obj(d, fun=lambda x: x):
    ret = defaultdict(set)
    for tipo_objs in d.values():
        for tipo, turno_objs in tipo_objs.items():
            ret[tipo].update({fun(o) for o in turno_objs})
    return ret


def _todos_los_intentos():
    asignaciones = Asignacion.objects.all()

    intentos_fin = {a.intentos.upper for a in asignaciones} - {None}
    intentos_fin = {Intento.de_valor(v) for v in intentos_fin}

    intentos_comienzo = {a.intentos.lower for a in asignaciones} - {None}
    intentos_comienzo = {Intento.de_valor(v) for v in intentos_comienzo}

    if intentos_comienzo:
        max_intento = max(i.valor for i in intentos_comienzo)
        max_intento_algoritmo = max(i.algoritmo for i in intentos_comienzo)
        max_intento_manual = max(i.manual for i in intentos_comienzo)
    else:
        max_intento, max_intento_algoritmo, max_intento_manual = 0, 0, 0

    return {
        'intentos_fin': intentos_fin,
        'intentos_comienzo': intentos_comienzo,
        'max_intento': max_intento,
        'max_intento_algoritmo': max_intento_algoritmo,
        'max_intento_manual': max_intento_manual,
    }


@login_required
@permission_required('dborrador.add_asignacion')
def ver_distribucion(request, anno, cuatrimestre, intento_algoritmo, intento_manual):
    ### TODO:
    ## agregar posibilidad de fijar varios cargos a la vez donde están distribuidos
    ## (salvarlos con intentos=(i.valor, i.valor+1) y con intentos=(i.valor+1, None)
    anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
    if 'distribucion' in request.POST:
        distribucion_url = reverse('dborrador:distribucion',
                                   args=(anno, cuatrimestre,
                                         int(request.POST['intento_algoritmo']), int(request.POST['intento_manual'])))
        return HttpResponseRedirect(distribucion_url)
    else:
        intento = Intento(intento_algoritmo, intento_manual)

    if 'hacer_distribucion' in request.POST:
        return None

    context = {'anno': anno,
               'cuatrimestre': cuatrimestre,
               'intento_algoritmo': intento.algoritmo,
               'intento_manual': intento.manual,
               'intento': intento.valor,
               'tipos': list(TipoDocentes),
               **_todos_los_intentos(),
               }

    turnos_ac = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    asignaciones_moviles = Distribucion.asignaciones_por_cargo_ocupado(anno_cuat, intento)
    asignaciones_fijas = Distribucion.ya_distribuidas_por_cargo(anno_cuat)

    preferencias = Preferencia.objects.order_by('peso_normalizado')
    preferencias_por_turno = {turno: preferencias.filter(preferencia__turno=turno).all() for turno in turnos_ac.all()}

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)

        ob_materias = []
        for materia in tmaterias:
            mat_turnos = []
            for turno in sorted(turnos_ac.filter(materia=materia)):
                turno.asignaciones = list(asignaciones_moviles[turno].items())
                turno.cargas = list(asignaciones_fijas[turno].items())
                turno.preferencias = list(preferencias_por_turno[turno])
                mat_turnos.append(turno)

            ob_materias.append([materia, mat_turnos])

        materias.append((obligatoriedad_largo, ob_materias))
    context['materias'] = materias

    cargas_sin_distribuir = Distribucion.no_distribuidas_por_cargo(anno_cuat)
    cargas_de_asignaciones_moviles = {a.carga for a in Asignacion.validas_en(intento)}
    cargas_sin_asignar = {tipo: sorted(set(cargas_sin_distribuir[tipo]) - cargas_de_asignaciones_moviles, key=lambda c: c.docente.nombre)
                          for tipo in TipoDocentes}
    # agrego preferencias al dict
    cargas_sin_asignar_anotadas = {tipo: [(carga, preferencias.filter(preferencia__docente=carga.docente).all())
                                          for carga in cargas]
                                   for tipo, cargas in cargas_sin_asignar.items()}

    context['sin_distribuir'] = cargas_sin_asignar_anotadas
    context['cambiar_docente_url'] = reverse('dborrador:cambiar_docente', args=(anno, cuatrimestre, intento.algoritmo, intento.manual, 0))[:-1]

    return render(request, 'dborrador/distribucion.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def empezar_a_distribuir(request):
    anno = int(request.POST['anno'])
    cuatrimestre = request.POST['cuatrimestre']
    distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, 0, 0))
    return HttpResponseRedirect(distribucion_url)


def hacer_distribucion(anno_cuat, tipo, intento_algoritmo):
    logger.info('Comienzo una distribución automática para el intento %d', intento_algoritmo)
    intento = Intento.de_algoritmo(intento_algoritmo)

    def _como_conjunto(turno_tipo_objs):
        return {obj
                for para_turno in turno_tipo_objs.values()
                for obj in para_turno[tipo]}

    cargas_distribuidas = Distribucion.ya_distribuidas_por_cargo(anno_cuat)
    cargas_asignadas = Distribucion.asignaciones_por_cargo_ocupado(anno_cuat, intento)

    cargas_asignadas_conjunto = {asignacion.carga for asignacion in _como_conjunto(cargas_asignadas)}
    cargas_a_distribuir = set(Distribucion.no_distribuidas_por_cargo(anno_cuat)[tipo])
    todavia_sin_distribuir = cargas_a_distribuir - cargas_asignadas_conjunto

    sources = {str(c.id): 1 for c in todavia_sin_distribuir}

    necesidades = Mapeos.turno_y_necesidad(tipo, anno_cuat)
    targets = {}
    for turno, necesidad in necesidades.items():
        cubiertas = len(cargas_distribuidas[turno][tipo]) + len(cargas_asignadas[turno][tipo])

        if cubiertas > necesidad:
            logger.error('Muchos docentes asignados a %s. Están asignados %s y la necesidad es %s',
                         turno, cargas_distribuidas[turno][tipo] + cargas_asignadas[turno][tipo], necesidad)
        elif cubiertas < necesidad:
            targets[str(turno.id)] = necesidad - cubiertas


    # docentes a distribuir
    preferencias = Preferencia.objects.all()
    pesos = []
    for carga in todavia_sin_distribuir:
        doc_pref = preferencias.filter(preferencia__docente=carga.docente)
        for preferencia in doc_pref:
            carga_id = str(carga.id)
            turno_id = str(preferencia.preferencia.turno.id)
            if turno_id in targets:
                pesos.append({'from': carga_id,
                              'to': turno_id,
                              'weight': preferencia.peso_normalizado
                              })
            else:
                logger.debug('Tengo una preferencia de %s para %s pero ese turno no necesita docentes de tipo %s',
                             preferencia.preferencia.docente, preferencia.preferencia.turno, tipo.value)

    wmap = allocating.ListWeightedMap(pesos)
    logger.info('Voy a hacer una distribución con %d cargas docentes y %d lugares en turnos',
                sum(sources.values()), sum(targets.values()))

    # llamamos al distribuidor
    allocator = allocating.Allocator(sources, wmap, targets, limit_denominator=100)
    distribucion = allocator.get_best()
    logger.debug('distribución obtenida (con ids): %s', distribucion)

    with transaction.atomic():

        logger.info('Voy a poner asignaciones para %s cargas de %s', len(distribucion), tipo.value)
        intento_hasta = Intento.de_algoritmo(intento_algoritmo + 1)
        intentos_para_distribuidos = (intento.valor, intento_hasta.valor)
        for carga_id, turno_id in distribucion:
            if carga_id is None or turno_id is None:
                continue

            carga = Carga.objects.get(pk=int(carga_id))
            turno = Turno.objects.get(pk=int(turno_id))
            asignacion, _ = Asignacion.objects.get_or_create(intentos=intentos_para_distribuidos,
                                                             carga=carga, turno=turno,
                                                             cargo_que_ocupa=tipo.name)


@login_required
@permission_required('dborrador.add_asignacion')
def distribuir(request, anno, cuatrimestre, tipo, intento_algoritmo, intento_manual):
    logger.info('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                tipo, cuatrimestre, anno)

    ##   Distribuimos a partir de I = Intento(a, m), generamos Intento(a+1, 0)
    ##   Lo que hacemos es:
    ##   a. borrar todas las asignaciones que empiezan después de I
    ##   b. a las asignaciones "activas" que empiezan en (a', n) con n > 0, quitarles fin (fin = None)
    ##   c. Para asignaciones de otros tipos
    ##      si empiezan en (a', 0), ponerles fin en (a+2, 0)
    ##   d. Para asignaciones de tipo = tipo
    ##      si empiezan en (a', 0) ponerles fin en (a+1, 0) ==> estas van a distribución

    with transaction.atomic():
        intento = Intento(intento_algoritmo, intento_manual)
        para_borrar = Asignacion.objects.filter(intentos__startswith__gt=intento.valor)
        logger.warning('Borro %d asignaciones', para_borrar.count())
        para_borrar.delete()

        asignaciones = Asignacion.validas_en(intento).all()
        para_extender = [a for a in asignaciones if not Intento.es_de_algoritmo(a.intentos.lower)]
        for a in para_extender:
            a.intentos = (a.intentos.lower, None)
            a.save()
        logger.info('Extendí %d asignaciones manuales', len(para_extender))

        proximo_intento_algoritmo = intento_algoritmo + 1
        tipo = TipoDocentes[tipo]
        for t in TipoDocentes:
            asignaciones_tipo_t = [a
                                   for a in asignaciones.filter(cargo_que_ocupa=t.name)
                                   if Intento.es_de_algoritmo(a.intentos.lower)]
            if t == tipo:
                for a in asignaciones_tipo_t:
                    a.intentos = (a.intentos.lower, Intento(proximo_intento_algoritmo, 0).valor)
                    a.save()
            else:
                for a in asignaciones_tipo_t:
                    a.intentos = (a.intentos.lower, Intento(proximo_intento_algoritmo + 1, 0).valor)
                    a.save()
            logger.info('Extendí %d asignaciones automáticas de tipo %s', len(asignaciones_tipo_t), t.value)

        anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
        hacer_distribucion(anno_cuat, tipo, proximo_intento_algoritmo)
        logger.info('hice una distribucion automática en intento %d', proximo_intento_algoritmo)

    distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, proximo_intento_algoritmo, 0))
    return HttpResponseRedirect(distribucion_url)

@login_required
@permission_required('dborrador.add_asignacion')
def seleccion_tipo_distribuir(request, anno, cuatrimestre, intento_algoritmo, intento_manual):
    tipo = request.POST['tipo']
    return distribuir(request, anno, cuatrimestre, tipo, intento_algoritmo, intento_manual)


class NoTurno:
    def __init__(self, _id=-1, **kwargs):
        self.__dict__.update(kwargs)
        self.id = _id

    def __str__(self):
        return '_____ ningún turno _____'


@login_required
@permission_required('dborrador.add_asignacion')
def cambiar_docente(request, anno, cuatrimestre, intento_algoritmo, intento_manual, carga_id):
    intento = Intento(intento_algoritmo, intento_manual)
    carga = Carga.objects.get(pk=carga_id)
    asignaciones = Asignacion.validas_en(intento).filter(carga=carga)

    if 'cambiar' in request.POST:
        nuevo_intento = Intento(intento.algoritmo, intento.manual + 1)

        if asignaciones.count():
            asignacion = asignaciones.first()
            asignacion.intentos = (asignacion.intentos.lower, nuevo_intento.valor)
            asignacion.save()

        nuevo_turno_id = int(request.POST['cambio_a'])
        if nuevo_turno_id >= 0:
            nuevo_turno = Turno.objects.get(pk=nuevo_turno_id)
            cargo_que_ocupa = TipoDocentes[request.POST['cargo_que_ocupa']]
            Asignacion.objects.create(carga=carga,
                                      turno=nuevo_turno,
                                      intentos=(nuevo_intento.valor, None),
                                      cargo_que_ocupa=cargo_que_ocupa.name)

        distribucion_url = reverse('dborrador:distribucion',
                                   args=(anno, cuatrimestre, nuevo_intento.algoritmo, nuevo_intento.manual))
        return HttpResponseRedirect(distribucion_url)

    elif 'cancelar' in request.POST:
        distribucion_url = reverse('dborrador:distribucion',
                                   args=(anno, cuatrimestre, intento.algoritmo, intento.manual))
        return HttpResponseRedirect(distribucion_url)

    else:
        preferencias = Preferencia.objects.filter(preferencia__docente=carga.docente).order_by('peso_normalizado')
        turnos_preferidos = {p.preferencia.turno for p in preferencias}
        turnos_ac = sorted(Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre).all(),
                           key=lambda t: strxfrm(t.materia.nombre))
        turnos = [(NoTurno(), True)] + [(t, t in turnos_preferidos) for t in turnos_ac]

        if asignaciones.count() == 1:
            asignado = asignaciones.first().turno
        elif asignaciones.count() == 0:
            asignado = NoTurno()
        else:
            raise RuntimeError('La carga %d tiene más de una asignación en %s', carga, intento)

        context = {'carga': carga,
                   'cargos': list(TipoDocentes),
                   'cargo': Mapeos.tipos_de_cargo(carga.cargo),
                   'turnos': turnos,
                   'anno': anno,
                   'cuatrimestre': cuatrimestre,
                   'preferencias': preferencias,
                   'intento_algoritmo': intento_algoritmo,
                   'intento_manual': intento_manual,
                   'asignado': asignado,
                   **_todos_los_intentos(),
                   }

        return render(request, 'dborrador/cambiar_docente.html', context)








######## TODO borrar lo que no se usa más de acá abajo ###########
def materias_distribuidas_dict(anno, cuatrimestre, intento, tipo):
    return {'materias': filtra_materias(anno=anno, cuatrimestre=cuatrimestre, intento=intento, tipo=tipo),
            'anno': anno,
            'cuatrimestre': cuatrimestre,
            'tipo': tipo.name,
            'intento': intento}


def filtra_materias(anno, cuatrimestre, intento, tipo, **kwargs):
    cargas = Mapeos.cargas(tipo, AnnoCuatrimestre(anno, cuatrimestre))

    turnos_ac = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre, **kwargs)
    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)
        materias_turnos = [
                (materia, sorted(turnos_ac.filter(materia=materia)))
                for materia in tmaterias
                ]
        #  TODO: mejorar esto como está en fijar()
        for materia, turnos in materias_turnos:
            for turno in turnos:
                asignaciones = [(a, a.carga in cargas)
                                for a in turno.asignacion_set.all() if a.intento == intento]
                turno.cargas_asignadas = asignaciones

        materias.append((obligatoriedad_largo, materias_turnos))

    return materias


def _append_dicts(*dicts):
    ret = defaultdict(list)
    for d in dicts:
        for k, l in d.items():
            ret[k].extend(l)
    return ret


def _fijar_y_desfijar(request, intento):
    '''Fija y desfija docentes y comentarios al intento actual'''
    logger.info('voy a fijar/desfijar docentes y comentarios para el intento %d', intento)
    with transaction.atomic():
        for k, val in request.POST.items():
            if k.startswith('fijoen'):
                carga_id = int(val)
                if carga_id >= 0:  # hay que crear una asignación nueva
                    _, turno_id, _ = k.split('_')
                    turno = Turno.objects.get(pk=int(turno_id))
                    carga = Carga.objects.get(pk=carga_id)
                    asignacion, creada = Asignacion.objects.get_or_create(
                        turno=turno, carga=carga, intento=intento)
                    if creada:
                        logger.info('Fijé a %s al turno %s en el intento %d',
                                    carga.docente, turno, intento)

            elif k.startswith('cambioen'):
                _, turno_id, carga_id = k.split('_')
                turno = Turno.objects.get(pk=int(turno_id))
                carga = Carga.objects.get(pk=int(carga_id))
                nueva_carga_id = int(val)
                if nueva_carga_id < 0:  # hay que borrar la asignación
                    asignaciones, _ = Asignacion.objects.filter(carga=carga, turno=turno, intento=intento).all().delete()
                    logger.info('Borré %d asignación(es) para %s en %s', asignaciones, carga.docente, turno)

            elif k.startswith('comentarios'):
                _, turno_id = k.split('_')
                turno = Turno.objects.get(pk=int(turno_id))

                if val:
                    comentario, creado = Comentario.objects.get_or_create(turno=turno, intento=intento)
                    comentario.texto = val
                    comentario.save()
                    if creado:
                        logger.debug('Guardé un comentario para turno %s en intento %d: "%s"', turno, intento, val)
                else:
                    previos = Comentario.objects.filter(turno=turno, intento=intento)
                    if previos:
                        logger.info('Borro comentario para turno %s en intento %d', turno, intento)
                        previos.delete()


def _mover_de_intento(turnos_cargas, desde, hacia):
    with transaction.atomic():
        for cargas in turnos_cargas.values():
            for carga in cargas:
                asignacion = Asignacion.objects.get(carga=carga, intento=desde)
                asignacion.intento = hacia
                asignacion.save()
    logger.info('Pasé %d asignaciones en %d turnos de intento %d a intento %d',
                sum(len(a) for a in turnos_cargas.values()), len(turnos_cargas), desde, hacia)


def _pasar_docentes(request, ac, tipo, intento):
    '''Pasa docentes del intento actual a fijos (intento 0)'''
    _mover_de_intento(MapeosDistribucion.cargas_de_asignaciones_para_intento(ac, intento), intento, 0)
    return {'intento': 0}


def _publicar_docentes(request, ac):
    '''Pasa asignaciones de intento -1 a cargas'''
    turnos_cargas = MapeosDistribucion.cargas_otro_tipo(ac)
    with transaction.atomic():
        for turno, cargas in turnos_cargas.items():
            for carga in cargas:

                carga.turno = turno
                carga.save()

                asignacion = Asignacion.objects.get(carga=carga, intento__lt=0)
                asignacion.delete()

                logger.info('publiqué un turno para %s: %s', carga.docente, carga.turno)


def _terminar_esta_distribucion(request, ac):
    '''Pasa asignaciones de año y cuatrimestre de intento 0 a -1'''
    _mover_de_intento(MapeosDistribucion.cargas_de_asignaciones_fijas(ac), 0, -1)
    # borro todas las asignaciones en otros intentos
    MapeosDistribucion.asignaciones_para_todos_los_intentos(ac).delete()
    return {'intento': 0}  # TODO: corregir esta salida (issue #36)


Accion = namedtuple('Accion', ['incluir_en_pagina', 'value', 'titulo', 'texto_on_click', 'funcion', 'args'])

class Acciones:

    def __init__(self):
        self.acciones = {}
        self.orden = []

    def registrar(self, incluir, value, titulo, texto, funcion, args):
        self.acciones[value] = Accion(incluir, value, titulo, texto, funcion, args)
        self.orden.append(value)

    def __getitem__(self, v):
        return self.acciones[v]

    def __iter__(self):
        ret = [self.acciones[k] for k in self.orden]
        return iter(ret)


def _acciones(request, ac, tipo, intento):
    acciones = Acciones()
    acciones.registrar(True,
                       'fijar a intento', f'Fijar y desfijar al intento {intento}', '',
                       _fijar_y_desfijar, (request, intento))
    acciones.registrar(intento > 0,
                       'fijar para todos los intentos', 'Fijar a todos los intentos', 'Confirmá que queres fijar para todos los intentos',
                       _pasar_docentes, (request, ac, tipo, intento))
    acciones.registrar(intento == 0,
                       'terminar esta distribución', 'Terminar',
                       f'Confirmá que ya no querés distribuir docentes de tipo {tipo.value} en {ac.anno} {ac.cuatrimestre}',
                       _terminar_esta_distribucion, (request, ac))
    acciones.registrar(intento == 0,
                       'publicar todo', 'Publicar',
                       f'Vas a publicar todas las distribuciones fijadas en {ac.anno} {ac.cuatrimestre}. Confirmalo',
                       _publicar_docentes, (request, ac))
    return acciones


@login_required
@permission_required('dborrador.add_asignacion')
def fijar(request, anno, cuatrimestre, tipo, intento):
    tipo = TipoDocentes[tipo]
    ac = AnnoCuatrimestre(anno, cuatrimestre)

    if 'fijar' in request.POST:
        # actuar según el botón que se apretó
        acciones = _acciones(request, ac, tipo, intento)
        accion = acciones[request.POST['fijar']]
        proximos_pasos = accion.funcion(*accion.args)
        if proximos_pasos and 'intento' in proximos_pasos:
            intento = proximos_pasos['intento']

    elif 'cambiar' in request.POST:
        intento = int(request.POST['nuevo_intento'])

    context = materias_distribuidas_dict(anno, cuatrimestre, intento, tipo)

    otro_tipo = _append_dicts(Mapeos.cargas_asignadas_en(ac), MapeosDistribucion.cargas_otro_tipo(ac))
    este_tipo = MapeosDistribucion.cargas_de_asignaciones_para_intento(ac, intento)
    necesidades_no_cubiertas = MapeosDistribucion.necesidades_tipo_no_cubiertas_en(tipo, ac, intento)
    # si queremos fijar docentes al intento 0, tienen que aparecer en este_tipo, no en este_tipo_fijo
    este_tipo_fijo = MapeosDistribucion.cargas_de_asignaciones_fijas(ac) if intento > 0 else defaultdict(list)

    ### XXX: este masajeo hay que refactorizarlo unificando bien con filtra_materias()
    DatosDeTurno = namedtuple('DDT', ['asignaciones_otro_tipo', 'asignaciones_este_tipo_fijo', 'asignaciones_este_tipo',
                                      'necesidades_no_cubiertas', 'comentarios'])
    for obligatoriedad, materias_turnos in context['materias']:
        for materia, turnos in materias_turnos:
            for turno in turnos:
                comentarios = Comentario.objects.filter(intento=intento, turno=turno)
                comentarios = comentarios.first().texto if comentarios else ''
                datos = DatosDeTurno(otro_tipo[turno], este_tipo_fijo[turno], este_tipo[turno],
                                     necesidades_no_cubiertas[turno], comentarios)
                turno.datos = datos

    cargas_a_distribuir = MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(tipo, ac, intento)
    context.update({'cargas_a_distribuir': cargas_a_distribuir})

    # TODO: si hay docentes distribuidos más que sus cargas o turnos cubiertos de más hay que tirar excepción
    context['problemas'] = MapeosDistribucion.chequeo(tipo, ac, intento, este_tipo_fijo, este_tipo)
    context['acciones'] = _acciones(request, ac, tipo, intento)

    return render(request, 'dborrador/fijar.html', context)
