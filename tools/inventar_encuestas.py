import random
import logging
from pathlib import Path
import argparse

from django.utils import timezone
from django.utils.dateparse import parse_time
import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from materias.models import (Materia, Turno, Docente, Cuatrimestres, TipoTurno, Cargos, choice_enum)
from encuestas.views import Mapeos, TipoDocentes, PreferenciasDocente


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def inventar_encuestas(anno, cuatrimestre, tipo_de_docentes):
    now = timezone.now()
    docentes = Mapeos.docentes(tipo_de_docentes)
    turnos = Mapeos.encuesta_tipo_turno(tipo_de_docentes).filter(anno=anno, cuatrimestre=cuatrimestre)

    for docente in docentes:
        logger.info('inventando encuestas para %s', docente)
        for turno in set(random.choices(turnos, k=5)):
            PreferenciasDocente.objects.create(docente=docente, turno=turno,
                                               peso=random.randint(0, 20),
                                               fecha_encuesta=now)


def parse():
    parser = argparse.ArgumentParser(description='Invento encuestas')
    parser.add_argument('-a', '--anno', type=int, required=True,
                        help='Año para inventar encuestas')
    parser.add_argument('-c', '--cuatrimestre', required=True,
                        choices=[c.name for c in Cuatrimestres],
                        help='Cuatrimestre para inventar encuestas')
    parser.add_argument('-d', '--docentes', required=True,
                        choices=[c.name for c in TipoDocentes],
                        help='Docentes para los que inventar encuestas')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse()
    inventar_encuestas(args.anno, args.cuatrimestre, args.docentes)
