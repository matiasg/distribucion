from collections import Counter, namedtuple, defaultdict

from .models import Asignacion
from materias.misc import Mapeos


Problemas = namedtuple('Problemas', ['cargas_no_distribuidas', 'necesidades_no_cubiertas'])

class MapeosDistribucion:

    @staticmethod
    def cargas_a_distribuir(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> {Carga}'''
        asignaciones_previas = MapeosDistribucion.asignaciones(tipo, ac, intento)
        docentes_cargas = Mapeos.docentes_y_cargas(tipo, ac)
        cargas = {c
                  for d_cargas in docentes_cargas.values()
                  for c in d_cargas}
        # TODO: chequear que no hay dos asignaciones con la misma carga
        cargas_distribuidas = {a.carga for a in asignaciones_previas}
        return cargas - cargas_distribuidas

    @staticmethod
    def necesidades_no_cubiertas(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> {Turno: necesidad}.
        Obs: necesidad puede ser < 0 (y significa una mala distribución)'''
        asignaciones_previas = MapeosDistribucion.asignaciones(tipo, ac, intento)
        asignaciones_por_turno = Counter(a.turno for a in asignaciones_previas)
        turnos = Mapeos.encuesta_tipo_turno(tipo).filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)
        necesidades = {}
        for turno in turnos:
            necesidades[turno] = Mapeos.necesidades(turno, tipo) - asignaciones_por_turno.get(turno, 0)
        return necesidades

    # TODO: agregar métodos con
    #   docentes_ya_asignados (similar a Mapeos.docentes_y_asignaciones pero que contemple

    @staticmethod
    def asignaciones(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> [Asignacion]'''
        cargas = Mapeos.cargas(tipo, ac)
        # TODO: agregar intento 0
        asignaciones = Asignacion.objects.filter(turno__anno=ac.anno,
                                                 turno__cuatrimestre=ac.cuatrimestre,
                                                 intento=intento)
        return [a for a in asignaciones if a.carga in cargas]

    @staticmethod
    def docentes_y_asignaciones(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> {Docente: [Asignacion]}'''
        cargas = Mapeos.cargas(tipo, ac)
        # TODO: agregar intento 0
        asignaciones = Asignacion.objects.filter(turno__anno=ac.anno,
                                                 turno__cuatrimestre=ac.cuatrimestre,
                                                 intento=intento)
        ret = defaultdict(list)
        for asignacion in asignaciones:
            if asignacion.carga in cargas:
                ret[asignacion.carga.docente].append(asignacion)
        return ret

    @staticmethod
    def chequeo(tipo, ac, intento):
        '''TipoDocentes -> AnnoCuatrimestre -> intento -> ([Carga], [Turno, necesidad])'''
        cargas = MapeosDistribucion.cargas_a_distribuir(tipo, ac, intento)
        necesidades = MapeosDistribucion.necesidades_no_cubiertas(tipo, ac, intento)
        no_cubiertas = [(turno, necesidad) for turno, necesidad in necesidades.items() if necesidad > 0]
        return Problemas(cargas, no_cubiertas)
