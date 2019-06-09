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

from materias.models import (Materia, Turno, Docente, Carga, Cuatrimestres, TipoTurno,
                             CargoDedicacion, Cargos, TipoDocentes, choice_enum)
from materias.misc import Mapeos
from encuestas.models import PreferenciasDocente


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def inventar_encuestas(anno, cuatrimestre, tipo_de_docentes):
    now = timezone.now()
    tipo = TipoDocentes[tipo_de_docentes]
    cargos = set(Mapeos.cargos_de_tipos(tipo))
    docentes = Mapeos.docentes_de_tipo(tipo)
    turnos = Mapeos.encuesta_tipo_turno(tipo).filter(anno=anno, cuatrimestre=cuatrimestre)

    for docente in docentes:
        doc_cargos = cargos & set(docente.cargos)
        logger.info('inventando encuestas para %s', docente)

        for cargo in doc_cargos:
            Carga.objects.get_or_create(docente=docente, cargo=cargo,
                                        anno=anno, cuatrimestre=cuatrimestre)

        for turno in set(random.choices(turnos, k=5)):
            for cargo in doc_cargos:
                PreferenciasDocente.objects.create(docente=docente, turno=turno,
                                                   cargo=cargo[:3],
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
