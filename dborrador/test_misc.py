from django.test import TestCase, Client

from collections import Counter

from materias.models import (Materia, Turno, TipoTurno, Cargos, Carga, CargoDedicacion,
                             Docente, TipoMateria, Cuatrimestres)
from materias.misc import Mapeos, TipoDocentes, AnnoCuatrimestre
from dborrador.models import Asignacion
from dborrador.misc import MapeosDistribucion

class TestMapeosDistribucion(TestCase):

    def setUp(self):
        anno = 2100
        cuatrimestre = Cuatrimestres.P.name
        self.ac = AnnoCuatrimestre(anno, cuatrimestre)
        self.n = Docente.objects.create(nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        self.m = Docente.objects.create(nombre='mario', telefono='11 1111', email='mario@nautilus.org',
                                   cargos=[CargoDedicacion.AsoSim.name])
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

        Asignacion.objects.create(intento=-1, carga=self.cargas_turno_1[TipoDocentes.P][1], turno=self.turno1)
        Asignacion.objects.create(intento=-1, carga=self.cargas_turno_2[TipoDocentes.J][1], turno=self.turno2)
        Asignacion.objects.create(intento=-1, carga=self.cargas_turno_2[TipoDocentes.A1][1], turno=self.turno2)

        Asignacion.objects.create(intento=0, carga=self.cargas_turno_1[TipoDocentes.J][1], turno=self.turno1)
        Asignacion.objects.create(intento=0, carga=self.cargas_turno_2[TipoDocentes.A2][1], turno=self.turno2)

        Asignacion.objects.create(intento=1, carga=self.cargas_turno_1[TipoDocentes.J][2], turno=self.turno1)
        Asignacion.objects.create(intento=1, carga=self.cargas_turno_2[TipoDocentes.A2][2], turno=self.turno2)
        # T1 nec: (2300) pub: (1100) otro: (1000) fijo: (0100) int1: (0100)
        # T2 nec: (0234) pub: (0111) otro: (0110) fijo: (0001) int1: (0001)

    def test_asignaciones_otro_tipo(self):
        cargas = MapeosDistribucion.cargas_otro_tipo(self.ac)
        self.assertEqual(cargas[self.turno1], [self.cargas_turno_1[TipoDocentes.P][1]])
        self.assertEqual(set(cargas[self.turno2]),
                         {self.cargas_turno_2[TipoDocentes.J][1], self.cargas_turno_2[TipoDocentes.A1][1]})

    def test_asignaciones_fijas(self):
        cargas = MapeosDistribucion.cargas_de_asignaciones_fijas(self.ac)
        self.assertEqual(cargas[self.turno1], [self.cargas_turno_1[TipoDocentes.J][1]])
        self.assertEqual(cargas[self.turno2], [self.cargas_turno_2[TipoDocentes.A2][1]])

    def test_asignaciones_intento(self):
        cargas = MapeosDistribucion.cargas_de_asignaciones_para_intento(self.ac, 1)
        self.assertEqual(cargas[self.turno1], [self.cargas_turno_1[TipoDocentes.J][2]])
        self.assertEqual(cargas[self.turno2], [self.cargas_turno_2[TipoDocentes.A2][2]])

    def test_cargas_tipo_ge_a_distribuir_en(self):
        self.assertEqual(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.P, self.ac, 1), [])
        self.assertEqual(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.P, self.ac, 2), [])
        self.assertEqual(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.J, self.ac, 1), [])
        self.assertEqual(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.J, self.ac, 2), [self.cargas_turno_1[TipoDocentes.J][2]])

        self.assertEqual(set(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.A1, self.ac, 1)),
                         {self.cargas_turno_2[TipoDocentes.A1][2]})
        self.assertEqual(set(MapeosDistribucion.cargas_tipo_ge_a_distribuir_en(TipoDocentes.A1, self.ac, 2)),
                         {self.cargas_turno_1[TipoDocentes.J][2], self.cargas_turno_2[TipoDocentes.A1][2]})

    def test_necesidades_no_cubiertas(self):
        # En este test se mezclan distribuciones de distinto TipoDocentes. Los resultados
        # no son los "intuitivos" y eso corresponde al diseño hecho. Mirar el docstring de
        # MapeosDistribucion.necesidades_tipo_no_cubiertas_en
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.P, self.ac, 1),
                         Counter())
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.J, self.ac, 1),
                         Counter([self.turno1]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.A1, self.ac, 1),
                         Counter([self.turno2]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.A2, self.ac, 1),
                         Counter([self.turno2, self.turno2]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.P, self.ac, 2),
                         Counter([self.turno1]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.J, self.ac, 2),
                         Counter([self.turno1, self.turno1, self.turno2]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.A1, self.ac, 2),
                         Counter([self.turno2, self.turno2]))
        self.assertEqual(MapeosDistribucion.necesidades_tipo_no_cubiertas_en(TipoDocentes.A2, self.ac, 2),
                         Counter([self.turno2, self.turno2, self.turno2]))
