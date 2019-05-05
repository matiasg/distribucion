from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import Permission

import re

from dborrador.models import Preferencia, Asignacion
from materias.models import Docente, Materia, Turno, Cuatrimestres, Cargos, Carga, CargoDedicacion, TipoTurno, TipoMateria
from materias.misc import TipoDocentes
from encuestas.models import PreferenciasDocente
from usuarios.models import Usuario

class TestPreparar(TestCase):

    def setUp(self):
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')

    def _agrega_preferencias(self):
        self.docente = Docente.objects.create(nombre='juan', email='mail@nada.org',
                                              telefono='1234',
                                              cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now = timezone.now()
        self.pref1 = PreferenciasDocente.objects.create(docente=self.docente, turno=self.turno1, peso=1, fecha_encuesta=now)
        self.pref2 = PreferenciasDocente.objects.create(docente=self.docente, turno=self.turno2, peso=3, fecha_encuesta=now)

    def test_no_falla_si_no_hay_preferencias(self):
        response = self.client.get('/dborrador/preparar/2100/P/P')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/dborrador/preparar/2100/P/P')
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
        self._agrega_preferencias()
        response = self.client.post('/dborrador/preparar/2100/P/P')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.search('Copiadas:[^0-9]*2[^0-9]*\n', content),
                        'La página deberia decir que se copiaron 2 preferencias')
        self.assertTrue(re.search('Borradas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se borraron 0 preferencias')
        self.assertEqual(Preferencia.objects.all().count(), 2, 'Debería haber dos preferencias copiadas')

    def test_borro_preferencias_correctas(self):
        self._agrega_preferencias()
        turno_otro_anno = Turno.objects.create(materia=self.materia, anno=2345, cuatrimestre=Cuatrimestres.P.name,
                                               numero=1, tipo=TipoTurno.A.name,
                                               necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        turno_otro_cuatri = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.S.name,
                                                 numero=1, tipo=TipoTurno.A.name,
                                                 necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now = timezone.now()

        pref = Preferencia.objects.create(preferencia=self.pref1, peso_normalizado=1)

        pref_doc_otro_anno = PreferenciasDocente.objects.create(docente=self.docente, turno=turno_otro_anno, peso=3, fecha_encuesta=now)
        pref_otro_anno = Preferencia.objects.create(preferencia=pref_doc_otro_anno, peso_normalizado=1)

        pref_doc_otro_cuatri = PreferenciasDocente.objects.create(docente=self.docente, turno=turno_otro_cuatri, peso=3, fecha_encuesta=now)
        pref_otro_cuatri = Preferencia.objects.create(preferencia=pref_doc_otro_cuatri, peso_normalizado=1)

        response = self.client.get('/dborrador/preparar/2100/P/P')
        self.assertEqual(response.status_code, 200)

        copiadas = Preferencia.objects.filter(preferencia__turno__anno=2100, preferencia__turno__cuatrimestre=Cuatrimestres.P.name)
        self.assertEqual(copiadas.count(), 2)
        self.assertTrue(pref not in copiadas)

        todas = Preferencia.objects.all()

        self.assertEqual(len(todas), 4)
        self.assertTrue(pref_otro_anno in todas)
        self.assertTrue(pref_otro_cuatri in todas)



class TestPaginaPrincipal(TestCase):

    def setUp(self):
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')

    def test_hay_pagina_principal_sin_datos(self):
        response = self.client.get('/dborrador/')
        self.assertContains(response, '<select name="anno">')
        self.assertContains(response, '<select name="cuatrimestre">')
        self.assertContains(response, '<select name="tipo">')

    def test_hay_pagina_principal_con_datos(self):
        response = self.client.post('/dborrador/', {'anno': 2100, 'cuatrimestre': 'P', 'tipo': 'P', 'intento': 0},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.search('<a href="/dborrador/preparar/2100/P/P">', response.content.decode()),
                        'La página redirigida no contiene un link a /dborrador/preparar')
        self.assertTrue(re.search('<a href="/dborrador/distribuir/2100/P/P/0">', response.content.decode()),
                        'La página redirigida no contiene un link a /dborrador/distribuir')
        self.assertTrue(re.search(r'<a href="/dborrador/fijar/2100/P/P/0">', response.content.decode()),
                        'La página redirigida no contiene un botón de post a /dborrador/')


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
        self.carga1 = Carga.objects.create(docente=self.docente1, cargo=CargoDedicacion.TitSim.name,
                                           anno=2100, cuatrimestre=Cuatrimestres.P.name, turno=self.turno1)
        self.carga2 = Carga.objects.create(docente=self.docente2, cargo=CargoDedicacion.TitSim.name,
                                           anno=2100, cuatrimestre=Cuatrimestres.P.name)
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')
        self.now = timezone.now()

    def test_figuran_docentes_no_distribuidos(self):

        Asignacion.objects.create(intento=1, carga=self.carga1, turno=self.turno1)
        response = self.client.get(reverse('dborrador:fijar',
                                           args=(2100, Cuatrimestres.P.name, TipoDocentes.P.name, 1)))
        content = response.content.decode()

        self.assertTrue(re.search('Cargas docentes sin distribución.*jose', content, flags=re.DOTALL),
                        'No figura un docente no distribuido')
        self.assertTrue(re.search('Turnos con necesidades insatisfechas.*epistemologia.*Teórico-Práctica 2',
                                  content, flags=re.DOTALL),
                        'No figura un turno no cubierto')
