import logging
from collections import Counter

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Max
from django.contrib import messages

from .models import Preferencia, Asignacion
from materias.models import (Turno, Docente, Carga, Materia, CuatrimestreDocente,
                             Cuatrimestres, TipoMateria, choice_enum)
from materias.misc import TipoDocentes, AnnoCuatrimestre, Mapeos
from encuestas.models import PreferenciasDocente

from allocation import allocating


logger = logging.getLogger(__name__)


def copiar_anno_y_cuatrimestre(anno, cuatrimestre, tipo):
    '''devuelve: (prefs copiadas, prefs ya existentes) '''
    copiadas = 0
    existentes, _ = Preferencia.objects.all().delete()

    for docente in Mapeos.docentes_de_tipo(tipo):
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
    return copiadas, existentes

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
    tipo = request.POST['tipo']
    return int(anno), cuatrimestre, tipo

def index(request):
    try:
        anno, cuatrimestre, tipo = _anno_cuat_tipo_de_request(request)
        distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo, 1))
        return HttpResponseRedirect(distribucion_url)
    except:
        anno = timezone.now().year
        return render(request, 'dborrador/index.html', _anno_cuat_tipos_context())


def preparar(request):
    try:
        anno, cuatrimestre, tipo = _anno_cuat_tipo_de_request(request)
        logger.info('copiando %s y %s para docents tipo %s', anno, cuatrimestre, tipo)

        copiadas, existentes = copiar_anno_y_cuatrimestre(anno, cuatrimestre, tipo)
        context = {'copiadas': copiadas, 'existentes': existentes}
        return render(request, 'dborrador/despues_de_preparar.html', context)
    except KeyError:
        anno_actual = timezone.now().year
        return render(request, 'dborrador/elegir_ac.html', _anno_cuat_tipos_context())


def distribuir(request):
    try:
        anno, cuatrimestre, tipo = _anno_cuat_tipo_de_request(request)
        intento = int(request.POST['intento'])

    except KeyError:
        anno_actual = timezone.now().year
        context = _anno_cuat_tipos_context()
        context['intento'] = 1
        return render(request, 'dborrador/distribuir.html', context)

    else:
        anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
        # buscamos asignaciones anteriores del mismo intento
        asignaciones_previas = Mapeos.asignaciones(tipo, anno_cuat, intento)
        docentes = Mapeos.docentes_de_tipo(tipo)
        if asignaciones_previas:
            logger.warning('Hay %d asignacion(es) previa(s)', asignaciones_previas.count())

        logger.info('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                    tipo, cuatrimestre, anno)

        turnos = Mapeos.encuesta_tipo_turno(tipo).filter(anno=anno, cuatrimestre=cuatrimestre)
        preferencias = Preferencia.objects.all()

        # Obs: esta línea de log no tiene en cuenta los docentes ya distribuidos
        # ni las necesidades de los turnos (que pueden ser 0 o mayores que 1).
        logger.info('%d docentes, %d turnos, %d preferencias',
                    docentes.count(), turnos.count(), preferencias.count())
        hay_errores = False

        docentes_cargas = Mapeos.docentes_y_cargas(tipo, anno_cuat)

        cargas = {c
                  for d_cargas in docentes_cargas.values()
                  for c in d_cargas}
        # TODO: chequear que no hay dos asignaciones con la misma carga
        cargas_distribuidas = {a.carga for a in asignaciones_previas}
        cargas_a_distribuir = cargas - cargas_distribuidas
        sources = {str(c.id): 1 for c in cargas_a_distribuir}

        asignaciones_por_turno = Counter(a.turno for a in asignaciones_previas)
        targets = {}
        for turno in turnos:
            necesidad = Mapeos.necesidades(turno, tipo) - asignaciones_por_turno.get(turno, 0)
            if necesidad > 0:
                targets[str(turno.id)] = necesidad
            elif necesidad < 0:
                messages.error(request, f'Hay demasiados docentes asignados al turno {turno}')
                hay_errores = True

        if hay_errores:
            context = {
                    'annos': [anno],
                    'cuatrimestres': [Cuatrimestres[cuatrimestre]],
                    'tipos': [TipoDocentes[tipo]],
                    'intento': intento}
            return render(request, 'dborrador/distribuir.html', context)

        pesos = []
        for carga in cargas_a_distribuir:
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
                    logger.debug('Tengo una preferencia de %s para %s pero no se está distribuyendo ese turno',
                                 preferencia.preferencia.docente, preferencia.preferencia.turno)

        wmap = allocating.ListWeightedMap(pesos)
        logger.info('Voy a hacer una distribución con %d cargas docentes y %d lugares en turnos',
                    sum(sources.values()), sum(targets.values()))

        # llamamos al distribuidor
        allocator = allocating.Allocator(sources, wmap, targets, limit_denominator=100)
        distribucion = allocator.get_best()
        logger.info('distribución obtenida (con ids): %s', distribucion)

        for carga_id, turno_id in distribucion:
            if carga_id is None or turno_id is None:
                continue

            carga = Carga.objects.get(pk=int(carga_id))
            turno = Turno.objects.get(pk=int(turno_id))
            asignacion, _ = Asignacion.objects.get_or_create(intento=intento, carga=carga, turno=turno)

        distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo, intento))
        return HttpResponseRedirect(distribucion_url)


def distribucion(request, anno, cuatrimestre, tipo, intento):
    if not 'fijar' in request.POST:
        try:
            proximo_intento = Asignacion.objects.all().aggregate(Max('intento'))['intento__max'] + 1
        except TypeError:  # None + 1 => TypeError
            logger.error('No hay docentes asignados todavía. Redirect a la página para distribuir')
            distribuir_url = reverse('dborrador:distribuir')
            return HttpResponseRedirect(distribuir_url)

        if 'cambiar' in request.POST:
            intento = int(request.POST['nuevo_intento'])
            distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo, intento))
            return HttpResponseRedirect(distribucion_url)

        materias_distribuidas = filtra_materias(anno=anno, cuatrimestre=cuatrimestre, intento=intento, tipo=tipo)
        context = {'materias': materias_distribuidas,
                   'anno': anno,
                   'cuatrimestre': cuatrimestre,
                   'tipo': tipo,
                   'intento': intento,
                   'nuevo_intento': proximo_intento}
        return render(request, 'dborrador/distribucion.html', context)

    else:
        fijados = request.POST.getlist('docente_fijado')
        proximo_intento = int(request.POST['proximo_intento'])
        for docente_id in fijados:
            docente = Docente.objects.get(pk=int(docente_id))
            turno = Asignacion.objects.filter(docente=docente, intento=intento).first().turno
            Asignacion.objects.create(docente=docente,
                                      turno=turno,
                                      intento=proximo_intento)

        distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo, intento))
        return HttpResponseRedirect(distribucion_url)


def filtra_materias(intento, tipo, **kwargs):
    docentes_distribuidos = Mapeos.docentes_de_tipo(tipo)
    turnos = Turno.objects.filter(**kwargs)
    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)
        materias_turnos = [
                (materia, Turno.objects.filter(materia=materia, **kwargs))
                for materia in tmaterias
                ]
        for materia, turnos in materias_turnos:
            for turno in turnos:
                asignaciones = [(a.carga.docente, a.carga.docente in docentes_distribuidos)
                                for a in turno.asignacion_set.all() if a.intento == intento]
                turno.docentes_asignados = asignaciones
        materias.append((obligatoriedad_largo, materias_turnos))

    return materias
