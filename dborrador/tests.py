from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

import re

from dborrador.models import Preferencia, Asignacion
from materias.models import Docente, Materia, Turno, Cuatrimestres, Cargos, CargoDedicacion, TipoTurno, TipoMateria
from materias.misc import TipoDocentes
from encuestas.models import PreferenciasDocente

class TestPreparar(TestCase):

    def test_no_falla_si_no_hay_preferencias(self):
        c = Client()
        response = c.get('/dborrador/preparar')
        self.assertEqual(response.status_code, 200)

        response = c.post('/dborrador/preparar', {'anno': '2100', 'cuatrimestre': 'P', 'tipo': 'P'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertTrue(re.search('Copiadas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se copiaron 0 preferencias')
        self.assertTrue(re.search('Borradas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se borraron 0 preferencias')
        self.assertTrue('Preferencias copiadas' in response.content.decode(),
                        'La página debería decir "Preferencias copiadas" y dice {}'.format(
                            response.content.decode()))

    def test_copia_preferencias(self):
        docente = Docente.objects.create(nombre='juan', email='mail@nada.org',
                                         telefono='1234',
                                         cargos=[CargoDedicacion.TitSim.name])
        materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        turno1 = Turno.objects.create(materia=materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=1, tipo=TipoTurno.A.name,
                                      necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        turno2 = Turno.objects.create(materia=materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=2, tipo=TipoTurno.A.name,
                                      necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now = timezone.now()
        pref1 = PreferenciasDocente.objects.create(docente=docente, turno=turno1, peso=1, fecha_encuesta=now)
        pref2 = PreferenciasDocente.objects.create(docente=docente, turno=turno2, peso=3, fecha_encuesta=now)

        c = Client()
        response = c.post('/dborrador/preparar', {'anno': '2100', 'cuatrimestre': 'P', 'tipo': 'P'})
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.search('Copiadas:[^0-9]*2[^0-9]*\n', content),
                        'La página deberia decir que se copiaron 2 preferencias')
        self.assertTrue(re.search('Borradas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se borraron 0 preferencias')
        self.assertEqual(Preferencia.objects.all().count(), 2, 'Debería haber dos preferencias copiadas')


class TestPaginaPrincipal(TestCase):

    def test_hay_pagina_principal(self):
        c = Client()
        response = c.get('/dborrador/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.search('<a href=.preparar.>', response.content.decode()),
                        'La página principal no contiene un link a /dborrador/preparar')
        self.assertTrue(re.search('<a href=.distribuir.>', response.content.decode()),
                        'La página principal no contiene un link a /dborrador/distribuir')
        self.assertTrue(re.search(r'<form action="/dborrador/" method="post">', response.content.decode()),
                        'La página principal no contiene un botón de post a /dborrador/')


class TestVerDistribucion(TestCase):

    def setUp(self):
        self.docente1 = Docente.objects.create(nombre='juan', email='mail@nada.org',
                                               telefono='1234', cargos=[CargoDedicacion.TitSim.name])
        self.docente2 = Docente.objects.create(nombre='jose', email='mail@nade.org',
                                               telefono='1235', cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.now = timezone.now()

    def test_figuran_docentes_no_distribuidos(self):
        pref_doc = PreferenciasDocente.objects.create(docente=self.docente1, turno=self.turno1, cargo=Cargos.Tit,
                                                      peso=1, fecha_encuesta=self.now)
        Preferencia.objects.create(preferencia=pref_doc, peso_normalizado=1)

    def test_figuran_docentes_no_distribuidos(self):
        Asignacion.objects.create(intento=1, docente=self.docente1, turno=self.turno1)
        response = self.client.get(reverse('dborrador:distribucion',
                                           args=(2100, Cuatrimestres.P.name, TipoDocentes.P.name, 1)))
        content = response.content.decode()

        self.assertTrue(re.search('Docentes no distribuidos.*jose', content),
                        'No figura un docente no distribuido')
        self.assertTrue(re.search('Turno no cubierto.*epistemologia.*P 2', content),
                        'No figura un turno no cubierto')
