from enum import Enum
from collections import namedtuple

from materias.models import Docente, Turno, Carga, TipoTurno, Cargos, CargoDedicacion
from dborrador.models import Preferencia, Asignacion


AnnoCuatrimestre = namedtuple('AC', 'anno cuatrimestre')

class TipoDocentes(Enum):
    '''P: profesor, J: JTP y Ay1, A: Ay2'''

    P = 'Profesores'
    J = 'JTP'
    A1 = 'Ay1'
    A2 = 'Ay2'


class Mapeos:
    '''Esta clase resuelve distintos tipos de mapeos'''

    @staticmethod
    def cargos_de_tipos(tipo):
        el_mapa = {TipoDocentes.P.name: [Cargos.Tit, Cargos.Aso, Cargos.Adj],
                   TipoDocentes.J.name: [Cargos.JTP],
                   TipoDocentes.A1.name: [Cargos.Ay1],
                   TipoDocentes.A2.name: [Cargos.Ay2],
                   }
        cardeds = [cd
                   for cargo in el_mapa[tipo.upper()]
                   for cd in CargoDedicacion.con_cargo(cargo)]
        return cardeds

    @staticmethod
    def docentes_de_tipo(tipo):
        '''TipoDocentes -> [docente]'''
        cardeds = Mapeos.cargos_de_tipos(tipo)
        return Docente.objects.filter(cargos__overlap=cardeds)

    @staticmethod
    def cargas_tipo(tipo):
        '''P | J | A1 | A2 => cargas docentes'''
        cardeds = Mapeos.cargos_de_tipos(tipo)
        Carga.objects.filter(cargo__overlap=cardeds)

    @staticmethod
    def encuesta_tipo_turno(tipo_docente):
        '''
        Para profesores: teóricas y teórico-prácticas.
        Para auxiliares: prácticas y teórico-prácticas.
        '''
        el_mapa = {TipoDocentes.P.name: [TipoTurno.T.name, TipoTurno.A.name],
                   TipoDocentes.J.name: [TipoTurno.P.name, TipoTurno.A.name],
                   TipoDocentes.A1.name: [TipoTurno.P.name, TipoTurno.A.name],
                   TipoDocentes.A2.name: [TipoTurno.P.name, TipoTurno.A.name],
                   }
        tipos = el_mapa[tipo_docente.upper()]
        return Turno.objects.filter(tipo__in=tipos)

