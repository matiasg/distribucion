from bs4 import BeautifulSoup
import datetime
import logging
import math
import coloredlogs
from pathlib import Path
import re
import urllib.request as request
from django.utils.dateparse import parse_time
from argparse import ArgumentParser

from django.db.models import Value, Func, F
from django.db.models.functions import Concat

import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import (Materia, AliasDeMateria, Turno, Horario, Docente, Carga,
                             Cuatrimestres, TipoMateria, TipoTurno, Cargos, CargoDedicacion, Dias, get_key_enum)

# logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger()
coloredlogs.install(level='DEBUG')


def lee_horarios_anteriores(anno, cuatrimestre):
    req = request.urlopen(f'http://cms.dm.uba.ar/horarios/horarios_html?cuatrim={anno}{cuatrimestre}')
    return req.read()


numeros_romanos = re.compile(r'\b(?i:i{1,3}|vi{0,3}|iv|ix)\b')
palabras_cortas = re.compile(r'\s([AYEOU]|\w{2,3})\b')
def maymin(materia):
    '''Convierte a mayúsculas cada primera letra de palabra y a minúsculas el resto.
    Deja en minúscula algunas palabras de hasta 3 letras.
    Tiene cuidado con poner en mayúsculas los números romanos entre 1 y 9
    '''
    materia = materia.title()
    materia = palabras_cortas.sub(lambda t: t.group(0).lower(), materia)
    return numeros_romanos.sub(lambda t: t.group(0).upper(), materia)



def convierte_a_horarios(text):
    dia = '({})'.format('|'.join(d.name for d in Dias))
    hora = r'(\d{1,2}(:\d{2})?)\b'
    dia_y_hora = re.compile(fr'^({dia}):\s*({hora}) (?:a|-) ({hora})')
    dos_dias_y_hora = re.compile(fr'^({dia}) - ({dia}):\s*({hora}) (?:a|-) ({hora})')
    tres_dias_y_hora = re.compile(fr'^({dia}) - ({dia}) - ({dia}):\s*({hora}) (?:a|-) ({hora})')

    def hm(hhmm):
        ret = parse_time(hhmm) or datetime.time(int(hhmm), 0)
        return ret

    m = dia_y_hora.search(text)
    if m:
        return [(m.group(1), hm(m.group(3)), hm(m.group(6)))]
    m = dos_dias_y_hora.search(text)
    if m:
        return [(m.group(1), hm(m.group(5)), hm(m.group(8))),
                (m.group(3), hm(m.group(5)), hm(m.group(8)))]
    m = tres_dias_y_hora.search(text)
    if m:
        return [(m.group(1), hm(m.group(7)), hm(m.group(10))),
                (m.group(3), hm(m.group(7)), hm(m.group(10))),
                (m.group(5), hm(m.group(7)), hm(m.group(10)))
                ]
    logger.warning('No veo los horarios en "%s"', text)
    return []



tipo_turnos = {'Teórica': TipoTurno.T.name,
               'Práctica': TipoTurno.P.name,
               'Teórico-Práctica': TipoTurno.A.name}
cargo_tipoturno = {'Teórica': [CargoDedicacion.AsoExc],
                   'Práctica': [CargoDedicacion.JTPSim, CargoDedicacion.Ay1Sim, CargoDedicacion.Ay2Sim],
                   'Teórico-Práctica': [CargoDedicacion.AsoExc,
                                        CargoDedicacion.JTPSim, CargoDedicacion.Ay1Sim, CargoDedicacion.Ay2Sim]}

docentes_separador = re.compile('(?: +-+ *| *—  *| *-+ +)')

def salva_datos(html, anno, cuatrimestre):
    soup = BeautifulSoup(html, 'html.parser')
    comienzo = soup.find_all('div', attrs={'class': 'seccion'})[0]

    tipos_de_materia = {
        'Materias Obligatorias'.lower(): TipoMateria.B,
        'Materias Dicatadas'.lower(): TipoMateria.B,  # 2012 V
        'materias para la maestría en estadística': TipoMateria.B,  # 2011 2
        'Materias Optativas Regulares'.lower(): TipoMateria.R,
        'Materias Optativas No Regulares'.lower(): TipoMateria.N,
        'Materias optativa no regulares'.lower(): TipoMateria.N,
        'Materias optativas'.lower(): TipoMateria.N,
    }

    tipo_de_materia = TipoMateria.B
    for parte in comienzo.findNextSiblings():

        if parte.attrs['class'][0] == 'seccion':
            tipo_de_materia = tipos_de_materia[parte.text.lower().strip()]

        else:
            nombre_materia = maymin(parte.find('thead').text)
            logger.info('Analizando: %s', nombre_materia)

            try:
                materia = Materia.objects.get(nombre=nombre_materia, obligatoriedad=tipo_de_materia.name)
            except Materia.DoesNotExist:
                try:
                    alias = AliasDeMateria.objects.get(nombre=nombre_materia)
                    materia = alias.materia
                except AliasDeMateria.DoesNotExist:
                    materia = Materia.objects.create(nombre=nombre_materia, obligatoriedad=tipo_de_materia.name)
                    logger.warning('Creé una nueva materia: %s', materia)

            for turno_html in parte.find_all('tr'):
                rows = turno_html.find_all('td')
                tipoynumero = rows[0].text.split()
                turno_docentes = docentes_separador.split(rows[2].text)
                logger.debug('docentes: %s', turno_docentes)

                # turnos
                tipo_turno = tipo_turnos[tipoynumero[0]]
                if tipo_turno == TipoTurno.T.name:
                    necesidad_prof = 1
                    necesidad_jtp = necesidad_ay1 = necesidad_ay2 = 0
                elif tipo_turno == TipoTurno.P.name:
                    tercio_docentes = len(turno_docentes) / 3
                    necesidad_prof = 0
                    necesidad_jtp = max(math.floor(tercio_docentes), 1)
                    necesidad_ay1 = round(tercio_docentes)
                    necesidad_ay2 = len(turno_docentes) - necesidad_prof - necesidad_jtp - necesidad_ay1
                else:
                    tercio_docentes = (len(turno_docentes) - 1) / 3
                    necesidad_prof = 1
                    necesidad_jtp = max(math.floor(tercio_docentes), 1 if len(turno_docentes) > 1 else 0)
                    necesidad_ay1 = round(tercio_docentes)
                    necesidad_ay2 = len(turno_docentes) - necesidad_prof - necesidad_jtp - necesidad_ay1
                defaults = {
                    'necesidad_prof': necesidad_prof,
                    'necesidad_jtp': necesidad_jtp,
                    'necesidad_ay1': necesidad_ay1,
                    'necesidad_ay2': necesidad_ay2,
                }

                try:
                    numero_turno = int(tipoynumero[1]) if len(tipoynumero) > 1 else 0
                    subnumero = tipoynumero[2] if len(tipoynumero) > 2 else ''
                except ValueError:
                    try:
                        numero_turno = int(tipoynumero[1][0])
                        subnumero = tipoynumero[1][1:]
                    # algunos cuatrimestres tienen el el numero_turno y el horario juntos
                    # en algunas materias
                    except ValueError:
                        try:
                            numero_turno = int(tipoynumero[1])
                            fin_numero = 2
                        except ValueError:
                            numero_turno = 0
                            fin_numero = 1
                        finally:
                            rows = list(rows)
                            rows[1:1] = [rows[0]]

                datos_turno = {
                    'materia': materia,
                    'cuatrimestre': cuatrimestre,
                    'numero': numero_turno,
                    'subnumero': subnumero,
                    'tipo': tipo_turno,
                }
                turno, creado = Turno.objects.get_or_create(**datos_turno, anno=anno, defaults=defaults)
                if creado:
                    logger.info('nuevo turno creado: %s', turno)


                # docentes y cargas
                cargos = cargo_tipoturno[tipoynumero[0]]
                cargos_inferidos = [CargoDedicacion.AsoExc] * necesidad_prof + [CargoDedicacion.JTPSim] * necesidad_jtp \
                                   + [CargoDedicacion.Ay1Sim] * necesidad_ay1 + [CargoDedicacion.Ay2Sim] * necesidad_ay2
                cargos_inferidos += [cargos_inferidos[-1]] * (len(turno_docentes) - len(cargos_inferidos))
                for i, docente in enumerate(turno_docentes):
                    # evitamos el docente '' que aparece en turnos sin asignaciones
                    if not docente:
                        continue

                    cargo = cargos_inferidos[i].name

                    # intento encontrar docente
                    docentes_qs = Docente.objects.annotate(na=Concat('na_nombre', Value(' '), 'na_apellido'))
                    posibles_docentes = docentes_qs.filter(na=docente)

                    doc = None
                    if posibles_docentes.count() == 1:
                        doc = posibles_docentes.first()
                        logger.debug('docente existente: %s', doc)
                    elif posibles_docentes.count() > 1:
                        logger.error('ah, no, hay más de un docente con el mismo nombre: %s', posibles_docentes)
                        raise RuntimeError('problema con docentes: más de uno con el mismo nombre: {}'.format(docente))
                    else:   # Todavía podríamos encontrar alguno que se llame parecido. Lo buscamos con distancia de edición
                        # Nota: el .replace() que sigue es horrible. No encontré nada mejor.
                        # Todo el escaping es muy automático y las funciones para escapar en SQL están
                        # medio escondidas. Lo más cercano que vi es
                        #     from django.db import connection
                        #     cursor = connection.cursor()
                        #     cursor.mogrify(docente)
                        # Pero no (me) funciona.
                        # TODO para el que mantenga este software: encontrá algo mejor. Suerte.
                        template = "%(function)s(%(expressions)s, '{}')".format(docente.replace("'", "''"))
                        docentes_lvns = docentes_qs.annotate(similar=Func(F('na'),
                                                                          function='levenshtein',
                                                                          template=template))
                        docentes_parecidos = docentes_lvns.filter(similar__lt=3)
                        if docentes_parecidos.count() > 0:
                            doc = docentes_parecidos.order_by('similar').first()
                            logger.warning('Encontré un docente que parece ser %s. Es %s. Los considero la misma persona.',
                                           docente, doc)

                    if doc is None:
                        palabras_na = docente.split()
                        palabras_nombre = 1 if len(palabras_na) < 3 else 2
                        nombre = ' '.join(palabras_na[:palabras_nombre])
                        apellido = ' '.join(palabras_na[palabras_nombre:])
                        doc = Docente.objects.create(na_nombre=nombre, na_apellido=apellido, cargos=[cargo])
                        logger.info('agregue a: %s', doc)

                    carga, creada = Carga.objects.get_or_create(docente=doc,
                                                                turno=turno,
                                                                anno=anno, cuatrimestre=cuatrimestre,
                                                                defaults={'cargo': cargo})
                    if creada:
                        logger.info('Carga docente: %s -> %s', doc.nombre, turno)

                # horarios
                horarios = convierte_a_horarios(rows[1].text)
                for horario in horarios:
                    logger.info('horario: %s, %s, %s', horario[0], horario[1], horario[2])
                    h, creado = Horario.objects.get_or_create(dia=horario[0],
                                                              comienzo=horario[1],
                                                              final=horario[2],
                                                              turno=turno,
                                                              defaults={'aula': '', 'pabellon': 1})
                    if creado:
                        logger.debug('Agregué un nuevo horario para %s: %s', turno, h)


def parse():
    anno = datetime.datetime.now().year
    parser = ArgumentParser(description='utilitario para llenar materias en la db')
    parser.add_argument('año', type=int,
                        help='Año del que se quiere tomar la información')
    parser.add_argument('cuatrimestre',
                        choices=[c.value for c in Cuatrimestres],
                        help='Cuatrimestre del que se quiere tomar la información')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse()
    cuatrimestre_name = get_key_enum(Cuatrimestres)[args.cuatrimestre]
    html = lee_horarios_anteriores(args.año, args.cuatrimestre.lower())
    salva_datos(html, args.año, cuatrimestre_name)
