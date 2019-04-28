import logging
from collections import defaultdict, namedtuple

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required

from .models import Preferencia, Asignacion
from .misc import MapeosDistribucion
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
    tipo_name = request.POST['tipo']
    tipo = TipoDocentes[tipo_name]
    return int(anno), cuatrimestre, tipo

def index(request):
    try:
        anno, cuatrimestre, tipo = _anno_cuat_tipo_de_request(request)
        intento = request.POST['intento']
        fijar_url = reverse('dborrador:fijar', args=(anno, cuatrimestre, tipo.name, intento))
        return HttpResponseRedirect(fijar_url)
    except KeyError:
        return render(request, 'dborrador/base.html', _anno_cuat_tipos_context())

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


@login_required
@permission_required('dborrador.add_asignacion')
def distribuir(request, anno, cuatrimestre, tipo, intento):
    logger.info('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                tipo, cuatrimestre, anno)

    tipo = TipoDocentes[tipo]
    anno_cuat = AnnoCuatrimestre(anno, cuatrimestre)
    cargas_a_distribuir = MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(tipo, anno_cuat, intento)
    sources = {str(c.id): 1 for c in cargas_a_distribuir}

    necesidades_no_cubiertas = MapeosDistribucion.necesidades_no_cubiertas(tipo, anno_cuat, intento)
    targets = {}
    hay_errores = False
    for turno, necesidad in necesidades_no_cubiertas.items():
        if necesidad > 0:
            targets[str(turno.id)] = necesidad
        elif necesidad < 0:
            messages.error(request, f'Hay demasiados docentes asignados al turno {turno}')
            hay_errores = True

    if hay_errores:
        context = {
                'annos': [anno],
                'cuatrimestres': [Cuatrimestres[cuatrimestre]],
                'tipos': tipo,
                'intento': intento}
        return render(request, 'dborrador/distribuir.html', context)

    logger.info('Hay que distribuir %d cargas docentes y hay %d necesidades.',
                len(cargas_a_distribuir), sum(necesidades_no_cubiertas.values()))

    preferencias = Preferencia.objects.all()
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

    distribucion_url = reverse('dborrador:fijar', args=(anno, cuatrimestre, tipo.name, intento))
    return HttpResponseRedirect(distribucion_url)


def distribucion(request, anno, cuatrimestre, tipo, intento):
    tipo = TipoDocentes[tipo.upper()]  # TODO: cambiar argumento a tipo_name
    if not 'fijar' in request.POST:
        try:
            proximo_intento = Asignacion.objects.all().aggregate(Max('intento'))['intento__max'] + 1
        except TypeError:  # None + 1 => TypeError
            logger.error('No hay docentes asignados todavía. Redirect a la página para distribuir')
            distribuir_url = reverse('dborrador:distribuir')
            return HttpResponseRedirect(distribuir_url)

        if 'cambiar' in request.POST:
            intento = int(request.POST['nuevo_intento'])
            distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo.name, intento))
            return HttpResponseRedirect(distribucion_url)

        problemas = MapeosDistribucion.chequeo(tipo, AnnoCuatrimestre(anno, cuatrimestre), intento)
        context = materias_distribuidas_dict(anno=anno, cuatrimestre=cuatrimestre, intento=intento, tipo=tipo)
        context['nuevo_intento'] = proximo_intento
        context['problemas'] = problemas
        return render(request, 'dborrador/distribucion.html', context)

    else:
        fijadas = request.POST.getlist('asignacion_fijada')
        proximo_intento = int(request.POST['proximo_intento'])
        for asignacion_id in fijadas:
            asignacion = Asignacion.objects.get(pk=int(asignacion_id))
            Asignacion.objects.create(carga=asignacion.carga,
                                      turno=asignacion.turno,
                                      intento=proximo_intento)
            logger.info('Asignacion fijada para %s en %s (intento %d)',
                        asignacion.carga.docente, asignacion.turno, proximo_intento)

        distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, tipo.name, intento))
        return HttpResponseRedirect(distribucion_url)


def materias_distribuidas_dict(anno, cuatrimestre, intento, tipo):
    return {'materias': filtra_materias(anno=anno, cuatrimestre=cuatrimestre, intento=intento, tipo=tipo),
            'anno': anno,
            'cuatrimestre': cuatrimestre,
            'tipo': tipo.name,
            'intento': intento}

def filtra_materias(anno, cuatrimestre, intento, tipo, **kwargs):
    cargas = Mapeos.cargas(tipo, AnnoCuatrimestre(anno, cuatrimestre))

    turnos = Turno.objects.filter(**kwargs)
    obligatoriedades = {TipoMateria.B.name: 'Obligatorias',
                        TipoMateria.R.name: 'Optativas regulares',
                        TipoMateria.N.name: 'Optativas no regulares'}

    materias = []
    for obligatoriedad, obligatoriedad_largo in obligatoriedades.items():
        tmaterias = Materia.objects.filter(obligatoriedad=obligatoriedad)
        materias_turnos = [
                (materia, Turno.objects.filter(materia=materia, anno=anno, cuatrimestre=cuatrimestre))
                for materia in tmaterias
                ]
        #  TODO: esto se usa para ver distribucion pero no para fijar distribucion
        for materia, turnos in materias_turnos:
            for turno in turnos:
                asignaciones = [(a, a.carga in cargas)
                                for a in turno.asignacion_set.all() if a.intento == intento]
                turno.cargas_asignadas = asignaciones

        materias.append((obligatoriedad_largo, materias_turnos))

    return materias


def fijar(request, anno, cuatrimestre, tipo, intento):
    if 'nuevo_intento' in request.POST:
        intento = int(request.POST['nuevo_intento'])

    tipo = TipoDocentes[tipo]

    if 'fijar' in request.POST:
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
            if k.startswith('cambioen'):
                _, turno_id, carga_id = k.split('_')
                turno = Turno.objects.get(pk=int(turno_id))
                carga = Carga.objects.get(pk=int(carga_id))
                nueva_carga_id = int(val)
                if nueva_carga_id < 0:  # hay que borrar la asignación
                    asignaciones, _ = Asignacion.objects.filter(carga=carga, turno=turno, intento=intento).delete()
                    logger.info('Borré %d asignación(es) para %s en %s', asignaciones, carga.docente, turno)

    def _append_dicts(*dicts):
        ret = defaultdict(list)
        for d in dicts:
            for k, l in d.items():
                ret[k].append(l)
        return ret

    context = materias_distribuidas_dict(anno, cuatrimestre, intento, tipo)
    ac = AnnoCuatrimestre(anno, cuatrimestre)

    otro_tipo = _append_dicts(Mapeos.cargas_asignadas_en(ac), MapeosDistribucion.asignaciones_otro_tipo(ac))
    este_tipo = MapeosDistribucion.asignaciones_para_intento(ac, intento)
    necesidades_no_cubiertas = MapeosDistribucion.necesidades_tipo_no_cubiertas_en(tipo, ac, intento)
    # si queremos fijar docentes al intento 0, tienen que aparecer en este_tipo, no en este_tipo_fijo
    este_tipo_fijo = MapeosDistribucion.asignaciones_fijas(ac) if intento > 0 else defaultdict(list)

    ### XXX: este masajeo hay que refactorizarlo unificando bien con filtra_materias()
    DatosDeTurno = namedtuple('DDT', ['asignaciones_otro_tipo', 'asignaciones_este_tipo_fijo', 'asignaciones_este_tipo',
                                      'necesidades_no_cubiertas'])
    for obligatoriedad, materias_turnos in context['materias']:
        for materia, turnos in materias_turnos:
            for turno in turnos:
                datos = DatosDeTurno(otro_tipo[turno], este_tipo_fijo[turno], este_tipo[turno],
                                     necesidades_no_cubiertas[turno])
                turno.datos = datos

    cargas_a_distribuir = MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(tipo, ac, intento)
    context.update({'cargas_a_distribuir': cargas_a_distribuir})

    # TODO: si hay docentes distribuidos más que sus cargas o turnos cubiertos de más hay que tirar excepción
    context['problemas'] = MapeosDistribucion.chequeo(tipo, ac, intento, este_tipo_fijo, este_tipo)

    return render(request, 'dborrador/fijar.html', context)
