from enum import Enum
from collections import namedtuple, defaultdict

from materias.models import Docente, Turno, Carga, TipoTurno, Cargos, CargoDedicacion, TipoDocentes, AnnoCuatrimestre


class Mapeos:
    '''Esta clase resuelve distintos tipos de mapeos'''

    tipo_a_cargos = {TipoDocentes.P: [Cargos.Tit, Cargos.Aso, Cargos.Adj],
                     TipoDocentes.J: [Cargos.JTP],
                     TipoDocentes.A1: [Cargos.Ay1],
                     TipoDocentes.A2: [Cargos.Ay2],
                     }

    cargos_a_tipo = {
        Cargos.Tit: TipoDocentes.P,
        Cargos.Aso: TipoDocentes.P,
        Cargos.Adj: TipoDocentes.P,
        Cargos.JTP: TipoDocentes.J,
        Cargos.Ay1: TipoDocentes.A1,
        Cargos.Ay2: TipoDocentes.A2,
    }

    @staticmethod
    def cargas_de_tipo(cargas, tipo):
        '''[Carga] -> TipoDocentes -> [Carga]'''
        return [carga for carga in cargas if Cargos[carga.cargo[:3]] in Mapeos.tipo_a_cargos[tipo]]

    @staticmethod
    def cargos_de_tipos(tipo):
        '''TipoDocentes -> [CargoDedicacion]'''
        cardeds = [cd
                   for cargo in Mapeos.tipo_a_cargos[tipo]
                   for cd in CargoDedicacion.con_cargo(cargo)]
        return cardeds

    @staticmethod
    def tipo_de_carga(carga):
        return Mapeos.cargos_a_tipo[Cargos[carga.cargo[:3]]]

    @staticmethod
    def tipos_de_cargo(cargodedicacion):
        '''CargoDedicacion -> TipoDocentes'''
        el_mapa = {Cargos.Tit.name: TipoDocentes.P,
                   Cargos.Aso.name: TipoDocentes.P,
                   Cargos.Adj.name: TipoDocentes.P,
                   Cargos.JTP.name: TipoDocentes.J,
                   Cargos.Ay1.name: TipoDocentes.A1,
                   Cargos.Ay2.name: TipoDocentes.A2
                   }
        return el_mapa[cargodedicacion[:3]]

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
        return {turno: Mapeos.necesidades(turno, tipo)
                for turno in Mapeos.turnos_de_tipo_y_ac(tipo, ac)}

    @staticmethod
    def necesidades_por_turno_y_tipo(ac):
        '''AnnoCuatrimestre -> {Turno -> TipoDocentes -> int}'''
        return {turno: {tipo: Mapeos.necesidades(turno, tipo)
                        for tipo in TipoDocentes}
                for turno in Turno.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)}

    @staticmethod
    def encuesta_tipo_turno(tipo_docente):
        '''
        Para profesores: teóricas y teórico-prácticas.
        Para auxiliares: prácticas y teórico-prácticas.
        '''
        el_mapa = {TipoDocentes.P: [TipoTurno.T.name, TipoTurno.A.name],
                   TipoDocentes.J: [TipoTurno.P.name, TipoTurno.A.name],
                   TipoDocentes.A1: [TipoTurno.P.name, TipoTurno.A.name],
                   TipoDocentes.A2: [TipoTurno.P.name, TipoTurno.A.name],
                   }
        tipos = el_mapa[tipo_docente]
        return Turno.objects.filter(tipo__in=tipos)

    @staticmethod
    def cargas(tipo, ac):
        '''TipoDocentes -> AnnoCuatrimestre -> {Carga}'''
        doc_y_cargas = Mapeos.docentes_y_cargas(tipo, ac)
        return {c for d_cargas in doc_y_cargas.values() for c in d_cargas}

    @staticmethod
    def cargas_no_asignadas_en(ac):
        '''AnnoCuatrimestre -> [Carga]'''
        return [carga
                for carga in Carga.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)
                if carga.turno is None]

    @staticmethod
    def cargas_asignadas_en(ac):
        '''AnnoCuatrimestre -> {Turno: [Carga]}'''
        ret = defaultdict(list)
        for carga in Carga.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre, turno__isnull=False):
            ret[carga.turno].append(carga)
        return ret

    @staticmethod
    def necesidades(turno, tipo_docente):
        if tipo_docente == TipoDocentes.P:
            return turno.necesidad_prof
        elif tipo_docente == TipoDocentes.J:
            return turno.necesidad_jtp
        elif tipo_docente == TipoDocentes.A1:
            return turno.necesidad_ay1
        else:
            return turno.necesidad_ay2

    @staticmethod
    def filtrar_cargas_de_tipo_ge(tipo_docente, cargas):
        '''TipoDocentes -> [Carga] -> [Carga]'''
        return [carga
                for carga in cargas
                if Mapeos.tipos_de_cargo(carga.cargo) >= tipo_docente
                ]
