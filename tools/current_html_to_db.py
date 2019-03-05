from bs4 import BeautifulSoup
import datetime
import logging
import coloredlogs
from pathlib import Path
import re
import urllib.request as request
from django.utils.dateparse import parse_time

import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import Materia, Turno, Horario, Docente, TipoMateria, TipoTurno, Cargos, Dias

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
    dia_y_hora = re.compile(fr'^({dia}): ({hora}) a ({hora})')
    dos_dias_y_hora = re.compile(fr'^({dia}) - ({dia}): ({hora}) a ({hora})')
    tres_dias_y_hora = re.compile(fr'^({dia}) - ({dia}) - ({dia}): ({hora}) a ({hora})')

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
cargo_tipoturno = {'Teórica': Cargos.Tit.name,
                   'Práctica': Cargos.JTP.name,
                   'Teórico-Práctica': Cargos.JTP.name}
def salva_datos(html, nuevo_anno, nuevo_cuatrimestre):
    soup = BeautifulSoup(html, 'html.parser')

    docentes = set()
    for tabla in soup.find_all('table', attrs={'class': 'contentbold'}):

        nombre_materia = maymin(tabla.find('thead').text)
        materia, _ = Materia.objects.get_or_create(nombre=nombre_materia, obligatoriedad=TipoMateria.B.name)
        logger.info('Analizando: %s', materia)

        for turno_html in tabla.find_all('tr'):
            rows = turno_html.find_all('td')
            tipoynumero = rows[0].text.split()
            tipo_turno = tipo_turnos[tipoynumero[0]]

            turno, creado = Turno.objects.get_or_create(
                                            materia=materia,
                                            anno=nuevo_anno,
                                            cuatrimestre=nuevo_cuatrimestre,
                                            numero=int(tipoynumero[1]) if len(tipoynumero) > 1 else 0,
                                            tipo=tipo_turno,
                                            defaults={'necesidades': '0,0,0'})
            turno.save()
            turno_docentes = rows[2].text.split(' — ')
            cargo = cargo_tipoturno[tipoynumero[0]]

            for docente in turno_docentes:
                docentes.add((docente, cargo))

            horarios = convierte_a_horarios(rows[1].text)
            for horario in horarios:
                logger.info('horario: %s, %s, %s', horario[0], horario[1], horario[2])
                h, creado = Horario.objects.get_or_create(
                                        dia=horario[0],
                                        comienzo=horario[1],
                                        final=horario[2],
                                        turno=turno,
                                        defaults={'aula': '', 'pabellon': 1})
                if creado:
                    logger.debug('Agregué un nuevo horario para %s: %s', turno, h)

    logger.info('Voy a ver docentes. Puedo llegar a agregar hasta %d', len(docentes))
    for docente in docentes:
        doc, creado = Docente.objects.get_or_create(nombre=docente[0],
                                                    defaults={'cargas': 1, 'cargo': docente[1]})
        if creado:
            logger.info('agregue a: %s', doc)


if __name__ == '__main__':
    html = lee_horarios_anteriores(2019, 1)
    salva_datos(html, 2020, 'P')
