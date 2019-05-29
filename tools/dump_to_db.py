import datetime
import logging
import coloredlogs
from pathlib import Path
import csv
import re

from django.utils.dateparse import parse_time
from argparse import ArgumentParser

import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import (Materia, Turno, Horario, Docente, Carga,
                             Cuatrimestres, TipoMateria, TipoTurno,
                             Cargos, Dedicaciones, CargoDedicacion, Dias, get_key_enum)
from tools.current_html_to_db import maymin, convierte_a_horarios

# logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger()
coloredlogs.install(level='DEBUG')


path = Path(__file__).parent / '../../sitio_anterior'
anno = 2019
cuatrimestre = Cuatrimestres.S


def borra_datos_de_anno_y_cuatrimestre():
    tb = Turno.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    cb = Carga.objects.filter(anno=anno, cuatrimestre=cuatrimestre.name).delete()
    logger.warning('Borré datos de turnos: %s', tb)
    logger.warning('Borré datos de cargas: %s', cb)



def csv_reader(txt):
    with open(path / txt) as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            yield row


def lee_docentes():
    return {_id: f'{nombre} {apellido}'
            for _id, apellido, nombre, legajo, notas in csv_reader('docente.txt')}

def lee_cargos():
    _a_cargo = {
        '1t': Cargos.Tit,
        '1a': Cargos.Aso,
        '1j': Cargos.Adj,
        '1v': Cargos.Tit, # TODO: crear cargos de visitante, issue #72
        '2': Cargos.JTP,
        '3': Cargos.Ay1,
        '4': Cargos.Ay2,
    }
    _a_dedicacion = {
        '1': Dedicaciones.Exc,  # TODO: realmente es así el código?
        '3': Dedicaciones.Sim,
    }

    def cargo_ded(c, d):
        c = _a_cargo[c].name
        d = _a_dedicacion[d].name
        return CargoDedicacion[f'{c}{d}']

    def cargas_cuatri(notas):
        m = re.search('Carga anual: ([0-9,.]+)$', notas)
        if m:
            return round(float(m.group(1).replace(',', '.')) / 2)
        return 1

    return [{'id': doc_id, 'cargo': cargo_ded(cargo, dedicacion), 'cargas': cargas_cuatri(notas)}
            for _, cargo, dedicacion, notas, doc_id in csv_reader('cargo.txt')]


def lee_materias_y_turnos():
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
                for _id, nombre, periodo, tipo in csv_reader('materia.txt')}
    turnos = {_id: {'tipo': tipo, 'numero': _a_numero(identificador),
                    'horarios': convierte_a_horarios(horario),
                    'nec_prof': int(usa_1), 'nec_jtp': int(usa_2), 'nec_ay1': int(usa_3), 'nec_ay2': int(usa_4),
                    'dificil': bool(forzar), 'materia': materia_id}
              for _id, _, tipo, identificador, horario, _, _, usa_1, usa_2, usa_3, usa_4, forzar, materia_id in csv_reader('turno.txt')}
    return materias, turnos


def main():
    borra_datos_de_anno_y_cuatrimestre()

    materias, turnos = lee_materias_y_turnos()
    materias_nuestras = {}

    for _id, mat in materias.items():
        nombre = maymin(mat['nombre'])
        mat, creada = Materia.objects.get_or_create(nombre=nombre, obligatoriedad=mat['tipo'].name)
        materias_nuestras[_id] = mat
        if creada:
            logger.info('creé la materia %s', mat)

    for turno in turnos.values():
        tur, creado = Turno.objects.get_or_create(materia=materias_nuestras[turno['materia']],
                                                  anno=anno, cuatrimestre=cuatrimestre.name,
                                                  numero=turno['numero'],
                                                  tipo=turno['tipo'],
                                                  defaults={
                                                      'necesidad_prof': turno['nec_prof'],
                                                      'necesidad_jtp': turno['nec_jtp'],
                                                      'necesidad_ay1': turno['nec_ay1'],
                                                      'necesidad_ay2': turno['nec_ay2'],
                                                      'dificil_de_cubrir': turno['dificil'],
                                                  },
                                                  )
        if creado:
            logger.info('Creé el turno %s', tur)
        else:
            logger.debug('Actualizo datos del turno %s', tur)
            tur.necesidad_prof=turno['nec_prof'],
            tur.necesidad_jtp=turno['nec_jtp'],
            tur.necesidad_ay1=turno['nec_ay1'],
            tur.necesidad_ay2=turno['nec_ay2'],
            tur.dificil_de_cubrir=turno['dificil'],

        for horario in turno['horarios']:
            logger.info('horario: %s, %s, %s', horario[0], horario[1], horario[2])
            h, creado = Horario.objects.get_or_create(
                                    dia=horario[0],
                                    comienzo=horario[1],
                                    final=horario[2],
                                    turno=tur,
                                    defaults={'aula': '', 'pabellon': 1})
            if creado:
                logger.debug('Agregué un nuevo horario: %s', h)

    docs = lee_docentes()
    cargos = lee_cargos()
    for cargo in cargos:
        nombre = docs[cargo['id']]
        cargo_ded = cargo['cargo']
        doc, creado = Docente.objects.get_or_create(nombre=nombre, cargos=[cargo_ded.name])
        if creado:
            logger.info('creé docente %s con cargo %s', nombre, cargo_ded.name)
        for _ in range(cargo['cargas']):
            Carga.objects.create(docente=doc, cargo=cargo_ded.name,
                                 anno=anno, cuatrimestre=cuatrimestre.name)



if __name__ == '__main__':
    main()
