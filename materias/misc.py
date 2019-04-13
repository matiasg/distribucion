from enum import Enum
from collections import namedtuple, defaultdict

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
        '''TipoDocentes -> [CargoDedicacion]'''
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
    def docentes_y_cargas(tipo, ac):
        '''TipoDocentes -> AnnoCuatrimestre -> {docente: [carga]}'''
        cargos = Mapeos.cargos_de_tipos(tipo)
        ret = defaultdict(list)
        for carga in Carga.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre, cargo__in=cargos):
            ret[carga.docente].append(carga)
        return ret

    @staticmethod
    def turnos_de_tipo_y_ac(tipo, ac):
        '''TipoDocentes -> AnnoCuatrimestre -> [Turno]'''
        return Mapeos.encuesta_tipo_turno(tipo).filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)

    @staticmethod
    def turno_y_necesidad(tipo, ac):
        '''TipoDocentes -> AnnoCuatrimestre -> {turno: necesidad}'''
        return {turno: MapeosDistribucion.necesidades(turno, tipo)
                for turno in Mapeos.turnos_de_tipo_y_ac(tipo, ac)}


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

    @staticmethod
    def cargas(tipo, ac):
        '''TipoDocentes -> AnnoCuatrimestre -> {Carga}'''
        doc_y_cargas = Mapeos.docentes_y_cargas(tipo, ac)
        return {c for d_cargas in doc_y_cargas.values() for c in d_cargas}

    @staticmethod
    def asignaciones(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> [Asignacion]'''
        cargas = Mapeos.cargas(tipo, ac)
        asignaciones = Asignacion.objects.filter(turno__anno=ac.anno,
                                                 turno__cuatrimestre=ac.cuatrimestre,
                                                 intento=intento)
        return [a for a in asignaciones if a.carga in cargas]

    @staticmethod
    def docentes_y_asignaciones(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> {Docente: [Asignacion]}'''
        cargas = Mapeos.cargas(tipo, ac)
        asignaciones = Asignacion.objects.filter(turno__anno=ac.anno,
                                                 turno__cuatrimestre=ac.cuatrimestre,
                                                 intento=intento)
        ret = defaultdict(list)
        for asignacion in asignaciones:
            if asignacion.carga in cargas:
                ret[asignacion.carga.docente].append(asignacion)
        return ret







class MapeosDistribucion:

    @staticmethod
    def necesidades(turno, tipo_docente):
        if tipo_docente == TipoDocentes.P.name:
            return turno.necesidad_prof
        elif tipo_docente == TipoDocentes.J.name:
            return turno.necesidad_jtp
        elif tipo_docente == TipoDocentes.A1.name:
            return turno.necesidad_ay1
        else:
            return turno.necesidad_ay2

