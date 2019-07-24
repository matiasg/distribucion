from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.contrib.auth.decorators import permission_required, login_required

from locale import strxfrm
from collections import Counter, namedtuple
import logging
logger = logging.getLogger(__name__)

from .models import (Materia, AliasDeMateria, Turno, Horario, Cuatrimestres, TipoMateria, TipoTurno,
                     TipoDocentes, Docente, CargoDedicacion, Carga, Pabellon, Dias)
from .misc import Mapeos, NoTurno
from encuestas.models import PreferenciasDocente, OtrosDatos, CargasPedidas


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
    if request.method == 'POST':
        anno = int(request.POST['anno'])
        cuatrimestre = request.POST['cuatrimestre']
        annos = [anno]
        cuatrimestres = [Cuatrimestres[cuatrimestre]]

        if 'turnos_alumnos' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_alumnos', args=(anno, cuatrimestre)))
        elif 'turnos_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_docentes', args=(anno, cuatrimestre)))
        elif 'exportar_informacion' in request.POST:
            return HttpResponseRedirect(reverse('materias:exportar_informacion', args=(anno, cuatrimestre)))
        elif 'generar_cuatrimestre' in request.POST:
            return HttpResponseRedirect(reverse('materias:generar_cuatrimestre', args=(anno, cuatrimestre)))
        elif 'generar_cargas_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:generar_cargas_docentes', args=(anno, cuatrimestre)))
        elif 'juntar_materias' in request.POST:
            return HttpResponseRedirect(reverse('materias:juntar_materias'))
        elif 'cargas_docentes' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_cargas_docentes', args=(anno, cuatrimestre)))
        elif 'cargas_docentes_publicadas' in request.POST:
            return HttpResponseRedirect(reverse('materias:administrar_cargas_publicadas', args=(anno, cuatrimestre)))
        elif 'administrar_encuestas' in request.POST:
            return HttpResponseRedirect(reverse('encuestas:administrar_habilitadas'))
        elif 'dborrador' in request.POST:
            return HttpResponseRedirect(reverse('dborrador:distribucion', args=(anno, cuatrimestre, 0, 0)))
    else:
        anno_actual = timezone.now().year
        annos = list(range(anno_actual - 3, anno_actual + 2))
        cuatrimestres = [c for c in Cuatrimestres]
        return render(request, 'materias/administrar.html', context={'annos': annos,
                                                                     'cuatrimestres': cuatrimestres,
                                                                     'actual': anno_actual})


def administrar_general(request, anno, cuatrimestre, key_to_field, url, **kwargs):
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


        return HttpResponseRedirect(reverse('materias:administrar'))

    else:
        materias = filtra_materias(anno=anno, cuatrimestre=cuatrimestre)

        context = {'anno': anno,
                   'cuatrimestre': Cuatrimestres[cuatrimestre],
                   'materias': materias,
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

    return administrar_general(request, anno, cuatrimestre, key_to_field, 'materias/administrar_alumnos.html')


@login_required
@permission_required('dborrador.add_asignacion')
def administrar_docentes(request, anno, cuatrimestre):
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

    return administrar_general(request, anno, cuatrimestre, key_to_field, 'materias/administrar_docentes.html',
                               necesidades_y_recursos=necesidades_y_recursos)

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
    docentes_y_cargas_encuesta = {cp.docente: cp.cargas for cp in CargasPedidas.objects.filter(anno=anno, cuatrimestre=cuatrimestre).all()}
    # calculo diferencias contra encuesta
    diferencias_encuesta = {d: (len(docentes_y_cargas_nuestras[d]),
                                docentes_y_cargas_encuesta[d],
                                OtrosDatos.objects.filter(anno=anno, cuatrimestre=cuatrimestre, docente=d).first())
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
               'cuatrimestre': cuatrimestre,
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

    context = {
        'distribuidas': cargas_distribuidas,
        'no_distribuidas': cargas_no_distribuidas,
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
@permission_required('materias.add_turno')
def agregar_turno(request, materia_id, tipo, anno, cuatrimestre):
    materia = Materia.objects.get(pk=materia_id)
    turnos = Turno.objects.filter(materia=materia, anno=anno, cuatrimestre=cuatrimestre)
    numero_nuevo_turno = max(t.numero for t in turnos.filter(tipo=tipo)) + 1
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
            'cuatrimestre': cuatrimestre,
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

    if 'volver' in request.POST:
        return HttpResponseRedirect(reverse('materias:administrar_materia', args=_turno_a_materia_args(turno)))

    # TODO: en este momento, cualquier botón de "agregar horario" da lo mismo. Todos agregan el primer horario
    # que tenga dia, comienzo y final completado. Si hay más de uno, agregan solo el primero.
    # Habría que permitir un botón general de "agregar horarios"
    for horario_agregado in range(3):
        try:
            dia = request.POST[f'dia{horario_agregado}']
            comienzo = parse_time(request.POST[f'comienzo{horario_agregado}'])
            final = parse_time(request.POST[f'final{horario_agregado}'])
            horario = Horario.objects.create(dia=dia, comienzo=comienzo, final=final, turno=turno,
                                             aula='', pabellon='')
            break
        except:
            pass

    else:
        context = {
            'turno': turno,
            'materia': turno.materia,
            'tipoturno': TipoTurno[turno.tipo],
            'dias': [d for d in Dias],
            'horas': [('', ''),
                      *((f'{hora:02d}:{minutos:02d}:00', f'{hora:02d}:{minutos:02d}')
                        for hora in range(6, 24) for minutos in (0, 30) ) ]
        }
        return render(request, 'materias/cambiar_turno.html', context)

    return HttpResponseRedirect(reverse('materias:cambiar_turno', args=(turno_id,)))


@login_required
@permission_required('materias.add_turno')
def borrar_horario(request, horario_id):
    horario = Horario.objects.get(pk=horario_id)
    turno = horario.turno
    horario.delete()
    return HttpResponseRedirect(reverse('materias:cambiar_turno', args=(turno.id,)))


@login_required
@permission_required('materias.add_turno')
def juntar_materias(request):
    if request.method == 'POST':
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

            return HttpResponseRedirect(reverse('materias:juntar_materias'))

        else:
            if not para_juntar:
                logger.warning('pusieron juntar pero sin ninguna materia')
                return HttpResponseRedirect(reverse('materias:juntar_materias'))


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
        materias = {obligatoriedad: Materia.objects.filter(obligatoriedad=obligatoriedad.name).order_by('nombre')
                    for obligatoriedad in TipoMateria}
        context = {
            'materias': materias,
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
        n_anno = int(request.POST['anno'])
        n_cuatrimestre = Cuatrimestres[request.POST['cuatrimestre']]
        logger.info('Voy a copiar a: %s, cuat: %s', n_anno, n_cuatrimestre)
        with transaction.atomic():
            for turno in Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre):
                tipo_materia = turno.materia.obligatoriedad
                if f'copiar_{tipo_materia}' in request.POST:
                    nturno, creado = Turno.objects.get_or_create(materia=turno.materia, anno=n_anno, cuatrimestre=n_cuatrimestre.name,
                                                                 numero=turno.numero, subnumero=turno.subnumero, tipo=turno.tipo,
                                                                 defaults={'necesidad_prof': turno.necesidad_prof,
                                                                           'necesidad_jtp': turno.necesidad_jtp,
                                                                           'necesidad_ay1': turno.necesidad_ay1,
                                                                           'necesidad_ay2': turno.necesidad_ay2,
                                                                           'dificil_de_cubrir': turno.dificil_de_cubrir})
                    if creado:
                        logger.info('Generé un nuevo turno: %s', nturno)
                        for horario in turno.horario_set.all():
                            nhorario = Horario.objects.create(turno=nturno, dia=horario.dia, comienzo=horario.comienzo, final=horario.final)
        return HttpResponseRedirect(reverse('materias:administrar'))

    else:
        context = {
            'anno': anno,
            'annos': list(range(anno + 1, anno + 3)),
            'cuatrimestre': Cuatrimestres[cuatrimestre],
            'cuatrimestres': list(Cuatrimestres),
            'tipos': list(TipoMateria),
        }
        return render(request, 'materias/generar_cuatrimestre.html', context)


@login_required
@permission_required('dborrador.add_asignacion')
def generar_cargas_docentes(request, anno, cuatrimestre):
    pass
