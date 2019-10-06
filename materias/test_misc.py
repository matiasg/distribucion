from django.test import TestCase, Client

from materias.models import (Materia, Turno, TipoTurno, Cargos, Carga, Dedicaciones, CargoDedicacion,
                             Docente, TipoMateria, Cuatrimestres)
from materias.misc import Mapeos, TipoDocentes, AnnoCuatrimestre
from dborrador.models import Asignacion


class TestMapeos(TestCase):

    def setUp(self):
        anno = 2100
        cuatrimestre = Cuatrimestres.P.name
        self.ac = AnnoCuatrimestre(anno, cuatrimestre)
        self.n = Docente.objects.create(na_nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        self.m = Docente.objects.create(na_nombre='mario', telefono='11 1111', email='mario@nautilus.org',
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
        self.asignacion1 = Asignacion.objects.create(intentos=(1, 3), carga=self.carga1, turno=self.turno1)
        self.asignacion2 = Asignacion.objects.create(intentos=(1, 3), carga=self.carga2, turno=self.turno3)
        self.asignacion3 = Asignacion.objects.create(intentos=(1, 3), carga=self.carga3, turno=self.turno2)

    def test_cargos_de_tipos(self):
        cardeds = Mapeos.cargos_de_tipos(TipoDocentes.P)
        self.assertEqual(len(cardeds), 8 * 3)
        some_expected = { 'TitSim', 'AsoSmx', 'AdjExc', 'VisSim', 'HonExc' }
        self.assertTrue(set(cardeds).issuperset(some_expected))

    def test_docentes_de_tipo(self):
        docs = Mapeos.docentes_de_tipo(TipoDocentes.P, 2100)
        self.assertEqual(set(docs), {self.n, self.m})

        docs = Mapeos.docentes_de_tipo(TipoDocentes.J, 2100)
        self.assertEqual(set(docs), set())

        docs = Mapeos.docentes_de_tipo(TipoDocentes.A1, 2100)
        self.assertEqual(set(docs), {self.n})

        docs = Mapeos.docentes_de_tipo(TipoDocentes.A2, 2100)
        self.assertEqual(set(docs), set())

    def test_docentes_y_cargas(self):
        doccargas = Mapeos.docentes_y_cargas(TipoDocentes.P, self.ac)
        self.assertEqual(set(doccargas), {self.n, self.m})
        self.assertEqual(doccargas[self.n], [self.carga1])
        self.assertEqual(doccargas[self.m], [self.carga3])

    def test_turnos_de_tipo_y_ac(self):
        turnos_p = Mapeos.turnos_de_tipo_y_ac(TipoDocentes.P, self.ac)
        turnos_j = Mapeos.turnos_de_tipo_y_ac(TipoDocentes.J, self.ac)
        self.assertEqual(set(turnos_p), {self.turno1, self.turno2})
        self.assertEqual(set(turnos_j), {self.turno3})

    def test_turno_y_necesidad(self):
        turno_necesidad_p = Mapeos.turno_y_necesidad(TipoDocentes.P, self.ac)
        turno_necesidad_j = Mapeos.turno_y_necesidad(TipoDocentes.J, self.ac)
        self.assertEqual(turno_necesidad_p, {self.turno1: 1, self.turno2: 1})
        self.assertEqual(turno_necesidad_j, {self.turno3: 1})

    def test_encuesta_tipo_turno(self):
        turnos_prof = Mapeos.encuesta_tipo_turno(TipoDocentes.P)
        self.assertEqual(set(turnos_prof), {self.turno1, self.turno2})
        turnos_jtp = Mapeos.encuesta_tipo_turno(TipoDocentes.J)
        self.assertEqual(set(turnos_jtp), {self.turno3})

    def test_necesidades(self):
        necesidades_turno1 = {t: Mapeos.necesidades(self.turno1, t) for t in TipoDocentes}
        self.assertEqual(necesidades_turno1, {TipoDocentes.P: 1, TipoDocentes.J: 0, TipoDocentes.A1: 0, TipoDocentes.A2: 0})
        necesidades_turno3 = {t: Mapeos.necesidades(self.turno3, t) for t in TipoDocentes}
        self.assertEqual(necesidades_turno3, {TipoDocentes.P: 0, TipoDocentes.J: 1, TipoDocentes.A1: 1, TipoDocentes.A2: 0})

    def test_cargas_no_asignadas_en(self):
        self.carga1.turno = self.turno1
        self.carga1.save()
        cargas = Mapeos.cargas_no_asignadas_en(self.ac)
        self.assertEqual(set(cargas), {self.carga2, self.carga3})

    def test_cargas_asignadas_en(self):
        self.carga1.turno = self.turno1
        self.carga1.save()
        turno_cargas = Mapeos.cargas_asignadas_en(self.ac)
        self.assertEqual(turno_cargas, {self.turno1: [self.carga1]})

    def test_orden_tipodocente(self):
        self.assertGreaterEqual(TipoDocentes.P, TipoDocentes.P)
        self.assertGreaterEqual(TipoDocentes.P, TipoDocentes.J)
        self.assertGreaterEqual(TipoDocentes.P, TipoDocentes.A1)
        self.assertGreaterEqual(TipoDocentes.P, TipoDocentes.A2)
        self.assertGreaterEqual(TipoDocentes.J, TipoDocentes.A2)
        self.assertGreaterEqual(TipoDocentes.A1, TipoDocentes.A2)
        self.assertGreaterEqual(TipoDocentes.A2, TipoDocentes.A2)

    def test_filtra_tipo_ge(self):
        cargas = [self.carga1, self.carga2, self.carga3]
        self.assertEqual(Mapeos.filtrar_cargas_de_tipo_ge(TipoDocentes.P, cargas), [self.carga1, self.carga3])
        self.assertEqual(Mapeos.filtrar_cargas_de_tipo_ge(TipoDocentes.J, cargas), [self.carga1, self.carga3])
        self.assertEqual(Mapeos.filtrar_cargas_de_tipo_ge(TipoDocentes.A1, cargas), [self.carga1, self.carga2, self.carga3])
        self.assertEqual(Mapeos.filtrar_cargas_de_tipo_ge(TipoDocentes.A2, cargas), [self.carga1, self.carga2, self.carga3])

    def test_docentes_con_cargos_de_tipo(self):
        self.assertEqual(set(Mapeos.docentes_con_cargo_de_tipo(TipoDocentes.P)), {self.n, self.m})
        self.assertEqual(set(Mapeos.docentes_con_cargo_de_tipo(TipoDocentes.J)), set())
        self.assertEqual(set(Mapeos.docentes_con_cargo_de_tipo(TipoDocentes.A1)), {self.n})
        self.assertEqual(set(Mapeos.docentes_con_cargo_de_tipo(TipoDocentes.A2)), set())

    def test_necesidades_no_cubiertas(self):
        anno = 2108
        cuatrimestre = Cuatrimestres.S.name
        turno = Turno.objects.create(materia=self.materia, anno=anno, cuatrimestre=cuatrimestre,
                                           numero=7, tipo=TipoTurno.T.name,
                                           necesidad_prof=1, necesidad_jtp=8, necesidad_ay1=3, necesidad_ay2=2)
        self.assertEqual(Mapeos.necesidades_no_cubiertas(turno, TipoDocentes.J), 8)
        carga1 = Carga.objects.create(docente=self.n, turno=turno, cargo=CargoDedicacion.JTPExc.name, anno=anno, cuatrimestre=cuatrimestre)
        self.assertEqual(Mapeos.necesidades_no_cubiertas(turno, TipoDocentes.J), 7)
        carga2 = Carga.objects.create(docente=self.n, turno=turno, cargo=CargoDedicacion.TitExc.name, anno=anno, cuatrimestre=cuatrimestre)
        self.assertEqual(Mapeos.necesidades_no_cubiertas(turno, TipoDocentes.J), 7)

