from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.contrib.auth.decorators import permission_required, login_required
from django.db.models import Max, Min

from locale import strxfrm
from collections import Counter, namedtuple, defaultdict
import re
import logging
logger = logging.getLogger(__name__)

from .models import (Materia, AliasDeMateria, Turno, Horario, Cuatrimestres, TipoMateria, TipoTurno,
                     TipoDocentes, Docente, CargoDedicacion, Carga, Pabellon, Dias, choice_enum,)
from .misc import Mapeos, NoTurno
from .forms import DocenteForm, MateriaForm
from encuestas.models import PreferenciasDocente, OtrosDatos, CargasPedidas

TURNOS_MAX = 4

TIPO_DICT = {TipoMateria.B: 'Obligatorias',
             TipoMateria.R: 'Optativas regulares',
             TipoMateria.N: 'Optativas no regulares'}


def anno_y_cuatrimestre_actuales():
    # Fechas inventadas de período actual:
    # Cuatrimestre de Verano: 1/1 al 15/3
    # Primer Cuatrimestre: 16/3 al 31/7
    # Segundo: 1/8 al 31/12
    now = timezone.now()
    anno = now.year
    mes_dia = (now.month, now.day)
    if mes_dia < (3, 16):
        cuatrimestre = Cuatrimestres.V
    elif mes_dia < (8, 1):
        cuatrimestre = Cuatrimestres.P
    else:
        cuatrimestre = Cuatrimestres.S
    return anno, cuatrimestre


def index(request):
    # Llamada sin anno y cuatrimestre. Tomamos el período actual
    anno, c = anno_y_cuatrimestre_actuales()
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
        raise ValueError(f'El cuatrimestre debe ser 1, 2 o V. Recibí {cuat}')
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

    materias = []
    for tipo, tipo_largo in TIPO_DICT.items():
        tmaterias = Materia.objects.filter(obligatoriedad=tipo.name)
        materias_turnos = [
                (materia, sorted(turnos_filtrados.filter(materia=materia)))
                for materia in tmaterias
                ]
        materias.append((tipo_largo, materias_turnos))

    return materias


def pagina_de_administrar_con_ac(request, anno, cuatrimestre):
    primer_anno = Turno.objects.aggregate(Min('anno'))['anno__min']
    ultimo_anno = Turno.objects.aggregate(Max('anno'))['anno__max']
    annos = list(range(primer_anno, ultimo_anno + 2))
    cuatrimestres = list(Cuatrimestres)

    return render(request, 'materias/administrar.html', context={'annos': annos,
                                                                 'cuatrimestres': cuatrimestres,
                                                                 'anno': anno, 'cuatrimestre': cuatrimestre})


def anno_y_cuatrimestre_de_request(request):
    anno = request.session.get('anno', None)
    cuatrimestre = request.session.get('cuatrimestre', None)

    if request.method == 'POST':
        anno = request.POST.get('anno', anno)
        cuatrimestre = request.POST.get('cuatrimestre', cuatrimestre)

    if anno is None:
        anno, cuatrimestre = anno_y_cuatrimestre_actuales()
    else:
        anno = int(anno)
        request.session['anno'] = anno
        request.session['cuatrimestre'] = cuatrimestre

    return anno, cuatrimestre


@login_required
@permission_required('materias.view_docente')
def administrar(request):
    anno, cuatrimestre = anno_y_cuatrimestre_de_request(request)

    if request.method == 'POST':
        if 'turnos_alumnos' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_alumnos', args=(anno, cuatrimestre)))
        elif 'turnos_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_necesidades_docentes', args=(anno, cuatrimestre)))
        elif 'exportar_informacion' in request.POST:
            return HttpResponseRedirect(reverse('materias:exportar_informacion', args=(anno, cuatrimestre)))
        elif 'generar_cuatrimestre' in request.POST:
            return HttpResponseRedirect(reverse('materias:generar_cuatrimestre', args=(anno, cuatrimestre)))
        elif 'administrar_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_docentes'))
        elif 'retocar_materias' in request.POST:
            return HttpResponseRedirect(reverse('materias:retocar_materias'))
        elif 'ver_materias' in request.POST:
            return HttpResponseRedirect(reverse('materias:por_anno_y_cuatrimestre',
                                                args=(f'{anno}{Cuatrimestres[cuatrimestre].value}',)))
        elif 'cargas_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_cargas_docentes', args=(anno, cuatrimestre)))
        elif 'cargas_docentes_anuales' in request.POST:
            return HttpResponseRedirect(reverse('materias:cargas_docentes_anuales', args=(anno,)))
        elif 'cargas_docentes_publicadas' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_cargas_publicadas', args=(anno, cuatrimestre)))
        elif 'administrar_encuestas' in request.POST:
            return HttpResponseRedirect(reverse('encuestas:administrar_habilitadas'))
        elif 'dborrador' in request.POST:
            return HttpResponseRedirect(reverse('dborrador:empezar'))

    return pagina_de_administrar_con_ac(request, anno, cuatrimestre)


def administrar_general(request, anno, cuatrimestre, key_to_field, url, seccion='materias', **kwargs):
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
                        if _type is bool:
                            # checkbox aparece solo si está marcado
                            v = page_field_objeto in request.POST
                        else:
                            v = _type(request.POST[page_field_objeto])
                        setattr(objeto, field, v)
                        logger.debug('cambiando %s a obj. %s por %s', page_field, objeto, v)
                    objeto.save()

        return HttpResponseRedirect(f"{reverse('materias:administrar')}#{seccion}")

    else:
        materias = filtra_materias(anno=anno, cuatrimestre=cuatrimestre)
        materias_con_turnos = {turno.materia for turno in Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)}
        materias_sin_turnos = set(Materia.objects.all()) - materias_con_turnos
        materias_sin_turnos = sorted(materias_sin_turnos, key=lambda m: (TipoMateria[m.obligatoriedad], strxfrm(m.nombre)))

        context = {'anno': anno,
                   'cuatrimestre': Cuatrimestres[cuatrimestre],
                   'materias': materias,
                   'materias_sin_turnos': materias_sin_turnos,
                   'pabellones': list(Pabellon)}
        context.update(kwargs)
        return render(request, url, context)


@login_required
@permission_required('materias.add_turno')
def administrar_alumnos(request, anno, cuatrimestre):
    key_to_field = {Turno: {'alumnos': ('alumnos', int)},
                    Horario: {'aula': ('aula', str),
                              'pabellon': ('pabellon', str)}
                    }

    return administrar_general(request, anno, cuatrimestre, key_to_field,
                               'materias/administrar_alumnos.html', seccion='materias')


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_necesidades_docentes(request, anno, cuatrimestre):
    key_to_field = {Turno: {'alumnos': ('alumnos', int),
                            'necesidadprof': ('necesidad_prof', int),
                            'necesidadjtp': ('necesidad_jtp', int),
                            'necesidaday1': ('necesidad_ay1', int),
                            'necesidaday2': ('necesidad_ay2', int),
                            'dificil': ('dificil_de_cubrir', bool),
                            }
                    }

    turnos = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
    necesidades = {tipo: sum(Mapeos.necesidades(turno, tipo) for turno in turnos)
                   for tipo in TipoDocentes}

    cargas = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
    recursos = Counter(Mapeos.tipo_de_carga(carga) for carga in cargas)

    necesidades_y_recursos = {tipo: (necesidades[tipo], recursos[tipo]) for tipo in TipoDocentes}

    return administrar_general(request, anno, cuatrimestre, key_to_field, 'materias/administrar_necesidades_docentes.html',
                               seccion='docentes', necesidades_y_recursos=necesidades_y_recursos)


@login_required
@permission_required('materias.add_turno')
def agregar_materia(request):
    nueva_materia, creada = Materia.objects.get_or_create(nombre='__ nueva materia __')
    return HttpResponseRedirect(reverse('materias:modificar_materia', args=(nueva_materia.id,)))


@login_required
@permission_required('materias.add_turno')
def modificar_materia(request, materia_id):
    materia = Materia.objects.get(pk=materia_id)
    context = {
        'materia': materia,
    }
    if request.method == 'POST':
        if 'salvar' in request.POST:
            form = MateriaForm(request.POST, instance=materia)
            if form.is_valid():
                form.save()
                logger.info('salvé una materia modificada: %s', materia)
                return HttpResponseRedirect(reverse('materias:retocar_materias'))
            else:
                logger.error(form.errors)
        elif 'borrar' in request.POST:
            borrado = materia.delete()
            logger.warning('borre la materia %s (objetos borrados: %s)', materia, borrado)
            return HttpResponseRedirect(reverse('materias:retocar_materias'))
    else:
        form = MateriaForm(instance=materia)
    context['form'] = form
    return render(request, 'materias/modificar_materia.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def cargas_docentes_anuales(request, anno):
    if request.method == 'POST':
        if 'salvar' in request.POST:
            reg = re.compile('^cargas_(\d+)_([a-zA-Z12]{6})_([VPS])$')
            with transaction.atomic():
                for carga_docid_cuat in request.POST:
                    m = reg.search(carga_docid_cuat)
                    if m:
                        docente_id = int(m.group(1))
                        docente = Docente.objects.get(pk=docente_id)
                        cargo = m.group(2)
                        cuatrimestre = m.group(3)

                        cantidad = int(request.POST[carga_docid_cuat])
                        actuales = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre, docente=docente, cargo=cargo)
                        a_generar = cantidad - actuales.count()

                        if a_generar < 0:
                            logger.warning('voy a borrar %d cargas de %s (%s) para el cuatrimestre %s', -a_generar, docente, cargo, cuatrimestre)
                            for c in range(-a_generar):
                                actuales.last().delete()

                        elif a_generar > 0:
                            logger.warning('voy a generar %d cargas de %s (%s) para el cuatrimestre %s', a_generar, docente, cargo, cuatrimestre)
                            for c in range(a_generar):
                                Carga.objects.create(anno=anno, cuatrimestre=cuatrimestre, docente=docente, cargo=cargo)

            return HttpResponseRedirect(f"{reverse('materias:administrar')}#docentes")

        elif 'generar' in request.POST:
            for docente in Docente.objects.filter(cargos__len__gt=0):
                logger.info('le genero cargas a %s para %d', docente, anno)
                for cargo in docente.cargos:
                    Carga.objects.create(docente=docente, anno=anno, cuatrimestre=Cuatrimestres.P.name, cargo=cargo)
                    Carga.objects.create(docente=docente, anno=anno, cuatrimestre=Cuatrimestres.S.name, cargo=cargo)

            return HttpResponseRedirect(reverse('materias:cargas_docentes_anuales', args=(anno,)))

    else:
        cargas_anno = Carga.objects.filter(anno=anno)
        docentes_y_cargos = {(docente, cargo)
                             for docente in Docente.objects.filter(cargos__len__gt=0).all()
                             for cargo in docente.cargos}
        docentes_y_cargos |= {(carga.docente, carga.cargo) for carga in cargas_anno}
        por_tipo_cargo = {tipo: {(docente, cargo) for (docente, cargo) in docentes_y_cargos if Mapeos.tipos_de_cargo(cargo) == tipo}
                          for tipo in TipoDocentes}

        contados = {cuatrimestre: Counter((carga.docente, carga.cargo) for carga in cargas_anno.filter(cuatrimestre=cuatrimestre.name))
                    for cuatrimestre in Cuatrimestres}

        cargas = {tipo: {doc_cargo: [contados[cuat][doc_cargo]
                                     for cuat in (Cuatrimestres.V, Cuatrimestres.P, Cuatrimestres.S)]
                         for doc_cargo in sorted(por_tipo_cargo[tipo],
                                                 key=lambda dc: strxfrm(dc[0].apellido_nombre))}
                  for tipo in TipoDocentes}

        context = {
            'anno': anno,
            'cargas': cargas,
            'generar_cargas': cargas_anno.count() == 0,
            'tipos': list(TipoDocentes),
            'cuatrimestres': [Cuatrimestres.V, Cuatrimestres.P, Cuatrimestres.S],
        }
        return render(request, 'materias/cargas_docentes_anuales.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_cargas_docentes(request, anno, cuatrimestre):
    docentes_y_cargas_nuestras = {d: d.carga_set.filter(anno=anno, cuatrimestre=cuatrimestre) for d in Docente.objects.all()}
    # todos los docentes, con y sin cargas en este cuatrimestre
    docentes = Docente.objects.all()
    docentes_con_cargas = {d: cargas for d, cargas in docentes_y_cargas_nuestras.items()
                           if cargas.count() > 0}
    docentes_sin_cargas = sorted(set(docentes) - set(docentes_con_cargas),
                                 key=lambda d: d.na_apellido)
    # docentes con diferencias con la encuesta
    docentes_y_cargas_encuesta = {cp.docente: cp.cargas
                                  for cp in CargasPedidas.objects.filter(anno=anno, cuatrimestre=cuatrimestre).all()}
    # calculo diferencias contra encuesta
    diferencias_encuesta = {d: (len(docentes_y_cargas_nuestras[d]),
                                docentes_y_cargas_encuesta[d],
                                OtrosDatos.objects.filter(anno=anno, cuatrimestre__contains=cuatrimestre, docente=d).first())
                            for d in sorted(set(docentes_y_cargas_nuestras) & set(docentes_y_cargas_encuesta),
                                            key=lambda d: strxfrm(d.apellido_nombre))
                            if len(docentes_y_cargas_nuestras[d]) != docentes_y_cargas_encuesta[d]
                            }

    # calculo docentes que deberían haber completado encuesta y no completaron
    docentes_sin_distribuir = {d: cargas.filter(turno__isnull=True)
                               for d, cargas in docentes_y_cargas_nuestras.items()}
    docentes_con_encuesta = {pref.docente
                             for pref in PreferenciasDocente.objects.filter(turno__anno=anno, turno__cuatrimestre=cuatrimestre)}
    docentes_sin_encuesta = {d: cargas.count()
                             for d, cargas in docentes_sin_distribuir.items()
                             if cargas.count() > 0 and d not in docentes_con_encuesta}

    context = {'anno': anno,
               'cuatrimestre': Cuatrimestres[cuatrimestre],
               'docentes_con_cargas': docentes_con_cargas,
               'docentes_sin_cargas': docentes_sin_cargas,
               'diferencias_encuesta': diferencias_encuesta,
               'docentes_sin_encuesta': docentes_sin_encuesta,
               }

    return render(request, 'materias/administrar_cargas_docentes.html', context)

@login_required
@permission_required('dborrador.add_asignacion')
def administrar_cargas_de_un_docente(request, anno, cuatrimestre, docente_id):
    docente = Docente.objects.get(pk=docente_id)

    if 'salvar' in request.POST:
        for cargo_label in request.POST:
            if cargo_label.startswith('cargo_'):
                cargo = CargoDedicacion[cargo_label[-6:]]
                cantidad_que_le_dejamos = int(request.POST[cargo_label])
                cantidad_que_tiene = docente.carga_set.filter(anno=anno, cuatrimestre=cuatrimestre, cargo=cargo.name).count()
                logger.info('cargas %s', docente.carga_set.filter(anno=anno, cuatrimestre=cuatrimestre, cargo=cargo))
                logger.info('le dejamos %d, tiene %d', cantidad_que_le_dejamos, cantidad_que_tiene)

                if cantidad_que_le_dejamos > cantidad_que_tiene:
                    for i in range(cantidad_que_tiene, cantidad_que_le_dejamos):
                        Carga.objects.create(anno=anno, cuatrimestre=cuatrimestre, docente=docente, cargo=cargo.name)
                        logger.debug('generé una carga para %s con cargo %s', docente, cargo)

                elif cantidad_que_le_dejamos < cantidad_que_tiene:
                    for i in range(cantidad_que_le_dejamos, cantidad_que_tiene):
                        Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre, docente=docente, cargo=cargo.name).last().delete()
                        logger.debug('borré una carga para %s con cargo %s', docente, cargo)

                else:
                    logger.debug('no cambié la cantidad de cargas de %s con cargo %s', docente, cargo)

        return HttpResponseRedirect(reverse('materias:administrar_cargas_docentes', args=(anno, cuatrimestre)))

    else:
        try:
            cargas_pedidas = CargasPedidas.objects.get(anno=anno, cuatrimestre=cuatrimestre, docente=docente).cargas
            completo_la_encuesta = True
        except CargasPedidas.DoesNotExist:
            cargas_pedidas = 0
            completo_la_encuesta = False
        cargas = docente.carga_set.filter(anno=anno, cuatrimestre=cuatrimestre)
        cargas_por_tipo = dict(Counter(carga.cargo for carga in cargas))
        # Corrección para el caso en que un docente no tiene cargas de un cargo.
        # Esto pasa por ejemplo si hay diferencias entre docente.cargos y cargas.cargo
        for cargo in docente.cargos:
            if cargo not in cargas_por_tipo:
                cargas_por_tipo[cargo] = 0

        context = {
            'anno': anno,
            'cuatrimestre': cuatrimestre,
            'docente': docente,
            'cargas': cargas,
            'cargas_pedidas': cargas_pedidas,
            'cargas_por_tipo': cargas_por_tipo,
            'completo_la_encuesta': completo_la_encuesta,
        }
        return render(request, 'materias/administrar_cargas_un_docente.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_cargas_publicadas(request, anno, cuatrimestre):
    cargas_distribuidas = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre,
                                               turno__isnull=False).order_by('docente__na_apellido', 'docente__na_nombre')
    cargas_no_distribuidas = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre,
                                                  turno__isnull=True).order_by('docente__na_apellido', 'docente__na_nombre')
    docentes_con_cargo_sin_cargas = set(Docente.objects.filter(cargos__len__gt=0).all()) \
                                    - {c.docente for c in cargas_distribuidas} \
                                    - {c.docente for c in cargas_no_distribuidas}
    docentes_con_cargo_sin_cargas = sorted(docentes_con_cargo_sin_cargas, key=lambda d: strxfrm(f'{d.apellido_nombre}'))

    context = {
        'distribuidas': cargas_distribuidas,
        'no_distribuidas': cargas_no_distribuidas,
        'sin_cargas': docentes_con_cargo_sin_cargas,
        'anno': anno,
        'cuatrimestre': Cuatrimestres[cuatrimestre],
    }
    return render(request, 'materias/cambiar_cargas_docentes_publicadas.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def cambiar_una_carga_publicada(request, carga_id):
    carga = Carga.objects.get(pk=carga_id)
    anno = carga.anno
    cuatrimestre = carga.cuatrimestre

    if 'salvar' in request.POST:
        nuevo_turno_id = int(request.POST['turno'])
        if nuevo_turno_id < 0:
            logger.warning('Estoy quitando a %s de su asignación a %s', carga.docente, carga.turno)
            carga.turno = None
        else:
            nuevo_turno = Turno.objects.get(pk=nuevo_turno_id)
            logger.info('Le cambio la carga a %s de %s a %s', carga.docente, carga.turno, nuevo_turno)
            carga.turno = nuevo_turno
        carga.save()
        return HttpResponseRedirect(reverse('materias:administrar_cargas_publicadas',
                                            args=(anno, cuatrimestre)))
    else:
        cargo = carga.cargo
        turnos = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
        context = {'carga': carga,
                   'turnos': [NoTurno()] + list(turnos.order_by('materia', 'numero', 'tipo')),
                   }
        return render(request, 'materias/cambiar_una_carga_publicada.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def agregar_carga_y_distribuir(request, docente_id, anno, cuatrimestre):
    docente = Docente.objects.get(pk=docente_id)
    if request.method == 'POST':
        if 'cambiar' in request.POST:
            for carga in Carga.objects.filter(docente=docente, anno=anno, cuatrimestre=cuatrimestre).all():
                turno_id = int(request.POST[f'carga_{carga.id}'])
                carga.turno = Turno.objects.get(pk=turno_id) if turno_id >= 0 else None
                logger.debug('nuevo turno para %s: %s', docente, carga.turno)
                carga.save()
        elif 'cancelar' in request.POST:
            para_borrar = Carga.objects.filter(docente=docente, anno=anno, cuatrimestre=cuatrimestre, turno=None).all()
            logger.info('borro cargas: %s', para_borrar)
            para_borrar.delete()
        return HttpResponseRedirect(reverse('materias:administrar_cargas_publicadas', args=(anno, cuatrimestre)))
    else:
        cargas = []
        for cargo in docente.cargos:
            carga, creada = Carga.objects.get_or_create(docente=docente, cargo=cargo, anno=anno, cuatrimestre=cuatrimestre)
            if creada:
                logger.info('generé carga: %s', carga)
            cargas.append(carga)
        turnos = [NoTurno()] + list(Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre).order_by('materia', 'numero', 'tipo'))
        return render(request, 'materias/distribuir_cargas_de_docente.html',
                      {'docente': docente, 'cargas': cargas, 'turnos': turnos,
                       'anno': anno, 'cuatrimestre': Cuatrimestres[cuatrimestre]})



@login_required
@permission_required('materias.add_turno')
def agregar_turno(request, materia_id, tipo, anno, cuatrimestre):
    materia = Materia.objects.get(pk=materia_id)
    turnos = Turno.objects.filter(materia=materia, anno=anno, cuatrimestre=cuatrimestre)
    turnos_tipo = turnos.filter(tipo=tipo)
    numero_nuevo_turno = max(t.numero for t in turnos_tipo) + 1 if turnos_tipo.count() else 0
    turno = Turno.objects.create(materia=materia, anno=anno, cuatrimestre=cuatrimestre, tipo=tipo, numero=numero_nuevo_turno,
                                 necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
    return HttpResponseRedirect(reverse('materias:cambiar_turno', args=(turno.id,)))


@login_required
@permission_required('materias.add_turno')
def administrar_materia(request, materia_id, anno, cuatrimestre):
    for tipo in TipoTurno:
        boton = f'agregar_turno_{tipo.name}'
        if boton in request.POST:
            return agregar_turno(request, materia_id, tipo.name, anno, cuatrimestre)
    else:
        materia = Materia.objects.get(pk=materia_id)
        context = {
            'materia': materia,
            'turnos': sorted(Turno.objects.filter(materia=materia, anno=anno, cuatrimestre=cuatrimestre)),
            'anno': anno,
            'cuatrimestre': Cuatrimestres[cuatrimestre],
            'tipoturno': {t.name: t.value for t in TipoTurno},
        }
        return render(request, 'materias/administrar_materia.html', context)

def _turno_a_materia_args(turno):
    return (turno.materia.id, turno.anno, turno.cuatrimestre)

@login_required
@permission_required('materias.add_turno')
def borrar_turno(request, turno_id):
    turno = Turno.objects.get(pk=turno_id)
    args = _turno_a_materia_args(turno)
    turno.delete()
    return HttpResponseRedirect(reverse('materias:administrar_materia', args=args))


@login_required
@permission_required('materias.add_turno')
def cambiar_turno(request, turno_id):
    turno = Turno.objects.get(pk=turno_id)
    if 'cancelar' in request.POST:
        return HttpResponseRedirect(reverse('materias:administrar_materia', args=_turno_a_materia_args(turno)))

    elif 'cambiar' in request.POST:
        turno.numero = int(request.POST['numero_turno'])
        turno.subnumero = request.POST['subnumero_turno'].strip()
        turno.save()

        def dia_com_fin(pre_key):
            dia_value = request.POST[f'{pre_key}_dia']
            dia = Dias[dia_value]
            comienzo = parse_time(request.POST[f'{pre_key}_comienzo'])
            final = parse_time(request.POST[f'{pre_key}_final'])
            if comienzo is None or final is None:
                raise KeyError
            return dia, comienzo, final

        for horario in turno.horario_set.all():
            try:
                dia, comienzo, final = dia_com_fin(f'existente_{horario.id}')
                horario.dia = dia.name
                horario.comienzo = comienzo
                horario.final = final
                horario.save()
            except KeyError:
                pass

        for horario_agregado in range(TURNOS_MAX):
            try:
                dia, comienzo, final = dia_com_fin(f'nuevo_{horario_agregado}')
                horario = Horario.objects.create(dia=dia.name, comienzo=comienzo, final=final, turno=turno,
                                                 aula='', pabellon='')
            except KeyError:
                pass

    else:
        context = {
            'turno': turno,
            'horarios': sorted(turno.horario_set.all()),
            'turnosmax': TURNOS_MAX,
            'materia': turno.materia,
            'tipoturno': TipoTurno[turno.tipo],
            'dias': [d for d in Dias],
            'horas': [('', ''),
                      *((f'{hora:02d}:{minutos:02d}:00', f'{hora:02d}:{minutos:02d}')
                        for hora in range(6, 24) for minutos in (0, 30) ) ]
        }
        return render(request, 'materias/cambiar_turno.html', context)

    # return HttpResponseRedirect(reverse('materias:cambiar_turno', args=(turno_id,)))
    return HttpResponseRedirect(reverse('materias:administrar_materia', args=_turno_a_materia_args(turno)))


@login_required
@permission_required('materias.add_turno')
def borrar_horario(request, horario_id):
    horario = Horario.objects.get(pk=horario_id)
    turno = horario.turno
    horario.delete()
    return HttpResponseRedirect(reverse('materias:cambiar_turno', args=(turno.id,)))


@login_required
@permission_required('materias.add_turno')
def retocar_materias(request):
    if request.method == 'POST':

        if 'agreguemos' in request.POST:
            return HttpResponseRedirect(reverse('materias:agregar_materia'))

        para_juntar = {Materia.objects.get(pk=int(k.split('_')[-1]))
                       for k, v in request.POST.items()
                       if k.startswith('juntar')}

        if 'confirmar' in request.POST:
            logger.info('Materias para juntar %s', para_juntar)
            queda_id = int(request.POST['nombre'].split('_')[-1])
            queda = Materia.objects.get(pk=queda_id)

            with transaction.atomic():
                for materia in para_juntar:
                    if materia != queda:
                        for turno in materia.turno_set.all():
                            logger.info('cambio turno %s a %s', turno, queda)
                            turno.materia = queda
                            turno.save()
                        AliasDeMateria.objects.create(materia=queda, nombre=materia.nombre)
                        materia.delete()

            return HttpResponseRedirect(reverse('materias:retocar_materias'))

        else:
            if not para_juntar:
                logger.warning('pusieron juntar pero sin ninguna materia')
                return HttpResponseRedirect(reverse('materias:retocar_materias'))


            turnos = {materia: {(t.anno, t.cuatrimestre) for t in materia.turno_set.all()} for materia in para_juntar}
            turnos_planos = Counter(cuat for turno in turnos.values() for cuat in turno)
            turnos_juntos = set.union(*turnos.values())
            logger.info('Turnos juntos: %s', turnos_juntos)

            context = {
                'materias': para_juntar,
                'turnos': turnos,
                'turnos_juntos': sorted(turnos_juntos),
                'esta_bien': max(turnos_planos.values()) == 1 if turnos_planos else True,
            }
            return render(request, 'materias/confirmar_juntar_materias.html', context=context)

    else:
        context = {
            'materias': {TIPO_DICT[ob]: Materia.objects.filter(obligatoriedad=ob.name).order_by('nombre')
                         for ob in TipoMateria}
        }
        return render(request, 'materias/juntar_materias.html', context=context)



@login_required
@permission_required('materias.add_turno')
def exportar_informacion(request, anno, cuatrimestre):
    if 'info_anual' in request.POST:
        import xlwt
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="turnos_{anno}.xls"'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Distribucion')

        xlwt.add_palette_colour("verano", 0x21)
        wb.set_colour_RGB(0x21, 0xff, 0xff, 0xcc)
        xlwt.add_palette_colour("primero", 0x22)
        wb.set_colour_RGB(0x22, 0xcc, 0xff, 0x99)
        xlwt.add_palette_colour("segundo", 0x23)
        wb.set_colour_RGB(0x23, 0xdc, 0xe6, 0xf2)
        estilos = {
            Cuatrimestres.V: xlwt.easyxf('pattern: pattern solid, fore_colour verano'),
            Cuatrimestres.P: xlwt.easyxf('pattern: pattern solid, fore_colour primero'),
            Cuatrimestres.S: xlwt.easyxf('pattern: pattern solid, fore_colour segundo'),
        }

        def docentes_por_cargo(cargas):
            return ' - '.join(f'{c.docente.nombre} ({Mapeos.tipo_de_carga(c).name})'
                              for c in sorted(sorted(cargas, key=lambda c: strxfrm(c.docente.na_apellido)),
                                              key=lambda c: Mapeos.tipo_de_carga(c),
                                              reverse=True))

        Columna = namedtuple('Columna', 'nombre ancho funcion')
        columnas = [Columna('materia', 40, lambda c, m, t: m.nombre),
                    Columna('cuat', 4, lambda c, m, t: c.value),
                    Columna('turno', 12, lambda c, m, t: TipoTurno[t.tipo].value),
                    Columna('horario', 18, lambda c, m, t: t.horarios_info().diayhora),
                    Columna('alumnos', 4, lambda c, m, t: t.alumnos),
                    Columna('docentes', 100, lambda c, m, t: docentes_por_cargo(turno.carga_set.all())),
                    Columna('jtp', 5, lambda c, m, t: t.necesidad_jtp if t.tipo != TipoTurno.T.name else ''),
                    Columna('ay1', 5, lambda c, m, t: t.necesidad_ay1 if t.tipo != TipoTurno.T.name else ''),
                    Columna('ay2', 5, lambda c, m, t: t.necesidad_ay2 if t.tipo != TipoTurno.T.name else ''),
                    ]

        fila = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        for col, columna in enumerate(columnas):
            ws.write(fila, col, columna.nombre, font_style)
            wscol = ws.col(col)
            wscol.width = columna.ancho * 256

        font_style = xlwt.XFStyle()
        turnos = Turno.objects.filter(anno=anno)
        materias = Materia.objects.order_by('obligatoriedad', 'nombre')

        for materia in materias:
            turnos_materia = turnos.filter(materia=materia)
            if turnos_materia.count() > 0:
                ws.write(fila + 1, 0, materia.nombre, font_style)

                for cuatrimestre in Cuatrimestres:
                    estilo = estilos[cuatrimestre]
                    for turno in turnos.filter(materia=materia, cuatrimestre=cuatrimestre.name):
                        fila += 1
                        for col, columna in enumerate(columnas[1:], 1):
                            ws.write(fila, col, columna.funcion(cuatrimestre, materia, turno), estilo)

        wb.save(response)
        return response

    else:
        context = {
            'anno': anno,
            'cuatrimestre': cuatrimestre,
        }
        return render(request, 'materias/exportar_informacion.html', context)


@login_required
@permission_required('materias.add_turno')
def generar_cuatrimestre(request, anno, cuatrimestre):
    if request.method == 'POST':
        nuevo_anno = int(request.POST['nuevo_anno'])
        nuevo_cuatrimestre = Cuatrimestres[request.POST['nuevo_cuatrimestre']]
        logger.info('Voy a copiar (%s, %s) a (%s, %s)', anno, cuatrimestre, nuevo_anno, nuevo_cuatrimestre)
        with transaction.atomic():
            for turno in Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre):
                tipo_materia = turno.materia.obligatoriedad
                if f'copiar_{tipo_materia}' in request.POST:
                    nturno, creado = Turno.objects.get_or_create(materia=turno.materia,
                                                                 anno=nuevo_anno, cuatrimestre=nuevo_cuatrimestre.name,
                                                                 numero=turno.numero, subnumero=turno.subnumero, tipo=turno.tipo,
                                                                 defaults={'necesidad_prof': turno.necesidad_prof,
                                                                           'necesidad_jtp': turno.necesidad_jtp,
                                                                           'necesidad_ay1': turno.necesidad_ay1,
                                                                           'necesidad_ay2': turno.necesidad_ay2,
                                                                           'dificil_de_cubrir': turno.dificil_de_cubrir})
                    if creado:
                        logger.info('Generé un nuevo turno: %s', nturno)
                        for horario in turno.horario_set.all():
                            nhorario = Horario.objects.create(turno=nturno,
                                                              dia=horario.dia, comienzo=horario.comienzo, final=horario.final,
                                                              aula='', pabellon=Pabellon.Uno.value[0]
                                                              )
                        logger.debug('  y le puse %d horarios', turno.horario_set.count())
        return HttpResponseRedirect(reverse('materias:administrar'))

    else:
        context = {
            'anno': anno,
            'annos': list(range(anno + 1, anno + 4)),
            'anno_m3': anno + 3,
            'cuatrimestre': Cuatrimestres[cuatrimestre],
            'cuatrimestres': list(Cuatrimestres),
            'tipos': list(TipoMateria),
        }
        return render(request, 'materias/generar_cuatrimestre.html', context)


SIN_CARGO = ('sincargo', 'sin cargo')
def _docentes_por_cargo():
    docentes = {(tipo_cargo.name, tipo_cargo.value): sorted(Mapeos.docentes_con_cargo_de_tipo(tipo_cargo),
                                                            key=lambda d: strxfrm(d.apellido_nombre))
                for tipo_cargo in TipoDocentes}
    docentes[SIN_CARGO] = Docente.objects.filter(cargos__len=0)
    return docentes

def _docentes_en_request(request):
    return {docente for docente in Docente.objects.all()
            if f'juntar_{docente.id}' in request.POST}


@login_required
@permission_required('materias.add_turno')
def administrar_docentes(request):
    if request.method == 'POST':
        if 'juntar' in request.POST:
            docentes = _docentes_en_request(request)
            logger.info('Voy a juntar a %s', docentes)
            turnos = {docente: [(carga.turno.anno, carga.turno.cuatrimestre)
                                for carga in docente.carga_set.all() if carga.turno is not None]
                      for docente in docentes}
            todos_los_turnos = sorted({ac
                                       for acs in turnos.values()
                                       for ac in acs})
            intersecciones = Counter(turno
                                     for turno in todos_los_turnos
                                     for docente, doc_turnos in turnos.items() if turno in doc_turnos)
            context = {
                'docentes': docentes,
                'cuatrimestres': Cuatrimestres,
                'turnos': turnos,
                'todos_los_turnos': todos_los_turnos,
                'no_hay_repetidos': max(intersecciones.values()) == 1 if intersecciones else True,
            }
            return render(request, 'materias/juntar_docentes.html', context)
        elif 'confirmar' in request.POST:
            docente_id = int(request.POST['nombre'].split('_')[1])
            docente_final = Docente.objects.get(pk=docente_id)
            para_juntar = {int(j_id.split('_')[1])
                           for j_id in request.POST
                           if j_id.startswith('juntar_')}
            docentes = {Docente.objects.get(pk=d_id) for d_id in para_juntar if d_id != docente_id}
            with transaction.atomic():
                for docente in docentes:
                    for carga in docente.carga_set.all():
                        logger.debug('cambiando carga de docente: %s', carga)
                        carga.docente = docente_final
                        carga.save()
                    for preferencia in docente.preferenciasdocente_set.all():
                        logger.debug('cambiando preferencia de docente: %s', preferencia)
                        preferencia.docente = docente_final
                        preferencia.save()
                    for otrosdatos in docente.otrosdatos_set.all():
                        logger.debug('cambiando otros datos de docente: %s', otrosdatos)
                        otrosdatos.docente = docente_final
                        otrosdatos.save()
                    for cargaspedidas in docente.cargaspedidas_set.all():
                        logger.debug('cambiando cargas pedidas de docente: %s', cargaspedidas)
                        cargaspedidas.docente = docente_final
                        cargaspedidas.save()
                    docente_final.email = docente_final.email or docente.email
                    docente_final.telefono = docente_final.telefono or docente.telefono
                    docente.delete()
                docente_final.save()

        elif 'cambiar_cargo' in request.POST:
            context = {
                'docentes': _docentes_en_request(request),
                'cargos': [('', '')] + list(reversed(list(choice_enum(CargoDedicacion)))),
            }
            return render(request, 'materias/cambiar_cargos.html', context)

        elif 'confirma_cambiar' in request.POST:
            docentes = _docentes_en_request(request)
            cargo = request.POST['cargo'].split('_')[1]
            cargos = [CargoDedicacion[cargo].name] if cargo else []
            logger.info('le voy a cambiar el cargo a %s: desde ahora, %s', docentes, cargo)
            with transaction.atomic():
                for docente in docentes:
                    docente.cargos = cargos
                    docente.save()

        elif 'agregar' in request.POST:
            docente, creado = Docente.objects.get_or_create(na_nombre='__ nuevo docente __', na_apellido='', cargos=[])
            if creado:
                logger.info('estoy creando un nuevo docente')
            return HttpResponseRedirect(reverse('materias:administrar_un_docente', args=(docente.id,)))

    context = {
        'docentes': _docentes_por_cargo(),
    }
    return render(request, 'materias/administrar_docentes.html', context)


@login_required
@permission_required('materias.add_turno')
def administrar_un_docente(request, docente_id):
    docente = Docente.objects.get(pk=docente_id)
    cargos = docente.cargos
    cargo = Mapeos.tipos_de_cargo(cargos[0]).name if cargos else SIN_CARGO[0]
    context = {
        'docente': docente,
        'cargo': cargo,
    }
    if request.method == 'POST':
        if 'salvar' in request.POST:
            form = DocenteForm(request.POST, instance=docente)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(f"{reverse('materias:administrar_docentes')}#tipo_{cargo}")
            else:
                logger.error(form.errors)
        elif 'borrar' in request.POST:
            borrado = docente.delete()
            logger.warning('Borré un docente: %s. Todo lo borrado es %s', docente, borrado)
            return HttpResponseRedirect(reverse('materias:administrar_docentes'))
    else:
        form = DocenteForm(instance=docente)
    context['form'] = form
    return render(request, 'materias/administrar_un_docente.html', context)
