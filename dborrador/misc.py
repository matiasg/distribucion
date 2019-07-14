from collections import Counter, namedtuple, defaultdict

from .models import Asignacion, Preferencia
from materias.misc import Mapeos
from materias.models import TipoDocentes, Turno, Cargos, Carga


Problemas = namedtuple('Problemas', ['cargas_no_distribuidas', 'necesidades_no_cubiertas', 'recargas'])


class Distribucion:

    @classmethod
    def asignaciones_por_cargo_ocupado(cls, ac, intento):
        '''AnnoCuatrimestre -> Intento -> {Turno -> TipoDocentes -> [Asignacion]}'''
        turnos = Turno.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)
        ret = {t: defaultdict(list) for t in turnos}

        asignaciones = Asignacion.validas_en(ac.anno, ac.cuatrimestre, intento).filter(turno__anno=ac.anno, turno__cuatrimestre=ac.cuatrimestre)
        for asignacion in asignaciones:
            tipo = TipoDocentes[asignacion.cargo_que_ocupa]
            ret[asignacion.turno][tipo].append(asignacion)
        return ret

    @classmethod
    def ya_distribuidas_por_cargo(cls, ac):
        '''AnnoCuatrimestre -> {Turno -> TipoDocentes -> [Asignacion]}'''
        ret = {}
        for turno in Turno.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre):
            ret[turno] = defaultdict(list)
            for carga in turno.carga_set.all():
                tipo = Mapeos.tipo_de_carga(carga)
                ret[turno][tipo].append(carga)
        return ret

    @classmethod
    def no_distribuidas_por_cargo(cls, ac):
        '''AnnoCuatrimestre -> {TipoDocentes -> [Carga]}'''
        ret = defaultdict(list)
        cargas = Carga.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre, turno__isnull=True)
        for carga in cargas:
            tipo = Mapeos.tipo_de_carga(carga)
            ret[tipo].append(carga)
        return ret
