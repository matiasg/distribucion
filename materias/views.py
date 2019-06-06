from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import permission_required, login_required

import logging
logger = logging.getLogger(__name__)

from .models import Materia, Turno, Horario, Cuatrimestres, TipoMateria


def index(request):
    # Llamada sin anno y cuatrimestre. Tomamos el período actual
    # Fechas inventadas de período actual:
    # Cuatrimestre de Verano: 1/1 al 15/3
    # Primer Cuatrimestre: 16/3 al 31/7
    # Segundo: 1/8 al 31/12
    now = timezone.now()
    anno = now.year
    mes_dia = (now.month, now.day)
    if mes_dia < (3, 16):
        c = Cuatrimestres.V
    elif mes_dia < (8, 1):
        c = Cuatrimestres.P
    else:
        c = Cuatrimestres.S
    return por_anno_y_cuatrimestre(request, f'{anno}{c.value}')


def anno_y_cuatrimestre(anno_cuat):
    if not len(anno_cuat) == 5:
        raise ValueError(f'El formato es aaaac, 5 caracteres; {anno_cuat} tiene {len(anno_cuat)}')
    anno, cuat = anno_cuat[:4], anno_cuat[4:]
    try:
        anno = int(anno)
    except ValueError:
        raise ValueError(f'El año debe ser un número. Recibí {anno}')
    cuatris_dict = {c.value: c.name for c in Cuatrimestres}
    if not cuat.capitalize() in cuatris_dict:
        raise ValueError(f'El cuatrimestre debe ser 1, 2 o v. Recibí {cuat}')
    cuat = cuatris_dict[cuat.capitalize()]
    return anno, cuat


def por_anno_y_cuatrimestre(request, anno_cuat):
    try:
        anno, cuat = anno_y_cuatrimestre(anno_cuat)
    except ValueError as e:
        raise Http404(e.args[0])
    else:
        materias = filtra_materias(anno=anno, cuatrimestre=cuat)
        context = {'materias': materias}
        return render(request, 'materias/index.html', context)


def filtra_materias(**kwargs):
    turnos_filtrados = Turno.objects.filter(**kwargs)
    tipo_dict = {TipoMateria.B.name: 'Obligatorias',
                 TipoMateria.R.name: 'Optativas regulares',
                 TipoMateria.N.name: 'Optativas no regulares'}

    materias = []
    for tipo, tipo_largo in tipo_dict.items():
        tmaterias = Materia.objects.filter(obligatoriedad=tipo)
        materias_turnos = [
                (materia, sorted(turnos_filtrados.filter(materia=materia)))
                for materia in tmaterias
                ]
        materias.append((tipo_largo, materias_turnos))

    return materias

@login_required
@permission_required('materias.view_docente')
def administrar(request):
    if 'turnos_alumnos' in request.POST:
        anno = int(request.POST['anno'])
        cuatrimestre = request.POST['cuatrimestre']
        return HttpResponseRedirect(reverse('materias:administrar_alumnos', args=(anno, cuatrimestre)))
    elif 'turnos_docentes' in request.POST:
        anno = int(request.POST['anno'])
        cuatrimestre = request.POST['cuatrimestre']
        return HttpResponseRedirect(reverse('materias:administrar_docentes', args=(anno, cuatrimestre)))
    else:
        anno_actual = timezone.now().year
        context = {
            'annos': [anno_actual, anno_actual + 1],
            'cuatrimestres': [c for c in Cuatrimestres],
        }
        return render(request, 'materias/administrar.html', context=context)


def administrar_general(request, anno, cuatrimestre, key_to_field, url):
    if 'cambiar' in request.POST:
        with transaction.atomic():

            for modelo, modelo_key_to_field in key_to_field.items():

                if modelo == Turno:
                    objetos = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
                elif  modelo == Horario:
                    objetos = Horario.objects.filter(turno__anno=anno, turno__cuatrimestre=cuatrimestre)
                logger.info('modifico %d objetos tipo %s', objetos.count(), modelo)

                for objeto in objetos:
                    for page_field, (field, _type) in modelo_key_to_field.items():
                        page_field_objeto = f'{page_field}_{objeto.id}'
                        if _type in (int, str):
                            v = _type(request.POST[page_field_objeto])
                        elif _type is bool:
                            # checkbox aparece solo si está marcado
                            v = page_field_objeto in request.POST
                        setattr(objeto, field, v)
                        logger.debug('cambiando %s a obj. %s por %s', page_field, objeto, v)
                    objeto.save()


        return HttpResponseRedirect(reverse('materias:administrar'))

    else:
        materias = filtra_materias(anno=anno, cuatrimestre=cuatrimestre)
        context = {'anno': anno, 'cuatrimestre': cuatrimestre, 'materias': materias}
        return render(request, url, context)


@login_required
@permission_required('materias.add_turno')
def administrar_alumnos(request, anno, cuatrimestre):
    key_to_field = {Turno: {'alumnos': ('alumnos', int)},
                    Horario: {'aula': ('aula', str),
                              'pabellon': ('pabellon', int)}
                    }

    return administrar_general(request, anno, cuatrimestre, key_to_field, 'materias/administrar_alumnos.html')


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_docentes(request, anno, cuatrimestre):
    key_to_field = {Turno: {'necesidadprof': ('necesidad_prof', int),
                            'necesidadjtp': ('necesidad_jtp', int),
                            'necesidaday1': ('necesidad_ay1', int),
                            'necesidaday2': ('necesidad_ay2', int),
                            'dificil': ('dificil_de_cubrir', bool),
                            }
                    }
    return administrar_general(request, anno, cuatrimestre, key_to_field, 'materias/administrar_docentes.html')
