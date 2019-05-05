from django.test import TestCase, Client

import datetime

from materias.models import (Cargos, Dedicaciones, CargoDedicacion, Docente,
                             Materia, Turno, TipoMateria, TipoTurno, Dias, Cuatrimestres,
                             Horario)

class TestModels(TestCase):

    def setUp(self):
        self.materia = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        self.turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                          numero=1, tipo=TipoTurno.T.name,
                                          necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)

    def test_con_cargo(self):
        for cargo in Cargos:
            cc = CargoDedicacion.con_cargo(cargo)
            self.assertEquals(len(cc), len(Dedicaciones))

    def test_mas_de_un_cargo(self):
        n = Docente.objects.create(nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])

        nemos = Docente.objects.filter(nombre='nemo')
        self.assertEquals(len(nemos), 1)
        self.assertEquals(nemos.first(), n)

        titulares = Docente.objects.filter(cargos__overlap=CargoDedicacion.con_cargo(Cargos.Tit))
        self.assertEquals(len(titulares), 1)
        self.assertEquals(titulares.first(), n)

    def test_nada(self):
        n = Docente.objects.create(nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        m = Docente.objects.create(nombre='mario', telefono='', email='',
                                   cargos=[CargoDedicacion.Ay2Sim.name, CargoDedicacion.Ay2Sim.name])
        o = Docente.objects.create(nombre='ovidio',
                                   cargos=[CargoDedicacion.Ay2Sim.name])
        ayds1 = Docente.todos_los(Cargos.Ay1)
        self.assertEquals(len(ayds1), 1)
        self.assertEquals(ayds1.first(), n)

        ayds2 = Docente.todos_los(Cargos.Ay2)
        self.assertEquals(len(ayds2), 2)
        self.assertEquals(set(ayds2), set([m, o]))

    def test_cantidad_de_alumnos(self):
        tdict = {'materia': self.materia, 'anno': 2100, 'cuatrimestre': Cuatrimestres.V.name,
                 'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        t1 = Turno.objects.create(numero=1, tipo=TipoTurno.T.name, alumnos=89, **tdict)

        t1.poner_necesidades_segun_alumnos()
        self.assertEquals(t1.necesidad_prof, 1)
        self.assertEquals(t1.necesidad_jtp, 0)

        t2 = Turno.objects.create(numero=1, tipo=TipoTurno.A.name, alumnos=89, **tdict)
        t2.poner_necesidades_segun_alumnos()
        self.assertEquals(t2.necesidad_prof, 1)
        self.assertEquals(t2.necesidad_jtp, 1)
        self.assertEquals(t2.necesidad_ay1, 1)
        self.assertEquals(t2.necesidad_ay2, 1)

        t3 = Turno.objects.create(numero=1, tipo=TipoTurno.P.name, alumnos=89, **tdict)
        t3.poner_necesidades_segun_alumnos()
        self.assertEquals(t3.necesidad_prof, 0)
        self.assertEquals(t3.necesidad_jtp, 1)
        self.assertEquals(t3.necesidad_ay1, 1)
        self.assertEquals(t3.necesidad_ay2, 2)

    def test_orden_dias(self):
        self.assertLess(Dias.Lu, Dias.Ma)
        self.assertLess(Dias.Ma, Dias.Mi)
        self.assertLess(Dias.Mi, Dias.Ju)
        self.assertLess(Dias.Ju, Dias.Vi)
        self.assertGreater(Dias.Ma, Dias.Lu)  # chequeo que funciona tambien >
        self.assertLessEqual(Dias.Lu, Dias.Lu)  # chequeo que funciona tambien <=
        self.assertGreaterEqual(Dias.Ma, Dias.Lu)  # chequeo que funciona tambien >=

    def test_orden_horarios(self):
        # Nota: <= y >= no implementados en Horario
        h1 = Horario.objects.create(dia=Dias.Lu.name, comienzo=datetime.time(9), final=datetime.time(10), turno=self.turno)
        h2 = Horario.objects.create(dia=Dias.Ma.name, comienzo=datetime.time(8), final=datetime.time(9), turno=self.turno)
        self.assertLess(h1, h2)
        self.assertGreater(h2, h1)

    def test_orden_turnos(self):
        # Nota: <= y >= no implementados en Turno
        turno2 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=1, tipo=TipoTurno.T.name,
                                      necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        Horario.objects.create(dia=Dias.Lu.name, comienzo=datetime.time(9), final=datetime.time(10), turno=self.turno)
        Horario.objects.create(dia=Dias.Ma.name, comienzo=datetime.time(8), final=datetime.time(9), turno=self.turno)
        Horario.objects.create(dia=Dias.Lu.name, comienzo=datetime.time(10), final=datetime.time(11), turno=turno2)
        Horario.objects.create(dia=Dias.Ma.name, comienzo=datetime.time(7), final=datetime.time(8), turno=turno2)
        self.assertLess(self.turno, turno2)
        self.assertGreater(turno2, self.turno)
