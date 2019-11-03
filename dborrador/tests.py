from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import Permission
from psycopg2.extras import NumericRange

import re
import datetime

from dborrador.models import Preferencia, Asignacion, Intento, IntentoRegistrado
from dborrador.views import hacer_distribucion, _cambiar_docente, NoTurno
from materias.models import (Docente, Materia, Turno, Cuatrimestres, Cargos, Carga, CargoDedicacion,
                             TipoTurno, TipoMateria, AnnoCuatrimestre)
from materias.misc import TipoDocentes, Mapeos
from encuestas.models import PreferenciasDocente, OtrosDatos
from usuarios.models import Usuario

class TestPreparar(TestCase):

    def setUp(self):
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')
        self.anno = 2100

    def _agrega_preferencias(self):
        self.docente = Docente.objects.create(na_nombre='juan', email='mail@nada.org',
                                              telefono='1234',
                                              cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now = timezone.now()
        self.pref1 = PreferenciasDocente.objects.create(docente=self.docente, turno=self.turno1, peso=1, fecha_encuesta=now)
        self.pref2 = PreferenciasDocente.objects.create(docente=self.docente, turno=self.turno2, peso=3, fecha_encuesta=now)
        OtrosDatos.objects.create(docente=self.docente, fecha_encuesta=now, comentario='',
                                  email='', telefono='', anno=self.anno, cuatrimestre=Cuatrimestres.P.name)

    def test_no_falla_si_no_hay_preferencias(self):
        response = self.client.get(f'/dborrador/preparar/{self.anno}/P', follow=True)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f'/dborrador/preparar/{self.anno}/P', follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

    def test_copia_preferencias_redirige_a_distribucion(self):
        self._agrega_preferencias()
        response = self.client.post(f'/dborrador/preparar/{self.anno}/P', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Docentes no distribuidos')

    def test_copio_preferencias_correctas(self):
        self._agrega_preferencias()
        turno_otro_anno = Turno.objects.create(materia=self.materia, anno=2345, cuatrimestre=Cuatrimestres.P.name,
                                               numero=1, tipo=TipoTurno.A.name,
                                               necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        turno_otro_cuatri = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.S.name,
                                                 numero=1, tipo=TipoTurno.A.name,
                                                 necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now = timezone.now()

        pref = Preferencia.objects.create(preferencia=self.pref1, peso_normalizado=1)

        pref_doc_otro_anno = PreferenciasDocente.objects.create(docente=self.docente,
                                                                turno=turno_otro_anno, peso=3,
                                                                fecha_encuesta=now)
        pref_otro_anno = Preferencia.objects.create(preferencia=pref_doc_otro_anno,
                                                    peso_normalizado=1)

        pref_doc_otro_cuatri = PreferenciasDocente.objects.create(docente=self.docente,
                                                                  turno=turno_otro_cuatri, peso=3,
                                                                  fecha_encuesta=now)
        pref_otro_cuatri = Preferencia.objects.create(preferencia=pref_doc_otro_cuatri,
                                                      peso_normalizado=1)

        # primero lo pruebo para un docente sin cargas. No se deben copiar las preferencias
        response = self.client.get(f'/dborrador/preparar/{self.anno}/P', follow=True)
        self.assertEqual(response.status_code, 200)
        copiadas = Preferencia.objects.filter(preferencia__turno__anno=self.anno,
                                              preferencia__turno__cuatrimestre=Cuatrimestres.P.name)
        self.assertEqual(copiadas.count(), 0)

        # ahora le agrego una carga. Se deben copiar
        Carga.objects.create(docente=self.docente, cargo=CargoDedicacion.TitExc.name,
                             anno=self.anno, cuatrimestre=Cuatrimestres.P.name)
        response = self.client.get(f'/dborrador/preparar/{self.anno}/P', follow=True)
        self.assertEqual(response.status_code, 200)
        copiadas = Preferencia.objects.filter(preferencia__turno__anno=self.anno,
                                              preferencia__turno__cuatrimestre=Cuatrimestres.P.name)
        self.assertEqual(copiadas.count(), 2)

        self.assertTrue(pref not in copiadas)

        todas = Preferencia.objects.all()

        self.assertEqual(len(todas), 4)
        self.assertTrue(pref_otro_anno in todas)
        self.assertTrue(pref_otro_cuatri in todas)

    def test_copio_ultimas_preferencias(self):
        self._agrega_preferencias()
        turno3 = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                      numero=3, tipo=TipoTurno.A.name,
                                      necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        now_mas_delta = timezone.now() + datetime.timedelta(seconds=15)
        pref_doc = PreferenciasDocente.objects.create(docente=self.docente, turno=turno3, peso=1, fecha_encuesta=now_mas_delta)

        response = self.client.get(f'/dborrador/preparar/{self.anno}/P', follow=True)
        copiadas = Preferencia.objects.filter(preferencia__turno__anno=self.anno,
                                              preferencia__turno__cuatrimestre=Cuatrimestres.P.name)
        self.assertEqual(copiadas.count(), 1)
        self.assertEqual(copiadas.first().preferencia.turno, turno3)


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


class TestVerDistribucion(TestCase):

    def setUp(self):
        self.anno = 2100
        self.cuatrimestre = Cuatrimestres.P

        self.docente1 = Docente.objects.create(na_nombre='juan', email='mail@nada.org',
                                               telefono='1234', cargos=[CargoDedicacion.TitSim.name])
        self.docente2 = Docente.objects.create(na_nombre='jose', email='mail@nade.org',
                                               telefono='1235', cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.carga1 = Carga.objects.create(docente=self.docente1, cargo=CargoDedicacion.TitSim.name,
                                           anno=self.anno, cuatrimestre=self.cuatrimestre.name, turno=self.turno1)
        self.carga2 = Carga.objects.create(docente=self.docente2, cargo=CargoDedicacion.TitSim.name,
                                           anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')
        self.now = timezone.now()

    def test_figuran_docentes_no_distribuidos(self):
        Asignacion.objects.create(intentos=(Intento(1, 0).valor, Intento(2, 0).valor),
                                  carga=self.carga1, turno=self.turno1,
                                  cargo_que_ocupa=TipoDocentes.P.name)
        IntentoRegistrado.objects.create(intento=Intento(1, 0).valor, anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        response = self.client.get(reverse('dborrador:distribucion',
                                           args=(self.anno, self.cuatrimestre.name, 1, 0)),
                                   follow=True)
        content = response.content.decode()

        self.assertContains(response, 'Docentes no distribuidos')
        self.assertTrue(re.search((f'<a href="/dborrador/cambiar_docente/{self.anno}/{self.cuatrimestre.name}/1/0/{self.carga2.id}">'
                                   f'\s*{self.docente2.nombre}'), content, flags=re.DOTALL),
                        'No figura un docente no distribuido')

    def test_figuran_pedidos_de_docentes_no_distribuidos(self):
        Asignacion.objects.create(intentos=(Intento(1, 0).valor, Intento(2, 0).valor),
                                  carga=self.carga1, turno=self.turno1,
                                  cargo_que_ocupa=TipoDocentes.P.name)
        IntentoRegistrado.objects.create(intento=Intento(1, 0).valor, anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        now = timezone.now()
        pd1 = PreferenciasDocente.objects.create(docente=self.docente2, turno=self.turno1, peso=1, fecha_encuesta=now)
        pd2 = PreferenciasDocente.objects.create(docente=self.docente2, turno=self.turno2, peso=1, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=pd1, peso_normalizado=0.5)
        Preferencia.objects.create(preferencia=pd2, peso_normalizado=0.5)

        response = self.client.get(reverse('dborrador:distribucion',
                                           args=(self.anno, self.cuatrimestre.name, 1, 0)),
                                   follow=True)
        content = response.content.decode()
        self.assertTrue(re.search((f'Encuesta de jose\s*:'
                                   f'(<span[^>]*>|</span>|\s|<span[^>]*>[^>]*</span>|<ul>|<li>)*'
                                   f'{self.materia.nombre}'),
                                  content, flags=re.DOTALL),
                        'No figuran las preferencias de un docente no distribuido')

    def test_figuran_interesados_en_turnos_sin_docentes(self):
        now = timezone.now()
        pd = PreferenciasDocente.objects.create(docente=self.docente2, turno=self.turno1, peso=1, fecha_encuesta=now,
                                                cargo=Cargos.Tit.name)
        Preferencia.objects.create(preferencia=pd, peso_normalizado=1)
        response = self.client.get(reverse('dborrador:distribucion', args=(self.anno, self.cuatrimestre.name, 1, 0)),
                                   follow=True)

        content = response.content.decode()
        self.assertTrue(re.search(('<div class="tooltip">Teórico-Práctica 1'
                                   '(Docentes que lo pidieron:|<span[^>]*>|</span>|\s|<span[^>]*>[^>]*</span>|<ul>|<li>)*'
                                   'Tit: jose'),
                                  content, flags=re.DOTALL),
                        'No figuran los docentes que prefieren un turno sin docentes')

    def test_espiar_distribucion(self):
        now = timezone.now()
        pd = PreferenciasDocente.objects.create(docente=self.docente2, turno=self.turno1, peso=1, fecha_encuesta=now,
                                                cargo=Cargos.Tit.name)
        Preferencia.objects.create(preferencia=pd, peso_normalizado=1)
        Asignacion.objects.create(intentos=(Intento(1, 0).valor, Intento(2, 0).valor),
                                  carga=self.carga1, turno=self.turno1,
                                  cargo_que_ocupa=TipoDocentes.P.name)
        IntentoRegistrado.objects.create(intento=Intento(1, 0).valor, anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        response = self.client.get(reverse('dborrador:espiar_distribucion', args=(self.anno, self.cuatrimestre.name, 1, 0)),
                                   follow=True)
        self.assertContains(response, 'intento 1 : 0')
        self.assertContains(response, self.materia.nombre.upper())
        self.assertTrue(re.search(f'{TipoDocentes.P.value}:\s*{self.carga1.docente.nombre}',
                                  response.content.decode(), flags=re.DOTALL),
                        'La página de espiar distribución no contiene una materia')


class TestDistribuir(TestCase):

    def setUp(self):
        self.ac = AnnoCuatrimestre(2100, Cuatrimestres.P.name)
        self.docente1 = Docente.objects.create(na_nombre='d1', email='d1@nada.org',
                                               telefono='1234', cargos=[CargoDedicacion.TitSim.name])
        self.docente2 = Docente.objects.create(na_nombre='d2', email='d2@nade.org',
                                               telefono='1235', cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno1 = Turno.objects.create(materia=self.materia, anno=self.ac.anno, cuatrimestre=self.ac.cuatrimestre,
                                           numero=1, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno2 = Turno.objects.create(materia=self.materia, anno=self.ac.anno, cuatrimestre=self.ac.cuatrimestre,
                                           numero=2, tipo=TipoTurno.A.name,
                                           necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.carga1 = Carga.objects.create(docente=self.docente1, cargo=CargoDedicacion.TitSim.name,
                                           anno=self.ac.anno, cuatrimestre=self.ac.cuatrimestre)
        self.carga2 = Carga.objects.create(docente=self.docente2, cargo=CargoDedicacion.TitSim.name,
                                           anno=self.ac.anno, cuatrimestre=self.ac.cuatrimestre)

        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')

    def test_distribuye(self):
        now = timezone.now()
        p1 = PreferenciasDocente.objects.create(docente=self.docente1, turno=self.turno2, peso=1, fecha_encuesta=now)
        p2 = PreferenciasDocente.objects.create(docente=self.docente2, turno=self.turno1, peso=3, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=p1, peso_normalizado=1)
        Preferencia.objects.create(preferencia=p2, peso_normalizado=1)

        hacer_distribucion(self.ac, TipoDocentes.P, 1)
        self.assertEqual(Asignacion.objects.count(), 2)
        for asignacion in Asignacion.objects.all():
            self.assertEqual(asignacion.intentos, NumericRange(Intento.de_algoritmo(1).valor, Intento.de_algoritmo(2).valor))

    def test_cambiar_docente(self):
        url = reverse('dborrador:distribucion', args=(self.ac.anno, self.ac.cuatrimestre, 0, 0))
        response = self.client.get(url, follow=True)

        cambiar_url = reverse('dborrador:cambiar_docente', args=(self.ac.anno, self.ac.cuatrimestre, 0, 0, self.carga1.id,))
        self.assertContains(response, cambiar_url)
        # el formulario apunta a la misma página y hay turnos en el select
        response = self.client.get(cambiar_url, follow=True)
        self.assertContains(response, cambiar_url)
        link = f'<option value="{self.turno1.id}"\s*>\s*{self.turno1.str_corto()}[,\s]*</option>'
        self.assertTrue(re.search(link, response.content.decode()))
        # con post se agrega la asignación
        self.client.post(cambiar_url,
                         {'cambiar': True, 'cambio_a': self.turno1.id, 'cargo_que_ocupa': TipoDocentes.A2.name},
                         follow=True)
        asignaciones = Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1)).filter(carga=self.carga1)
        self.assertEqual(asignaciones.count(), 1)
        asignacion = asignaciones.first()
        self.assertEqual(asignacion.turno, self.turno1)
        self.assertEqual(asignacion.cargo_que_ocupa, TipoDocentes.A2.name)

    def test_cambiar_docente_que_borra_cambios(self):
        # (0, 0) nada
        # (0, 1) d1 -> t1
        # (0, 2) d1 -> t2
        # (0, 3) d2 -> t1
        # cambio en (0, 1): d1 -> NoTurno
        # tienen que estar ambos no distribuidos
        _cambiar_docente(self.ac.anno, self.ac.cuatrimestre, Intento(0, 0), self.carga1.id, self.turno1.id, Mapeos.tipo_de_carga(self.carga1))
        self.assertEqual(IntentoRegistrado.maximo_intento(self.ac.anno, self.ac.cuatrimestre), Intento(0, 1))
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1)).count(), 1)

        _cambiar_docente(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1), self.carga1.id, self.turno2.id, Mapeos.tipo_de_carga(self.carga1))
        self.assertEqual(IntentoRegistrado.maximo_intento(self.ac.anno, self.ac.cuatrimestre), Intento(0, 2))
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1)).count(), 1)
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 2)).count(), 1)

        _cambiar_docente(self.ac.anno, self.ac.cuatrimestre, Intento(0, 2), self.carga2.id, self.turno1.id, Mapeos.tipo_de_carga(self.carga2))
        self.assertEqual(IntentoRegistrado.maximo_intento(self.ac.anno, self.ac.cuatrimestre), Intento(0, 3))
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1)).count(), 1)
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 2)).count(), 1)
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 3)).count(), 2)

        _cambiar_docente(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1), self.carga1.id, NoTurno().id, Mapeos.tipo_de_carga(self.carga1))
        self.assertEqual(IntentoRegistrado.maximo_intento(self.ac.anno, self.ac.cuatrimestre), Intento(0, 2))
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 2)).count(), 0)
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 3)).count(), 0)
        self.assertEqual(Asignacion.validas_en(self.ac.anno, self.ac.cuatrimestre, Intento(0, 1)).count(), 1)

    def test_distribuir_no_borra_otros_cuatrimestres(self):
        otro_cuat = Cuatrimestres.S
        turno_otro_cuat = Turno.objects.create(materia=self.materia, anno=self.ac.anno, cuatrimestre=otro_cuat.name,
                                               numero=1, tipo=TipoTurno.A.name,
                                               necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        carga_otro_cuat = Carga.objects.create(docente=self.docente1, cargo=CargoDedicacion.TitSim.name,
                                               anno=self.ac.anno, cuatrimestre=otro_cuat.name)
        now = timezone.now()
        pref_ahora = PreferenciasDocente.objects.create(docente=self.docente1, turno=self.turno2, peso=1, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=pref_ahora, peso_normalizado=1)
        pref_otro_cuat = PreferenciasDocente.objects.create(docente=self.docente1, turno=turno_otro_cuat, peso=1, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=pref_otro_cuat, peso_normalizado=1)

        hacer_distribucion(self.ac, TipoDocentes.P, 1)
        self.assertEqual(Asignacion.objects.count(), 1)

        hacer_distribucion(AnnoCuatrimestre(2100, otro_cuat.name), TipoDocentes.P, 0)
        self.assertEqual(Asignacion.objects.count(), 2)
        turnos_asignados = {a.turno for a in Asignacion.objects.all()}
        self.assertEqual(turnos_asignados, {self.turno2, turno_otro_cuat})

    def test_cambiar_manualmente_no_borra_otros_cuatrimestres(self):
        otro_cuat = Cuatrimestres.S
        turno_otro_cuat = Turno.objects.create(materia=self.materia, anno=self.ac.anno, cuatrimestre=otro_cuat.name,
                                               numero=1, tipo=TipoTurno.A.name,
                                               necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        carga_otro_cuat = Carga.objects.create(docente=self.docente1, cargo=CargoDedicacion.TitSim.name,
                                               anno=self.ac.anno, cuatrimestre=otro_cuat.name)
        now = timezone.now()
        pref_ahora = PreferenciasDocente.objects.create(docente=self.docente1, turno=self.turno2, peso=1, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=pref_ahora, peso_normalizado=1)
        pref_otro_cuat = PreferenciasDocente.objects.create(docente=self.docente1, turno=turno_otro_cuat, peso=1, fecha_encuesta=now)
        Preferencia.objects.create(preferencia=pref_otro_cuat, peso_normalizado=1)

        hacer_distribucion(self.ac, TipoDocentes.P, 1)
        self.assertEqual(Asignacion.objects.count(), 1)

        response = self.client.post(reverse('dborrador:cambiar_docente',
                                            args=(self.ac.anno, otro_cuat.name, 0, 0, carga_otro_cuat.id)),
                                    {'cambiar': True, 'cambio_a': turno_otro_cuat.id, 'cargo_que_ocupa': TipoDocentes.P.name},
                                    follow=True)
        self.assertEqual(Asignacion.objects.count(), 2)
        turnos_asignados = {a.turno for a in Asignacion.objects.all()}
        self.assertEqual(turnos_asignados, {self.turno2, turno_otro_cuat})


class TestModel(TestCase):

    def setUp(self):
        self.docente = Docente.objects.create(na_nombre='d1', email='d1@nada.org',
                                              telefono='1234', cargos=[CargoDedicacion.TitSim.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                          numero=1, tipo=TipoTurno.A.name,
                                          necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.carga = Carga.objects.create(docente=self.docente, cargo=CargoDedicacion.TitSim.name,
                                          anno=2100, cuatrimestre=Cuatrimestres.P.name)

    def test_intentos(self):
        comienzo = Intento(2, 4)
        final = Intento(3, 2)
        asignacion = Asignacion.objects.create(intentos=(comienzo.valor, final.valor),
                                               carga=self.carga, turno=self.turno)

        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(2, 5))), {asignacion})
        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(2, 2395))), {asignacion})
        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(3, 1))), {asignacion})
        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(2, 2))), set())
        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(3, 5))), set())
        self.assertEqual(set(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(3, 2))), set())

    def test_intento_registrado(self):
        IntentoRegistrado.objects.create(intento=Intento(3, 1).valor, anno=2100, cuatrimestre=Cuatrimestres.P.name)
        IntentoRegistrado.objects.create(intento=Intento(3, 7).valor, anno=2100, cuatrimestre=Cuatrimestres.P.name)
        IntentoRegistrado.objects.create(intento=Intento(2, 17).valor, anno=2100, cuatrimestre=Cuatrimestres.P.name)
        maximo = IntentoRegistrado.maximo_intento(anno=2100, cuatrimestre=Cuatrimestres.P.name)
        self.assertEqual(maximo, Intento(3, 7))

    def test_no_se_cofunde_asignaciones_validas(self):
        comienzo = Intento(2, 4)
        final = Intento(3, 2)
        a1 = Asignacion.objects.create(intentos=(comienzo.valor, final.valor),
                                       carga=self.carga, turno=self.turno)
        otro_turno = Turno.objects.create(materia=self.materia, anno=2102, cuatrimestre=Cuatrimestres.S.name,
                                          numero=1, tipo=TipoTurno.T.name,
                                          necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        otra_carga = Carga.objects.create(docente=self.docente, cargo=CargoDedicacion.TitSim.name,
                                          anno=2102, cuatrimestre=Cuatrimestres.S.name)
        a2 = Asignacion.objects.create(intentos=(comienzo.valor, final.valor),
                                       carga=otra_carga, turno=otro_turno)
        self.assertEqual(list(Asignacion.validas_en(2100, Cuatrimestres.P.name, Intento(2,5))), [a1])
        self.assertEqual(list(Asignacion.validas_en(2102, Cuatrimestres.S.name, Intento(2,5))), [a2])
        self.assertEqual(list(Asignacion.validas_en(2100, Cuatrimestres.S.name, Intento(2,5))), [])
