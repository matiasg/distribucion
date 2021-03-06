from django.test import TestCase, Client

from collections import Counter

from materias.models import (Materia, Turno, TipoTurno, Cargos, Carga, CargoDedicacion,
                             Docente, TipoDocentes, TipoMateria, Cuatrimestres)
from materias.misc import Mapeos, AnnoCuatrimestre
from dborrador.models import Asignacion, Intento
from dborrador.misc import Distribucion

class TestDistribucion(TestCase):

    def setUp(self):
        anno = 2100
        cuatrimestre = Cuatrimestres.P.name
        self.ac = AnnoCuatrimestre(anno, cuatrimestre)
        self.n = Docente.objects.create(na_nombre='nemo',
                                        telefono='00 0000',
                                        email='nemo@nautilus.org',
                                        cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        self.m = Docente.objects.create(na_nombre='mario', telefono='11 1111', email='mario@nautilus.org',
                                        cargos=[CargoDedicacion.AsoPar.name])
        self.materia = Materia.objects.create(nombre='navegacion', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=2, necesidad_jtp=3, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=0, necesidad_jtp=2, necesidad_ay1=3, necesidad_ay2=4)

        def genera_cargas(cantidades, publicadas, docente, turno):
            cargas = {t: [] for t in TipoDocentes}
            for tipo, cantidad, pub, cargo in zip(TipoDocentes, cantidades,
                                                  publicadas, [Cargos.Tit, Cargos.JTP, Cargos.Ay1, Cargos.Ay2]):

                for k in range(cantidad):
                    cargas[tipo].append(Carga.objects.create(docente=docente, cargo=(cargo.name + 'Exc'),
                                                             anno=anno, cuatrimestre=cuatrimestre,
                                                             turno=turno if k < pub else None))
            return cargas

        self.cargas_turno_1 = genera_cargas([2, 3, 0, 0], [1, 1, 0, 0], self.m, self.turno1)
        self.cargas_turno_2 = genera_cargas([0, 2, 3, 4], [0, 1, 1, 1], self.n, self.turno2)

        self.asignacion_1_1 = Asignacion.objects.create(intentos=(Intento.de_algoritmo(-1).valor, None),
                                                        carga=self.cargas_turno_1[TipoDocentes.P][1], turno=self.turno1,
                                                        cargo_que_ocupa=TipoDocentes.P.name)
        Asignacion.objects.create(intentos=(Intento.de_algoritmo(-1).valor, None),
                                  carga=self.cargas_turno_2[TipoDocentes.J][1], turno=self.turno2,
                                  cargo_que_ocupa=TipoDocentes.J.name)
        Asignacion.objects.create(intentos=(Intento.de_algoritmo(-1).valor, None),
                                  carga=self.cargas_turno_2[TipoDocentes.A1][1], turno=self.turno2,
                                  cargo_que_ocupa=TipoDocentes.A1.name)

        Asignacion.objects.create(intentos=(Intento.de_algoritmo(0).valor, None),
                                  carga=self.cargas_turno_1[TipoDocentes.J][1], turno=self.turno1,
                                  cargo_que_ocupa=TipoDocentes.J.name)
        Asignacion.objects.create(intentos=(Intento.de_algoritmo(0).valor, None),
                                  carga=self.cargas_turno_2[TipoDocentes.A2][1], turno=self.turno2,
                                  cargo_que_ocupa=TipoDocentes.A2.name)

        Asignacion.objects.create(intentos=(Intento.de_algoritmo(1).valor, Intento.de_algoritmo(2).valor),
                                  carga=self.cargas_turno_1[TipoDocentes.J][2], turno=self.turno1,
                                  cargo_que_ocupa=TipoDocentes.J.name)
        Asignacion.objects.create(intentos=(Intento.de_algoritmo(1).valor, Intento.de_algoritmo(2).valor),
                                  carga=self.cargas_turno_2[TipoDocentes.A2][2], turno=self.turno2,
                                  cargo_que_ocupa=TipoDocentes.A2.name)
        # T1 nec: (2300) pub: (1100) otro: (1000) fijo: (0100) int1: (0100)
        # T2 nec: (0234) pub: (0111) otro: (0110) fijo: (0001) int1: (0001)

    def test_asignaciones_por_cargo_ocupado(self):
        asignaciones = Distribucion.asignaciones_por_cargo_ocupado(self.ac, Intento.de_algoritmo(1))
        self.assertEqual(set(asignaciones[self.turno1][TipoDocentes.P]), {self.asignacion_1_1})
