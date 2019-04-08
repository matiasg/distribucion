from django.test import TestCase, Client

from materias.models import Cargos, Dedicaciones, CargoDedicacion, Docente

class TestModels(TestCase):

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
