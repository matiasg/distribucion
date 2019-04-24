from django.test import TestCase, Client

from materias.models import (Materia, Turno, TipoTurno, Cargos, Carga, Dedicaciones, CargoDedicacion,
                             Docente, TipoMateria, Cuatrimestres)
from materias.misc import Mapeos, TipoDocentes, AnnoCuatrimestre
from dborrador.models import Asignacion
from dborrador.misc import MapeosDistribucion


class TestMapeos(TestCase):

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
                                           numero=1, tipo=TipoTurno.T.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=2, tipo=TipoTurno.T.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno3 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=1, tipo=TipoTurno.P.name,
                                           necesidad_prof=0, necesidad_jtp=1, necesidad_ay1=1, necesidad_ay2=0)
        self.carga1 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                                           anno=anno, cuatrimestre=cuatrimestre)
        self.carga2 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.Ay1Smx.name,
                                           anno=anno, cuatrimestre=cuatrimestre)
        self.carga3 = Carga.objects.create(docente=self.m, cargo=CargoDedicacion.AsoSim.name,
                                           anno=anno, cuatrimestre=cuatrimestre)
        self.asignacion1 = Asignacion.objects.create(intento=3, carga=self.carga1, turno=self.turno1)
        self.asignacion2 = Asignacion.objects.create(intento=3, carga=self.carga2, turno=self.turno3)
        self.asignacion3 = Asignacion.objects.create(intento=3, carga=self.carga3, turno=self.turno2)

    def test_cargos_de_tipos(self):
        cardeds = Mapeos.cargos_de_tipos(TipoDocentes.P.name)
        self.assertEqual(len(cardeds), 3 * 3)
        some_expected = { 'TitSim', 'AsoSmx', 'AdjExc' }
        self.assertTrue(set(cardeds).issuperset(some_expected))

    def test_docentes_de_tipo(self):
        docs = Mapeos.docentes_de_tipo(TipoDocentes.P.name)
        self.assertEqual(set(docs), {self.n, self.m})

        docs = Mapeos.docentes_de_tipo(TipoDocentes.J.name)
        self.assertEqual(set(docs), set())

        docs = Mapeos.docentes_de_tipo(TipoDocentes.A1.name)
        self.assertEqual(set(docs), {self.n})

        docs = Mapeos.docentes_de_tipo(TipoDocentes.A2.name)
        self.assertEqual(set(docs), set())

    def test_docentes_y_cargas(self):
        doccargas = Mapeos.docentes_y_cargas(TipoDocentes.P.name, self.ac)
        self.assertEqual(set(doccargas), {self.n, self.m})
        self.assertEqual(doccargas[self.n], [self.carga1])
        self.assertEqual(doccargas[self.m], [self.carga3])

    def test_turnos_de_tipo_y_ac(self):
        turnos_p = Mapeos.turnos_de_tipo_y_ac(TipoDocentes.P.name, self.ac)
        turnos_j = Mapeos.turnos_de_tipo_y_ac(TipoDocentes.J.name, self.ac)
        self.assertEqual(set(turnos_p), {self.turno1, self.turno2})
        self.assertEqual(set(turnos_j), {self.turno3})

    def test_turno_y_necesidad(self):
        turno_necesidad_p = Mapeos.turno_y_necesidad(TipoDocentes.P.name, self.ac)
        turno_necesidad_j = Mapeos.turno_y_necesidad(TipoDocentes.J.name, self.ac)
        self.assertEqual(turno_necesidad_p, {self.turno1: 1, self.turno2: 1})
        self.assertEqual(turno_necesidad_j, {self.turno3: 1})

    def test_encuesta_tipo_turno(self):
        turnos_prof = Mapeos.encuesta_tipo_turno(TipoDocentes.P.name)
        self.assertEqual(set(turnos_prof), {self.turno1, self.turno2})
        turnos_jtp = Mapeos.encuesta_tipo_turno(TipoDocentes.J.name)
        self.assertEqual(set(turnos_jtp), {self.turno3})

    def test_asignaciones(self):
        asignaciones_p_1 = MapeosDistribucion.asignaciones(TipoDocentes.P.name, self.ac, 1)
        asignaciones_p_3 = MapeosDistribucion.asignaciones(TipoDocentes.P.name, self.ac, 3)
        asignaciones_j_3 = MapeosDistribucion.asignaciones(TipoDocentes.J.name, self.ac, 3)
        asignaciones_a_3 = MapeosDistribucion.asignaciones(TipoDocentes.A1.name, self.ac, 3)
        self.assertEqual(asignaciones_p_1, [])
        self.assertEqual(set(asignaciones_p_3), {self.asignacion1, self.asignacion3})
        self.assertEqual(asignaciones_j_3, [])
        self.assertEqual(set(asignaciones_a_3), {self.asignacion2})

    def test_docentes_y_asignaciones(self):
        asignaciones_p_3 = MapeosDistribucion.docentes_y_asignaciones(TipoDocentes.P.name, self.ac, 3)
        asignaciones_j_3 = MapeosDistribucion.docentes_y_asignaciones(TipoDocentes.J.name, self.ac, 3)
        asignaciones_a_3 = MapeosDistribucion.docentes_y_asignaciones(TipoDocentes.A1.name, self.ac, 3)
        self.assertEqual(asignaciones_p_3, {self.n: [self.asignacion1], self.m: [self.asignacion3]})
        self.assertEqual(asignaciones_j_3, {})
        self.assertEqual(asignaciones_a_3, {self.n: [self.asignacion2]})

    def test_necesidades(self):
        necesidades_turno1 = {t: Mapeos.necesidades(self.turno1, t.name) for t in TipoDocentes}
        self.assertEqual(necesidades_turno1, {TipoDocentes.P: 1, TipoDocentes.J: 0, TipoDocentes.A1: 0, TipoDocentes.A2: 0})
        necesidades_turno3 = {t: Mapeos.necesidades(self.turno3, t.name) for t in TipoDocentes}
        self.assertEqual(necesidades_turno3, {TipoDocentes.P: 0, TipoDocentes.J: 1, TipoDocentes.A1: 1, TipoDocentes.A2: 0})


class TestMasMapeos(TestCase):

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
                                           numero=1, tipo=TipoTurno.T.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=2, tipo=TipoTurno.T.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno3 = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=1, tipo=TipoTurno.P.name,
                                           necesidad_prof=0, necesidad_jtp=1, necesidad_ay1=1, necesidad_ay2=0)
        self.carga1 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                                           anno=anno, cuatrimestre=cuatrimestre,
                                           turno=self.turno1)
        self.carga2 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.Ay1Smx.name,
                                           anno=anno, cuatrimestre=cuatrimestre)
        self.carga3 = Carga.objects.create(docente=self.m, cargo=CargoDedicacion.AsoSim.name,
                                           anno=anno, cuatrimestre=cuatrimestre)

    def test_cargas_no_asignadas_en(self):
        cargas = Mapeos.cargas_no_asignadas_en(self.ac)
        self.assertEqual(set(cargas), {self.carga2, self.carga3})

    def test_cargas_asignadas_en(self):
        turno_cargas = Mapeos.cargas_asignadas_en(self.ac)
        self.assertEqual(turno_cargas, {self.turno1: [self.carga1]})
