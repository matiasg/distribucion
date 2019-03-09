import logging

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .models import Preferencia, Asignacion
from materias.models import Turno, Docente, Materia, Cuatrimestres, TipoMateria, choice_enum
from encuestas.models import PreferenciasDocente
from encuestas.views import Mapeos

from allocation import allocating


logger = logging.getLogger(__name__)


def index(request):
    raise Http404('Todavía no hay contenido para esta página')


def copiar_anno_y_cuatrimestre(anno, cuatrimestre):
    '''devuelve: (prefs copiadas, prefs ya existentes) '''
    prefs_anno_cuat = PreferenciasDocente.objects.filter(
                                turno__anno=anno, turno__cuatrimestre=cuatrimestre)
    preferencias_copiadas = 0
    for pd in prefs_anno_cuat:
        pref, creada = Preferencia.objects.get_or_create(preferencia=pd)
        if creada:
            logger.debug('copié %s -- %s --> %s', pd.docente.nombre, pd.peso, pd.turno)
            preferencias_copiadas += 1

    return preferencias_copiadas, len(prefs_anno_cuat) - preferencias_copiadas


def preparar(request):
    try:
        anno = request.POST['anno']
        cuatrimestre = request.POST['cuatrimestre']
        logger.info('copiando %s y %s', anno, cuatrimestre)
        copiadas, existentes = copiar_anno_y_cuatrimestre(anno, cuatrimestre)
        context = {'copiadas': copiadas, 'existentes': existentes}
        return render(request, 'dborrador/despues_de_preparar.html', context)
    except KeyError:
        anno_actual = timezone.now().year
        context = {
                'annos': [anno_actual, anno_actual + 1],
                'cuatrimestres': [c for c in Cuatrimestres]}
        return render(request, 'dborrador/elegir_ac.html', context)


def distribuir(request):
    try:
        anno = request.POST['anno']
        cuatrimestre = request.POST['cuatrimestre']
        tipo = request.POST['tipo']
        intento = 1

    except KeyError:
        anno_actual = timezone.now().year
        context = {
                'annos': [anno_actual, anno_actual + 1],
                'cuatrimestres': [c for c in Cuatrimestres],
                'tipos': ['P', 'J', 'A']}
        return render(request, 'dborrador/distribuir.html', context)

    else:
        logger.warning('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                    tipo, cuatrimestre, anno)

        docentes = Mapeos.docentes(tipo)
        turnos = Mapeos.encuesta_tipo_turno(tipo)
        preferencias = Preferencia.objects.all()

        logger.info('%d docentes, %d turnos, %d preferencias', len(docentes), len(turnos), len(preferencias))

        sources = {str(d.id): d.cargas for d in docentes}

        necesidad_indice = 'PJA'.index(tipo)
        targets = {t.id: int(t.necesidades.split(',')[necesidad_indice]) for t in turnos}

        pesos = [{'from': str(p.preferencia.docente.id), 'to': p.preferencia.turno.id, 'weight': p.preferencia.peso}
                 for p in preferencias]
        wmap = allocating.WeightedMap(pesos)

        allocator = allocating.Allocator(sources, wmap, targets)
        distribucion = allocator.get_best()
        logger.info('distribución obtenida (con ids): %s', distribucion)

        for docente_id, turno_id in distribucion:
            if turno_id is None:
                continue
            if docente_id is None:
                continue

            docente = Docente.objects.get(pk=int(docente_id))
            turno = Turno.objects.get(pk=turno_id)
            asignacion, _ = Asignacion.objects.get_or_create(
                                        intento=intento, docente=docente, turno=turno)

        context = {'materias': filtra_materias(anno=anno, cuatrimestre=cuatrimestre)}
        return render(request, 'dborrador/distribucion.html', context)


def filtra_materias(**kwargs):
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
                turno.docentes_asignados = ' - '.join([a.docente.nombre for a in turno.asignacion_set.all()])
        materias.append((tipo_largo, materias_turnos))

    return materias
