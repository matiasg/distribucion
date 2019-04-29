from django.http import Http404
from django.shortcuts import render
from django.db import transaction
from django.contrib.auth.decorators import permission_required, login_required

from .models import Materia, Turno, Horario, Cuatrimestres, TipoMateria


def index(request):
    materias = filtra_materias()
    context = {'materias': materias}
    return render(request, 'materias/index.html', context)


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
        materias.append((tipo_largo, materias_turnos))

    return materias


@login_required
@permission_required('dborrador.add_turno')
def administrar(request):
    return render(request, 'materias/administrar.html')


@login_required
@permission_required('dborrador.add_turno')
def administrar_turnos(request, anno, cuatrimestre):
    if 'cambiar' in request.POST:
        key_to_field = {'alumnos': 'alumnos',
                        'necesidadprof': 'necesidad_prof',
                        'necesidadjtp': 'necesidad_jtp',
                        'necesidaday1': 'necesidad_ay1',
                        'necesidaday2': 'necesidad_ay2',
                        }
        with transaction.atomic():
            for k, v in request.POST.items():
                if k.startswith('alumnos') or k.startswith('necesidad'):
                    k_field, turno_id = k.split('_')
                    turno = Turno.objects.get(pk=int(turno_id))
                    setattr(turno, key_to_field[k_field], int(v))
                    turno.save()
        return render(request, 'materias/administrar.html')

    else:
        materias = filtra_materias(anno=anno, cuatrimestre=cuatrimestre)
        context = {'anno': anno, 'cuatrimestre': cuatrimestre, 'materias': materias}
        return render(request, 'materias/administrar_turnos.html', context)
