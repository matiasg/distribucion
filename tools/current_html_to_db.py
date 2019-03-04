from bs4 import BeautifulSoup
import logging
from pathlib import Path
import re
import urllib.request as request

import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import Materia, Turno, Horario, Docente, TipoMateria, TipoTurno, Cargos

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

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

            turno = Turno(materia=materia,
                          anno=nuevo_anno,
                          cuatrimestre=nuevo_cuatrimestre,
                          numero=int(tipoynumero[1]) if len(tipoynumero) > 1 else 0,
                          tipo=tipo_turno,
                          necesidades='0,0,0')
            turno.save()
            turno_docentes = rows[2].text.split(' — ')
            cargo = cargo_tipoturno[tipoynumero[0]]

            for docente in turno_docentes:
                docentes.add((docente, cargo))

    logger.info('Voy a agregar hasta %d docentes', len(docentes))
    for docente in docentes:
        doc, creado = Docente.objects.get_or_create(nombre=docente[0],
                                                    defaults={'cargas': 1, 'cargo': docente[1]})
        if creado:
            print(f'agregue a: {doc}')


if __name__ == '__main__':
    html = lee_horarios_anteriores(2019, 1)
    salva_datos(html, 2020, 'P')
