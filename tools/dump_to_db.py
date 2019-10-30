#
# este código estuvo pensado para usarse solo una vez, para una distribución específica
# que se había hecho con el sistema anterior.
# Ya no montamos ../sitio_anterior en el docker-compose así que probablemente falle
# si lo pretendés usar ahora.
#
import datetime
import pytz
import logging
import coloredlogs
from pathlib import Path
import csv
import re
from argparse import ArgumentParser

from django.utils.dateparse import parse_datetime
from django.db import transaction

import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import (Materia, Turno, Horario, Docente, Carga, Cuatrimestres, TipoMateria, TipoTurno,
                             Cargos, Dedicaciones, CargoDedicacion, Dias, TipoDocentes, get_key_enum)
from materias.misc import Mapeos
from encuestas.models import PreferenciasDocente, OtrosDatos, CargasPedidas
from dborrador.models import Asignacion
from tools.current_html_to_db import maymin, convierte_a_horarios

logger = logging.getLogger()
coloredlogs.install(level='WARNING')


path = Path(__file__).absolute().parent.parent.parent / 'sitio_anterior'
anno = 2019
cuatrimestre = Cuatrimestres.S
cargos_ya_distribuidos = TipoDocentes.P
ajustar_cargas_a_encuestas = False

def borra_datos_de_anno_y_cuatrimestre():
    tb = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    cb = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    eb = PreferenciasDocente.objects.filter(turno__anno=anno, turno__cuatrimestre=cuatrimestre.name).delete()
    ob = OtrosDatos.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    cp = CargasPedidas.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    logger.info('Borré datos de turnos: %s', tb)
    logger.info('Borré datos de cargas: %s', cb)
    logger.info('Borré datos de preferencias: %s', eb)
    logger.info('Borré otros datos de encuestas: %s', ob)
    logger.info('Borré cargas pedidas de encuestas: %s', cp)


class LectorDeCsv:

    _a_cargo = {
        '1t': Cargos.Tit,
        '1a': Cargos.Aso,
        '1j': Cargos.Adj,
        '1v': Cargos.Vis,
        '2': Cargos.JTP,
        '3': Cargos.Ay1,
        '4': Cargos.Ay2,
    }

    _a_dedicacion = {
        '1': Dedicaciones.Exc,
        '2': Dedicaciones.Smx,
        '3': Dedicaciones.Sim,
    }

    @classmethod
    def csv_reader(cls, txt):
        with open(path / txt) as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                yield row

    @classmethod
    def lee_docentes(cls):
        return {_id: {'nombre': f'{nombre}', 'apellido': f'{apellido}'}
                for _id, apellido, nombre, legajo, notas in cls.csv_reader('docente.txt')}

    @classmethod
    def lee_cargos(cls):
        def cargo_ded(c, d):
            c = cls._a_cargo[c].name
            d = cls._a_dedicacion[d].name
            return CargoDedicacion[f'{c}{d}']

        def cargas_cuatri(notas):
            m = re.search('Carga anual: ([0-9,.]+)$', notas)
            if m:
                return round(float(m.group(1).replace(',', '.')) / 2)
            return 1

        return [{'id': doc_id, 'cargo': cargo_ded(cargo, dedicacion), 'cargas': cargas_cuatri(notas)}
                for _, cargo, dedicacion, notas, doc_id in cls.csv_reader('cargo.txt')]

    @classmethod
    def lee_materias_y_turnos(cls):
        _a_obligatoriedad = {
            '1': TipoMateria.B,
            '2': TipoMateria.R,
            '3': TipoMateria.N,
        }

        def _a_numero(ide):
            if not ide:
                return 0
            try:
                return int(ide)
            except ValueError:
                return int(ide[:1])  # TODO: tomar de acá más información

        materias = {_id: {'nombre': nombre, 'tipo': _a_obligatoriedad[tipo]}
                    for _id, nombre, periodo, tipo in cls.csv_reader('materia.txt')}
        turnos = {_id: {'tipo': tipo, 'numero': _a_numero(identificador),
                        'secuencia': int(secuencia),
                        'horarios': convierte_a_horarios(horario),
                        'nec_prof': int(usa_1), 'nec_jtp': int(usa_2), 'nec_ay1': int(usa_3), 'nec_ay2': int(usa_4),
                        'dificil': forzar == '1', 'materia': materia_id}
                  for _id, secuencia, tipo, identificador, horario, _, _, usa_1, usa_2, usa_3, usa_4, forzar, materia_id in cls.csv_reader('turno.txt')}
        return materias, turnos

    @classmethod
    def lee_docentes_ya_distribuidos(cls):
        return [{'docente': docente, 'turno': turno}
                for _, _, _, _, docente, turno in cls.csv_reader('dictat.txt')]

    @classmethod
    def lee_encuestas(cls):
        buenos_aires_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        datos_docentes = {encuesta_id: {'docente': docente,
                                        'timestamp': buenos_aires_tz.localize(parse_datetime(timestamp)),
                                        'email': email,
                                        'telefono': telefono.replace(' ', ''),
                                        'observaciones_generales': observaciones,
                                        }
                          for encuesta_id, timestamp, email, telefono, observaciones, _, docente in cls.csv_reader('encuesta.txt')}

        for encuesta_periodo_id, _, cargas, _, _, _, observaciones, encuesta_id in cls.csv_reader('encuestaperiodo.txt'):
            datos_docentes[encuesta_id].update({'encuesta_periodo_id': encuesta_periodo_id,
                                                'cargas': int(cargas),
                                                'observaciones_particulares': observaciones})

        # ponemos encuesta_periodo_id como key porque eso es lo que viene en opciones
        datos_docentes = {dato['encuesta_periodo_id']: dato for dato in datos_docentes.values()}

        opciones = [{'encuesta_periodo_id': encuesta_periodo_id, 'turno': turno, 'peso': int(peso)}
                    for _, peso, _, encuesta_periodo_id, turno in cls.csv_reader('opcion.txt')]

        return opciones, datos_docentes


def main():
    borra_datos_de_anno_y_cuatrimestre()

    materias, turnos = LectorDeCsv.lee_materias_y_turnos()
    materias_nuestras = {}
    docentes_nuestros = {}
    turnos_nuestros = {}

    with transaction.atomic():
        for _id, mat in materias.items():
            nombre = maymin(mat['nombre'])
            mat, creada = Materia.objects.get_or_create(nombre=nombre, obligatoriedad=mat['tipo'].name)
            materias_nuestras[_id] = mat
            if creada:
                logger.info('creé la materia %s', mat)

        for _id, turno in turnos.items():
            turno_actual, creado = Turno.objects.get_or_create(materia=materias_nuestras[turno['materia']],
                                                               anno=anno, cuatrimestre=cuatrimestre.name,
                                                               numero=turno['numero'],
                                                               tipo=turno['tipo'],
                                                               defaults={'necesidad_prof': turno['nec_prof'],
                                                                         'necesidad_jtp': turno['nec_jtp'],
                                                                         'necesidad_ay1': turno['nec_ay1'],
                                                                         'necesidad_ay2': turno['nec_ay2'],
                                                                         'dificil_de_cubrir': turno['dificil']},
                                                               )
            if creado:
                logger.info('Creé el turno %s', turno_actual)
                turnos_nuestros[_id] = turno_actual
            else:
                logger.error('Ya hay un turno que colisiona con este: %s. Invento identificadores en base a secuencia', turno_actual)
                # busco la secuencia del turno anterior
                id_previa = next(ide for ide, t in turnos_nuestros.items() if t == turno_actual)
                turno_actual_info_de_tabla = turnos[id_previa]
                turno_actual.numero = turno_actual_info_de_tabla['secuencia']
                turno_actual.save()
                # ahora salvo este
                turno_actual = Turno.objects.create(materia=materias_nuestras[turno['materia']],
                                                    anno=anno, cuatrimestre=cuatrimestre.name,
                                                    numero=turno['secuencia'],
                                                    tipo=turno['tipo'],
                                                    necesidad_prof=turno['nec_prof'], necesidad_jtp=turno['nec_jtp'],
                                                    necesidad_ay1=turno['nec_ay1'], necesidad_ay2=turno['nec_ay2'],
                                                    dificil_de_cubrir=turno['dificil'])
                turnos_nuestros[_id] = turno_actual

            for horario in turno['horarios']:
                logger.info('horario: %s, %s, %s', horario[0], horario[1], horario[2])
                h, creado = Horario.objects.get_or_create(dia=horario[0],
                                                          comienzo=horario[1],
                                                          final=horario[2],
                                                          turno=turno_actual,
                                                          defaults={'aula': '', 'pabellon': 1})
                if creado:
                    logger.debug('Agregué un nuevo horario: %s', h)

        docentes = LectorDeCsv.lee_docentes()
        cargos = LectorDeCsv.lee_cargos()
        for cargo in cargos:
            doc_id = cargo['id']
            nombre = docentes[doc_id]['nombre']
            apellido = docentes[doc_id]['apellido']
            cargo_ded = cargo['cargo']
            docente_actual, creado = Docente.objects.get_or_create(na_nombre=nombre, na_apellido=apellido,
                                                                   defaults={'cargos': [cargo_ded.name]})
            docentes_nuestros[doc_id] = docente_actual

            if creado:
                logger.info('creé docente %s %s con cargo %s', nombre, apellido, cargo_ded.name)
            for _ in range(cargo['cargas']):
                Carga.objects.create(docente=docente_actual, cargo=cargo_ded.name,
                                     anno=anno, cuatrimestre=cuatrimestre.name)

        for carga_fila in LectorDeCsv.lee_docentes_ya_distribuidos():
            doc_id = carga_fila['docente']
            docente_actual = docentes_nuestros[doc_id]

            cargo = docente_actual.cargos[0]  # lo que viene en 'dictat.txt' no distingue tipos de Profesor

            cargas = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name, docente=docente_actual, cargo=cargo, turno=None)
            if cargas.count() == 0:
                carga = Carga.objects.create(anno=anno, cuatrimestre=cuatrimestre.name, docente=docente_actual, cargo=cargo)
            else:
                # tomamos la primera carga que no tenga turno asignado
                carga = cargas.first()

            tipo_de_cargo = Mapeos.tipos_de_cargo(cargo)
            if tipo_de_cargo >= cargos_ya_distribuidos:
                carga.turno = turnos_nuestros[carga_fila['turno']]
                carga.save()
                logger.info('Carga generada: %s', carga)
            else:
                asignacion = Asignacion.objects.create(carga=carga,
                                                       turno=turnos_nuestros[carga_fila['turno']],
                                                       intentos=(0, None),
                                                       cargo_que_ocupa=tipo_de_cargo.name)
                logger.info('Asigné un docente de manera fija: %s', asignacion)

        opciones, datos_docentes = LectorDeCsv.lee_encuestas()

        # chequeamos que las cargas pedidas sean las que tenemos
        # y creamos o borramos cargas si no
        for datos in datos_docentes.values():
            docente = docentes_nuestros[datos['docente']]
            cargas_esperadas = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name, docente=docente)
            fecha_encuesta = datos['timestamp']

            if ajustar_cargas_a_encuestas:
                if datos['cargas'] < cargas_esperadas.count():
                    a_borrar = cargas_esperadas.count() - datos['cargas']
                    logger.warning("%s tiene %d carga(s) esperada(s) pero pide %d. Le borro %d carga(s)",
                                   docente, cargas_esperadas.count(), datos['cargas'], a_borrar)
                    for _ in range(a_borrar):
                        cargas_esperadas.filter(turno=None).last().delete()

                elif datos['cargas'] > cargas_esperadas.count():
                    a_crear = datos['cargas'] - cargas_esperadas.count()
                    logger.warning("%s tiene %d carga(s) esperada(s) pero pide %d. Le agrego %d carga(s)",
                                   docente, cargas_esperadas.count(), datos['cargas'], a_crear)
                    cargo = docente.cargos[0]
                    for _ in range(a_crear):
                        Carga.objects.create(anno=anno, cuatrimestre=cuatrimestre.name, docente=docente, cargo=cargo)

            OtrosDatos.objects.create(
                docente=docente,
                fecha_encuesta=fecha_encuesta,
                anno=anno,
                cuatrimestre=cuatrimestre.name,
                email=datos['email'],
                telefono=datos['telefono'],
                comentario=f'General: {datos["observaciones_generales"]}.\nCuatrimestre: {datos["observaciones_particulares"]}'
            )
            CargasPedidas.objects.create(
                docente=docente,
                fecha_encuesta=fecha_encuesta,
                anno=anno,
                cuatrimestre=cuatrimestre.name,
                cargas=datos['cargas'],
            )

            docente.email = datos['email']
            docente.telefono = datos['telefono']
            docente.save()

        # salvamos opciones
        for opcion in opciones:
            datos = datos_docentes[opcion['encuesta_periodo_id']]
            docente = docentes_nuestros[datos['docente']]
            turno = turnos_nuestros[opcion['turno']]
            cargo = docente.cargos[0][:3]
            PreferenciasDocente.objects.get_or_create(docente=docente, cargo=cargo,
                                                      turno=turno, peso=opcion['peso'],
                                                      fecha_encuesta=fecha_encuesta)


if __name__ == '__main__':
    main()
