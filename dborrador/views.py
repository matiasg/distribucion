import logging

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .models import Preferencia, Asignacion
from materias.models import (Turno, Docente, Materia, CuatrimestreDocente,
                             Cuatrimestres, TipoMateria, choice_enum)
from encuestas.models import PreferenciasDocente
from encuestas.views import TipoDocentes, Mapeos

from allocation import allocating


logger = logging.getLogger(__name__)


class MapeosDistribucion:

    @staticmethod
    def necesidades(turno, tipo_docente):
        if tipo_docente == TipoDocentes.P.name:
            return turno.necesidad_prof
        elif tipo_docente == TipoDocentes.J.name:
            return turno.necesidad_jtp
        elif tipo_docente == TipoDocentes.A1.name:
            return turno.necesidad_ay1
        else:
            return turno.necesidad_ay2


def index(request):
    raise Http404('Todavía no hay contenido para esta página')


def copiar_anno_y_cuatrimestre(anno, cuatrimestre, tipo):
    '''devuelve: (prefs copiadas, prefs ya existentes) '''
    copiadas = 0
    existentes = 0

    for docente in Mapeos.docentes(tipo):
        prefs = PreferenciasDocente.objects.filter(turno__anno=anno, turno__cuatrimestre=cuatrimestre,
                                                   docente=docente)
        peso_total = sum(pref.peso for pref in prefs)
        logger.debug('considerando %d prefs para %s. Peso total: %s', len(prefs), docente, peso_total)

        for pref in prefs:
            pref_copia, creada = Preferencia.objects.get_or_create(preferencia=pref,
                                                                   defaults={'peso_normalizado': pref.peso})
            pref_copia.peso_normalizado = pref.peso / peso_total if peso_total else 1 / len(prefs)
            pref_copia.save()
            if creada:
                logger.debug('copié %s -- %s --> %s',
                             pref.docente.nombre, pref_copia.peso_normalizado, pref.turno)
                copiadas += 1
            else:
                existentes += 1

    return copiadas, existentes


def preparar(request):
    try:
        anno = request.POST['anno']
        cuatrimestre = request.POST['cuatrimestre']
        tipo = request.POST['tipo']
        logger.info('copiando %s y %s para docents tipo %s', anno, cuatrimestre, tipo)

        copiadas, existentes = copiar_anno_y_cuatrimestre(anno, cuatrimestre, tipo)
        context = {'copiadas': copiadas, 'existentes': existentes}
        return render(request, 'dborrador/despues_de_preparar.html', context)
    except KeyError:
        anno_actual = timezone.now().year
        context = {
                'annos': [anno_actual, anno_actual + 1],
                'cuatrimestres': [c for c in Cuatrimestres],
                'tipos': [t for t in TipoDocentes]}
        return render(request, 'dborrador/elegir_ac.html', context)


def distribuir(request):
    try:
        anno = request.POST['anno']
        cuatrimestre = request.POST['cuatrimestre']
        tipo = request.POST['tipo']
        intento = int(request.POST['intento'])

    except KeyError:
        anno_actual = timezone.now().year
        context = {
                'annos': [anno_actual, anno_actual + 1],
                'cuatrimestres': [c for c in Cuatrimestres],
                'tipos': [t for t in TipoDocentes],
                'intento': 1}
        return render(request, 'dborrador/distribuir.html', context)

    else:
        asignaciones_previas = Asignacion.objects.filter(intento=intento)
        if asignaciones_previas:
            logger.warning('Hay %d asignaciones previas', len(asignaciones_previas))

        logger.info('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                    tipo, cuatrimestre, anno)

        docentes = Mapeos.docentes(tipo)
        turnos = Mapeos.encuesta_tipo_turno(tipo).filter(anno=anno, cuatrimestre=cuatrimestre)
        preferencias = Preferencia.objects.all()

        logger.info('%d docentes, %d turnos, %d preferencias', len(docentes), len(turnos), len(preferencias))

        info_cuatri = CuatrimestreDocente.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
        sources = dict()
        for d in docentes:
            info_doc = info_cuatri.filter(docente=d).first()
            if info_doc is not None:
                sources[str(d.id)] = info_doc.cargas

        targets = {}
        for turno in turnos:
            necesidad = MapeosDistribucion.necesidades(turno, tipo)
            necesidad -= len(asignaciones_previas.filter(turno=turno))
            targets[str(turno.id)] = necesidad

        pesos = [{'from': str(p.preferencia.docente.id),
                  'to': str(p.preferencia.turno.id),
                  'weight': p.peso_normalizado}
                 for p in preferencias]
        wmap = allocating.ListWeightedMap(pesos)

        # llamamos al distribuidor
        allocator = allocating.Allocator(sources, wmap, targets, limit_denominator=100)
        distribucion = allocator.get_best()
        logger.info('distribución obtenida (con ids): %s', distribucion)

        for docente_id, turno_id in distribucion:
            if turno_id is None:
                continue
            if docente_id is None:
                continue

            docente = Docente.objects.get(pk=int(docente_id))
            turno = Turno.objects.get(pk=int(turno_id))
            asignacion, _ = Asignacion.objects.get_or_create(
                                        intento=intento, docente=docente, turno=turno)

        distribucion_url = reverse('dborrador:distribucion', args=(anno, cuatrimestre, intento))
        return HttpResponseRedirect(distribucion_url)


def distribucion(request, anno, cuatrimestre, intento):
    try:
        intento = int(request.POST['nuevo_intento'])
    except:
        pass
    finally:
        materias_distribuidas = filtra_materias(anno=anno, cuatrimestre=cuatrimestre, intento=intento)
        context = {'materias': materias_distribuidas,
                   'anno': anno,
                   'cuatrimestre': cuatrimestre,
                   'intento': intento}
        return render(request, 'dborrador/distribucion.html', context)


def filtra_materias(intento, **kwargs):
    turnos = Turno.objects.filter(**kwargs)
    tipo_dict = {TipoMateria.B.name: 'Obligatorias',
                 TipoMateria.R.name: 'Optativas regulares',
                 TipoMateria.N.name: 'Optativas no regulares'}

    materias = []
    for tipo, tipo_largo in tipo_dict.items():
        tmaterias = Materia.objects.filter(obligatoriedad=tipo)
        materias_turnos = [
                (materia, Turno.objects.filter(materia=materia, **kwargs))
                for materia in tmaterias
                ]
        for materia, turnos in materias_turnos:
            for turno in turnos:
                asignaciones = [a for a in turno.asignacion_set.all() if a.intento == intento]
                turno.docentes_asignados = ' - '.join([a.docente.nombre for a in asignaciones])
        materias.append((tipo_largo, materias_turnos))

    return materias
