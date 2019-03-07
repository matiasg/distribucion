import logging

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .models import Preferencia, Asignacion
from materias.models import Turno, Cuatrimestres, choice_enum
from encuestas.models import PreferenciasDocente
from encuestas.views import Mapeos

from allocation import allocating


logger = logging.getLogger(__name__)


def index(request):
    raise Http404('Todavía no hay contenido para esta página')


def copiar_anno_y_cuatrimestre(anno, cuatrimestre):
    prefs_anno_cuat = PreferenciasDocente.objects.filter(
                                turno__anno=anno, turno__cuatrimestre=cuatrimestre)
    for pd in prefs_anno_cuat:
        pref, creada = Preferencia.objects.get_or_create(preferencia=pd)
        if creada:
            logger.debug('copié %s', pd)


def preparar(request):
    try:
        anno = request.POST['anno']
        cuatrimestre = request.POST['cuatrimestre']
        logger.info('copiando %s y %s', anno, cuatrimestre)
        copiar_anno_y_cuatrimestre(anno, cuatrimestre)
        return HttpResponseRedirect(reverse('dborrador:index'))
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
        logger.warning('comienzo una distribución para docentes tipo %s, cuatrimestre %s, año %s',
                    tipo, cuatrimestre, anno)

        docentes = Mapeos.docentes(tipo)
        turnos = Mapeos.encuesta_tipo_turno(tipo)
        preferencias = Preferencia.objects.all()

        sources = {str(d.id): d.cargas for d in docentes}

        necesidad_indice = 'PJA'.index(tipo)
        targets = {t.id: int(t.necesidades.split(',')[necesidad_indice]) for t in turnos}

        pesos = [{'from': str(p.preferencia.docente.id), 'to': p.preferencia.turno.id, 'weight': p.preferencia.peso}
                 for p in preferencias]
        wmap = allocating.WeightedMap(pesos)

        allocator = allocating.Allocator(sources, wmap, targets)
        distribucion = allocator.get_best()
        logger.info('te conseguí esto: %s', distribucion)

        return HttpResponseRedirect(reverse('dborrador:index'))

    except KeyError:
        anno_actual = timezone.now().year
        context = {
                'annos': [anno_actual, anno_actual + 1],
                'cuatrimestres': [c for c in Cuatrimestres],
                'tipos': ['P', 'J', 'A']}
        return render(request, 'dborrador/distribuir.html', context)

