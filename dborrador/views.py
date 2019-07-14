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


from .models import Preferencia, Asignacion, Comentario, Intento, IntentoRegistrado
from .misc import Distribucion
from materias.models import (Turno, Docente, Carga, Materia, Cuatrimestres, TipoMateria,
                             choice_enum, AnnoCuatrimestre, TipoDocentes,)
from materias.misc import Mapeos, NoTurno
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


def _todos_los_intentos(anno, cuatrimestre, intento_algoritmo):
    intentos = IntentoRegistrado.objects.filter(anno=anno, cuatrimestre=cuatrimestre)

    intentos_manuales_con_algoritmo = {Intento.de_valor(i.intento).manual
                                       for i in intentos
                                       if Intento.de_valor(i.intento).algoritmo == intento_algoritmo}
    max_intento = IntentoRegistrado.maximo_intento(anno, cuatrimestre)

    return {
        'max_intento': max_intento.valor,
        'max_intento_algoritmo': max_intento.algoritmo,
        'max_intento_manual': max(intentos_manuales_con_algoritmo) if intentos_manuales_con_algoritmo else 0,
    }


@login_required
@permission_required('dborrador.add_asignacion')
def espiar_distribucion(request, anno, cuatrimestre, intento_algoritmo, intento_manual):
    anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
    intento = Intento(intento_algoritmo, intento_manual)

    intento_algoritmo_acotado, intento_manual_acotado = _acota_intentos_para_ver(anno_cuat.anno, anno_cuat.cuatrimestre,
                                                                                 intento_algoritmo, intento_manual)
    intento_acotado = Intento(intento_algoritmo_acotado, intento_manual_acotado)
    if intento.valor != intento_acotado.valor:
        redirect = reverse('dborrador:espiar_distribucion', args=(anno, cuatrimestre, intento_algoritmo_acotado, intento_manual_acotado))
        return HttpResponseRedirect(redirect)


    context = {'anno': anno,
               'cuatrimestre': Cuatrimestres[cuatrimestre],
               'intento_algoritmo': intento.algoritmo,
               'intento_manual': intento.manual,
               'intento': intento.valor,
               'tipos': list(TipoDocentes),
               **_todos_los_intentos(anno, cuatrimestre, intento.algoritmo),
               }

    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    asignaciones_moviles = Distribucion.asignaciones_por_cargo_ocupado(anno_cuat, intento)
    asignaciones_fijas = Distribucion.ya_distribuidas_por_cargo(anno_cuat)

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)

        ob_materias = []
        for materia in tmaterias:
            mat_turnos = []
            for turno in sorted(materia.turno_set.filter(anno=anno, cuatrimestre=cuatrimestre)):
                turno.asignaciones = list(asignaciones_moviles[turno].items())
                turno.cargas = list(asignaciones_fijas[turno].items())
                mat_turnos.append(turno)

            ob_materias.append([materia, mat_turnos])

        materias.append((obligatoriedad_largo, ob_materias))
    context['materias'] = materias
    return render(request, 'dborrador/espiar_distribucion.html', context)


def _acota_intentos_para_ver(anno, cuatrimestre, intento_algoritmo, intento_manual):
    '''devuelve (intento_algoritmo, intento_manual) más cercanos a los de entrada
    de manera que haya asignaciones con ese intento.

    TODO: re-escribirla usando directamente IntentoRegistrado.max_intento()
    '''
    intentos = _todos_los_intentos(anno, cuatrimestre, intento_algoritmo)

    if intento_algoritmo < 0:
        return _acota_intentos_para_ver(anno, cuatrimestre, 0, intento_manual)
    elif intento_algoritmo > intentos['max_intento_algoritmo']:
        return _acota_intentos_para_ver(anno, cuatrimestre, intentos['max_intento_algoritmo'], intento_manual)
    elif intento_manual < 0:
        return _acota_intentos_para_ver(anno, cuatrimestre, intento_algoritmo, 0)
    elif intento_manual > intentos['max_intento_manual']:
        return _acota_intentos_para_ver(anno, cuatrimestre, intento_algoritmo, intentos['max_intento_manual'])

    return (intento_algoritmo, intento_manual)


class InformacionParaTemplate(namedtuple('IPT', 'sin_distribuir necesidades cargas')):

    pass


@login_required
@permission_required('dborrador.add_asignacion')
def ver_distribucion(request, anno, cuatrimestre, intento_algoritmo, intento_manual):
    ### TODO:
    ## agregar posibilidad de fijar varios cargos a la vez donde están distribuidos
    ## (salvarlos con intentos=(i.valor, i.valor+1) y con intentos=(i.valor+1, None)
    anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
    intento = Intento(intento_algoritmo, intento_manual)

    intento_algoritmo_acotado, intento_manual_acotado = _acota_intentos_para_ver(anno_cuat.anno, anno_cuat.cuatrimestre,
                                                                                 intento_algoritmo, intento_manual)
    intento_acotado = Intento(intento_algoritmo_acotado, intento_manual_acotado)
    if intento.valor != intento_acotado.valor:
        redirect = reverse('dborrador:distribucion', args=(anno, cuatrimestre, intento_algoritmo_acotado, intento_manual_acotado))
        return HttpResponseRedirect(redirect)

    logger.info('intento: %d, %d', intento_algoritmo, intento_manual)

    context = {'anno': anno,
               'cuatrimestre': Cuatrimestres[cuatrimestre],
               'intento_algoritmo': intento_algoritmo,
               'intento_manual': intento_manual,
               'intento': intento.valor,
               'tipos': list(TipoDocentes),
               **_todos_los_intentos(anno, cuatrimestre, intento_algoritmo),
               }

    turnos_ac = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    asignaciones_moviles = Distribucion.asignaciones_por_cargo_ocupado(anno_cuat, intento)
    asignaciones_fijas = Distribucion.ya_distribuidas_por_cargo(anno_cuat)
    necesidades_por_turno = Mapeos.necesidades_por_turno_y_tipo(anno_cuat)

    preferencias = Preferencia.objects.order_by('preferencia__cargo',
                                                'peso_normalizado',
                                                'preferencia__docente__na_apellido')
    preferencias_por_turno = {turno: preferencias.filter(preferencia__turno=turno).all()
                              for turno in turnos_ac.all()}

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)

        ob_materias = []
        for materia in tmaterias:
            mat_turnos = []
            for turno in sorted(turnos_ac.filter(materia=materia)):
                turno.asignaciones = list(asignaciones_moviles[turno].items())
                turno.cargas = list(asignaciones_fijas[turno].items())
                turno.necesidades_insatisfechas = {tipo: necesidades_por_turno[turno][tipo] \
                                                         - len(asignaciones_moviles[turno][tipo]) \
                                                         - len(asignaciones_fijas[turno][tipo])
                                                   for tipo in TipoDocentes}
                turno.preferencias = list(preferencias_por_turno[turno])
                mat_turnos.append(turno)

            ob_materias.append([materia, mat_turnos])

        materias.append((obligatoriedad_largo, ob_materias))
    context['materias'] = materias

    cargas_sin_distribuir = Distribucion.no_distribuidas_por_cargo(anno_cuat)
    cargas_de_asignaciones_moviles = {a.carga for a in Asignacion.validas_en(intento)}
    cargas_sin_asignar = {tipo: sorted(set(cargas_sin_distribuir[tipo]) - cargas_de_asignaciones_moviles,
                                       key=lambda c: c.docente.nombre)
                          for tipo in TipoDocentes}
    # agrego preferencias al dict
    cargas_sin_asignar_anotadas = {tipo: [(carga, preferencias.filter(preferencia__docente=carga.docente).all())
                                          for carga in cargas]
                                   for tipo, cargas in cargas_sin_asignar.items()}

    context['cambiar_docente_url'] = reverse('dborrador:cambiar_docente',
                                             args=(anno, cuatrimestre, intento.algoritmo, intento.manual, 0))[:-1]

    necesidades_por_tipo = {tipo: sum(necesidades_por_turno[turno][tipo] for turno in turnos_ac)
                            for tipo in TipoDocentes}
    cargas_por_tipo = {tipo: sum(len(asignaciones_moviles[turno][tipo]) + len(asignaciones_fijas[turno][tipo]) for turno in turnos_ac) \
                             + len(cargas_sin_asignar[tipo])
                       for tipo in TipoDocentes}

    context['info_por_tipo'] = {tipo: InformacionParaTemplate(cargas_sin_asignar_anotadas[tipo],
                                                              necesidades_por_tipo[tipo],
                                                              cargas_por_tipo[tipo])
                                for tipo in TipoDocentes}

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
        IntentoRegistrado.objects.create(intento=intento.valor, anno=anno_cuat.anno, cuatrimestre=anno_cuat.cuatrimestre)

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

        IntentoRegistrado.objects.filter(intento__gt=intento.valor, anno=anno, cuatrimestre=cuatrimestre).delete()

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


@login_required
@permission_required('dborrador.add_asignacion')
def cambiar_docente(request, anno, cuatrimestre, intento_algoritmo, intento_manual, carga_id):
    intento = Intento(intento_algoritmo, intento_manual)
    carga = Carga.objects.get(pk=carga_id)
    asignaciones = Asignacion.validas_en(intento).filter(carga=carga)

    if 'cambiar' in request.POST:
        nuevo_intento = Intento(intento.algoritmo, intento.manual + 1)
        IntentoRegistrado.objects.create(intento=nuevo_intento.valor, anno=anno, cuatrimestre=cuatrimestre)

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

        turnos_preferidos = {p.preferencia.turno: p.peso_normalizado for p in preferencias}

        turnos_ac = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre).all()
        turnos_no_preferidos = sorted(set(turnos_ac) - set(turnos_preferidos),
                                      key=lambda t: strxfrm(t.materia.nombre))

        if asignaciones.count() == 1:
            asignado = asignaciones.first().turno
        elif asignaciones.count() == 0:
            asignado = NoTurno()
        else:
            raise RuntimeError('La carga %d tiene más de una asignación en %s', carga, intento)

        context = {'carga': carga,
                   'cargos': list(TipoDocentes),
                   'cargo': Mapeos.tipos_de_cargo(carga.cargo),
                   'no_turno': NoTurno(),
                   'turnos_preferidos': turnos_preferidos,
                   'turnos_no_preferidos': turnos_no_preferidos,
                   'anno': anno,
                   'cuatrimestre': Cuatrimestres[cuatrimestre],
                   'preferencias': preferencias,
                   'intento_algoritmo': intento_algoritmo,
                   'es_maximo_intento': IntentoRegistrado.maximo_intento(anno, cuatrimestre) == intento,
                   'intento_manual': intento_manual,
                   'asignado': asignado,
                   **_todos_los_intentos(anno, cuatrimestre, intento_algoritmo),
                   }

        return render(request, 'dborrador/cambiar_docente.html', context)


def publicar(request, anno, cuatrimestre, intento_algoritmo, intento_manual):
    intento = Intento(intento_algoritmo, intento_manual)
    asignaciones = Asignacion.validas_en(intento).all()

    with transaction.atomic():
        for asignacion in asignaciones:
            carga = asignacion.carga
            carga.turno = asignacion.turno
            carga.save()
            logger.debug('Estoy publicando: %s', carga)

        logger.info('publiqué %d asignaciones', asignaciones.count())
        IntentoRegistrado.objects.filter(anno=anno, cuatrimestre=cuatrimestre).delete()
        borradas, _ = Asignacion.objects.filter(carga__anno=anno, carga__cuatrimestre=cuatrimestre).all().delete()
        logger.info('y ahora borré %d de dborrador', borradas)

    redirect = reverse('materias:por_anno_y_cuatrimestre', args=(f'{anno}{Cuatrimestres[cuatrimestre].value}',))
    return HttpResponseRedirect(redirect)
