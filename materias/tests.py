from django.test import TestCase
from unittest.mock import patch

import re
import datetime
from locale import strxfrm
from django.utils import timezone

from materias.models import (Cargos, Carga, Dedicaciones, CargoDedicacion, Docente,
                             Materia, Turno, TipoMateria, TipoTurno, Dias, Cuatrimestres,
                             Horario, Pabellon)
from encuestas.models import PreferenciasDocente, OtrosDatos
from usuarios.models import Usuario
from django.contrib.auth.models import Permission
from django.urls import reverse

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
        n = Docente.objects.create(na_nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])

        nemos = Docente.objects.filter(na_nombre='nemo')
        self.assertEquals(len(nemos), 1)
        self.assertEquals(nemos.first(), n)

        titulares = Docente.objects.filter(cargos__overlap=CargoDedicacion.con_cargo(Cargos.Tit))
        self.assertEquals(len(titulares), 1)
        self.assertEquals(titulares.first(), n)

    def test_nada(self):
        n = Docente.objects.create(na_nombre='nemo',
                                   telefono='00 0000',
                                   email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        m = Docente.objects.create(na_nombre='mario', telefono='', email='',
                                   cargos=[CargoDedicacion.Ay2Sim.name, CargoDedicacion.Ay2Sim.name])
        o = Docente.objects.create(na_nombre='ovidio',
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

    def test_turno_0(self):
        turno0 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=0, tipo=TipoTurno.T.name,
                                      necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.assertTrue('Teórica' in str(turno0))
        self.assertTrue('Teórica 0' not in str(turno0))
        self.assertTrue('Teórica 1' in str(self.turno))

    def test_pabellones_en_turnos(self):
        turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                     numero=1, tipo=TipoTurno.T.name,
                                     necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        siete, nueve = datetime.time(7), datetime.time(9)
        horario1 = Horario.objects.create(turno=turno, dia=Dias.Lu.name, comienzo=siete, final=nueve,
                                          aula='5', pabellon=Pabellon.Uno.value[0])
        horario2 = Horario.objects.create(turno=turno, dia=Dias.Ju.name, comienzo=siete, final=nueve,
                                          aula='6', pabellon=Pabellon.Cero_infinito.value[0])

        self.assertEquals(turno.horarios_info().aula, f'5 (P.{Pabellon.Uno.value[1]}) y 6 (P.{Pabellon.Cero_infinito.value[1]})')

    def test_orden_docente(self):
        c = Docente.objects.create(na_nombre='Ca', na_apellido='C',
                                   telefono='00 0000', email='ca@nada.org', cargos=[CargoDedicacion.TitExc.name])
        b = Docente.objects.create(na_nombre='Ba', na_apellido='B',
                                   telefono='00 0000', email='ba@nada.org', cargos=[CargoDedicacion.TitExc.name])
        a = Docente.objects.create(na_nombre='Áb', na_apellido='A',
                                   telefono='00 0000', email='ab@nada.org', cargos=[CargoDedicacion.TitExc.name])
        docentes = Docente.objects.all()
        self.assertEquals(list(docentes), [a, b, c])

        docentes = sorted(Docente.objects.all(), key=lambda d: strxfrm(d.apellido_nombre))
        self.assertEquals(list(docentes), [a, b, c])



class TestPaginas(TestCase):

    def setUp(self):
        self.anno = 2100
        self.cuatrimestre = Cuatrimestres.P
        self.materia1 = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        self.materia2 = Materia.objects.create(nombre='lacan 2', obligatoriedad=TipoMateria.B.name)
        self.materia3 = Materia.objects.create(nombre='lacan 3', obligatoriedad=TipoMateria.B.name)

        dict_nec = {'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        self.turno11 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=1, tipo=TipoTurno.T.name, **dict_nec)
        self.turno12 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=2, tipo=TipoTurno.T.name, **dict_nec)
        self.turno13 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=3, tipo=TipoTurno.T.name, **dict_nec)
        self.turno14 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=4, tipo=TipoTurno.T.name, **dict_nec)
        self.turno21 = Turno.objects.create(materia=self.materia2, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=1, tipo=TipoTurno.T.name, **dict_nec)
        self.turno22 = Turno.objects.create(materia=self.materia2, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=2, tipo=TipoTurno.T.name, **dict_nec)

        siete, ocho, nueve, diez = datetime.time(7), datetime.time(8), datetime.time(9), datetime.time(10)
        aula_pab = {'aula': 'no', 'pabellon': '0'}
        self.horario111 = Horario.objects.create(turno=self.turno11, dia=Dias.Lu.name, comienzo=ocho, final=nueve, **aula_pab)
        self.horario112 = Horario.objects.create(turno=self.turno11, dia=Dias.Ju.name, comienzo=siete, final=ocho, **aula_pab)
        self.horario121 = Horario.objects.create(turno=self.turno12, dia=Dias.Lu.name, comienzo=siete, final=nueve, **aula_pab)
        self.horario122 = Horario.objects.create(turno=self.turno12, dia=Dias.Ju.name, comienzo=ocho, final=ocho, **aula_pab)

        self.horario131 = Horario.objects.create(turno=self.turno13, dia=Dias.Ju.name, comienzo=ocho, final=ocho, **aula_pab)
        self.horario141 = Horario.objects.create(turno=self.turno14, dia=Dias.Mi.name, comienzo=siete, final=ocho, **aula_pab)

        self.horario211 = Horario.objects.create(turno=self.turno21, dia=Dias.Vi.name, comienzo=diez, final=diez,
                                                 aula='3', pabellon=1)
        Usuario.objects.create_user(username='desautorizado', password='123')
        autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='materias', codename='add_turno'))
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='dborrador', codename='add_asignacion'))
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='materias', codename='view_docente'))

    def test_pagina_principal_con_y_sin_turnos(self):
        response = self.client.get(f'/materias/{self.anno}{self.cuatrimestre.value}')
        self.assertContains(response, '<div class="seccion">Obligatorias</div>' )
        self.assertContains(response, '<table' )
        self.assertContains(response, self.materia1.nombre.upper())
        self.assertContains(response, self.materia2.nombre.upper())
        self.assertNotContains(response, self.materia3.nombre.upper())

        response = self.client.get(f'/materias/{self.anno}{Cuatrimestres.S.value}')
        self.assertNotContains(response, '<table' )

        response = self.client.get('/materias/21011')
        self.assertNotContains(response, '<table' )

    def test_turnos_en_orden(self):
        response = self.client.get(f'/materias/{self.anno}{self.cuatrimestre.value}')
        ubicacion_t11 = response.content.decode().index('Lu y Ju: 8 a 9 y 7 a 8')
        ubicacion_t12 = response.content.decode().index('Lu y Ju: 7 a 9 y 8 a 8')
        ubicacion_t13 = response.content.decode().index('Ju: 8 a 8')
        ubicacion_t14 = response.content.decode().index('Mi: 7 a 8')
        self.assertLess(ubicacion_t12, ubicacion_t11)
        self.assertLess(ubicacion_t11, ubicacion_t14)
        self.assertLess(ubicacion_t14, ubicacion_t13)

    def test_tabla_dice_aula(self):
        response = self.client.get(f'/materias/{self.anno}{self.cuatrimestre.value}')
        self.assertContains(response, '<td class="aula">Aula: 3 (P.1)</td>')

    def test_turno_no_tiene_0(self):
        turno0 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                      numero=0, tipo=TipoTurno.T.name,
                                      necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        response = self.client.get(f'/materias/{self.anno}{self.cuatrimestre.value}')
        self.assertNotContains(response, 'Teórica 0')
        self.assertContains(response, 'Teórica 1')

    def test_ac_mal_formado(self):
        for ac in ['abc', '1234', '1234a', '0x231', '10005', '1000Y']:
            response = self.client.get(f'/materias/{ac}')
            self.assertEqual(response.status_code, 404)

    def test_pagina_principal_sin_ac(self):
        response = self.client.get('/materias/')
        self.assertNotContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(self.anno, 1, 1)):
            response = self.client.get('/materias/')
            self.assertNotContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(self.anno, 5, 1)):
            response = self.client.get('/materias/')
            self.assertContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(self.anno, 10, 1)):
            response = self.client.get('/materias/')
            self.assertNotContains(response, 'Teórica')

    def test_administrar_permisos(self):
        response = self.client.get('/materias/administrar', follow=True)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/materias/administrar', 302))

        self.client.login(username='desautorizado', password='123')
        response = self.client.get('/materias/administrar', follow=True)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/materias/administrar', 302))

        self.client.login(username='autorizado', password='1234')
        response = self.client.get('/materias/administrar', follow=True)
        self.assertContains(response, 'Administrar turnos')
        self.assertEqual(len(response.redirect_chain), 0)

    def test_administrar_dirige_bien(self):
        self.client.login(username='autorizado', password='1234')
        botones_urls = {
            'turnos_docentes': 'administrar_docentes',
            'turnos_alumnos': 'administrar_alumnos',
            'cargas_docentes': 'administrar_cargas_docentes',
        }
        for boton, url in botones_urls.items():
            response = self.client.post('/materias/administrar',
                                        {boton: True, 'anno': self.anno, 'cuatrimestre': self.cuatrimestre.name},
                                        follow=True)
            self.assertEqual(response.redirect_chain[-1],
                             (f'/materias/{url}/{self.anno}/{self.cuatrimestre.name}', 302),
                             f'No está redirigiendo bien a {url}')

    def test_administrar_docentes(self):
        self.client.login(username='autorizado', password='1234')

        self.turno11.dificil_de_cubrir = True
        self.turno11.save()

        url = f'/materias/administrar_docentes/{self.anno}/{self.cuatrimestre.name}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, f'name="dificil_{self.turno11.id}" checked')

        key_to_field = {'alumnos': 'alumnos',
                        'necesidadprof': 'necesidad_prof',
                        'necesidadjtp': 'necesidad_jtp',
                        'necesidaday1': 'necesidad_ay1',
                        'necesidaday2': 'necesidad_ay2'}

        post = dict()
        for k_field, t_attr in key_to_field.items():
            for turno in Turno.objects.all():
                post[f'{k_field}_{turno.id}'] = getattr(turno, t_attr)

        post[f'dificil_{self.turno12.id}'] = 'on'
        post['cambiar'] = True
        self.client.post(url, post)

        nturno11 = Turno.objects.get(pk=self.turno11.id)
        nturno12 = Turno.objects.get(pk=self.turno12.id)
        self.assertFalse(nturno11.dificil_de_cubrir)
        self.assertTrue(nturno12.dificil_de_cubrir)

    def test_administrar_alumnos(self):
        self.client.login(username='autorizado', password='1234')

        self.turno11.alumnos = 7
        self.turno11.save()

        self.horario111.aula = 'EP1'
        self.horario111.pabellon = '2'
        self.horario111.save()

        url = f'/materias/administrar_alumnos/{self.anno}/{self.cuatrimestre.name}'
        response = self.client.get(url, follow=True)
        self.assertTrue(re.search(f'name="alumnos_{self.turno11.id}".*value=7',
                                  response.content.decode()))
        self.assertTrue(re.search(f'name="aula_{self.horario111.id}".*value="EP1"',
                                  response.content.decode()))
        self.assertTrue(re.search((f'name="pabellon_{self.horario111.id}">'
                                   f'(\s*(<option value="(1|I|0)"\s*>|(1|Ind|0+∞)|</option>)\s*)+'
                                   f'<option value="2" selected>'),
                                  response.content.decode(), flags=re.DOTALL))

        model_to_ktf = {Turno: {'alumnos': ('alumnos', int)},
                        Horario: {'aula': ('aula', str),
                                  'pabellon': ('pabellon', int)}}

        post = dict()
        for model, key_to_field in model_to_ktf.items():
            for k_field, (t_attr, _) in key_to_field.items():
                for o in model.objects.all():
                    post[f'{k_field}_{o.id}'] = getattr(o, t_attr)

        post[f'alumnos_{self.turno12.id}'] = '13'
        post[f'aula_{self.horario112.id}'] = 'xyz'
        post[f'pabellon_{self.horario112.id}'] = '0'
        post['cambiar'] = True
        self.client.post(url, post)

        nturno12 = Turno.objects.get(pk=self.turno12.id)
        nhorario112 = Horario.objects.get(pk=self.horario112.id)
        self.assertEqual(nturno12.alumnos, 13)
        self.assertEqual(nhorario112.aula, 'xyz')
        self.assertEqual(nhorario112.pabellon, '0')

    def test_administrar_cargas_docentes(self):
        self.client.login(username='autorizado', password='1234')
        n = Docente.objects.create(na_nombre='nemo', na_apellido='X',
                                   telefono='00 0000', email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name])
        m = Docente.objects.create(na_nombre='mario', na_apellido='Y',
                                   telefono='00 0000', email='mario@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        now = timezone.now()
        Carga.objects.create(docente=n, cargo=CargoDedicacion.TitExc.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        Carga.objects.create(docente=m, cargo=CargoDedicacion.TitExc.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        Carga.objects.create(docente=m, cargo=CargoDedicacion.Ay1Smx.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        PreferenciasDocente.objects.create(docente=n, turno=self.turno11,
                                           cargo=Cargos.Tit.name, peso=2, fecha_encuesta=now)
        OtrosDatos.objects.create(docente=n, fecha_encuesta=now,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name, cargas=2,
                                  comentario='_esto deberia aparecer_')

        response = self.client.get(f'/materias/administrar_cargas_docentes/{self.anno}/{self.cuatrimestre.name}', follow=True)
        self.assertContains(response, '>nemo X<')
        self.assertContains(response, '_esto deberia aparecer_')
        self.assertContains(response, '>mario Y<')

    def test_administrar_cargas_de_un_docente(self):
        self.client.login(username='autorizado', password='1234')

        n = Docente.objects.create(na_nombre='nemo',
                                   telefono='00 0000', email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        m = Docente.objects.create(na_nombre='mario',
                                   telefono='00 0000', email='mario@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])
        c1 = Carga.objects.create(docente=n, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        c2 = Carga.objects.create(docente=n, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        OtrosDatos.objects.create(docente=n, fecha_encuesta=timezone.now(),
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                  cargas=2)
        cm = Carga.objects.create(docente=m, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)

        url = f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{n.id}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'cargo_TitExc')
        self.assertContains(response, 'cargo_Ay1Smx')

        response = self.client.post(f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{n.id}',
                                    {'salvar': True, 'anno': self.anno, 'cuatrimestre': self.cuatrimestre.name,
                                     'cargo_TitExc': 1, 'cargo_Ay1Smx': 1},
                                    follow=True)
        self.assertEquals(Carga.objects.filter(docente=n, cargo='TitExc').count(), 1)
        self.assertEquals(Carga.objects.filter(docente=n, cargo='Ay1Smx').count(), 1)

        url = f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{m.id}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'no completó la encuesta')
        self.assertContains(response, 'cargo_TitExc')

    def test_adminitrar_materia_requiere_login(self):
        url = reverse('materias:administrar_materia', args=(self.materia1.id, self.anno, self.cuatrimestre.name))

        response = self.client.get(url, follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertEqual(response.redirect_chain[-1][1], 301)
        self.assertTrue(response.redirect_chain[-1][0].startswith('/admin/login'))

        self.client.login(username='autorizado', password='1234')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.redirect_chain, [])
        self.assertEqual(response.status_code, 200)

    def test_administrar_materia(self):
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:administrar_materia', args=(self.materia1.id, self.anno, self.cuatrimestre.name))
        response = self.client.get(url, follow=True)

        for turno in (self.turno11, self.turno12, self.turno13, self.turno14):
            self.assertContains(response, f'{TipoTurno[turno.tipo].value} {turno.numero}')
            href_url = reverse('materias:cambiar_turno', args=(turno.id,))
            self.assertContains(response, href_url)

        for tipo in TipoTurno:
            self.assertContains(response, f'name="agregar_turno_{tipo.name}"')

    def test_agregar_turno(self):
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:administrar_materia', args=(self.materia1.id, self.anno, self.cuatrimestre.name))
        response = self.client.post(url, {'agregar_turno_T': True}, follow=True)
        # se generó un turno nuevo
        self.assertContains(response, f'{TipoTurno.T.value} 5')
        nuevo_turno = Turno.objects.get(materia=self.materia1, tipo=TipoTurno.T.name, numero=5)
        # no tiene horarios
        self.assertEqual(nuevo_turno.horario_set.count(), 0)

    def test_cambiar_turno(self):
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:cambiar_turno', args=(self.turno11.id,))
        response = self.client.post(url, follow=True)
        # hay botones para borrar y agregar horarios
        for horario in self.turno11.horario_set.all():
            boton = f'input type="button" id="borrar_horario" data-horario="{horario.id}" value="Borrar horario">'
            self.assertContains(response, boton)
        self.assertContains(response, '<button>Agregar horario</button>')
        # se puede agregar un horario
        self.assertEqual(self.turno11.horario_set.count(), 2)
        self.client.post(url, {'dia2': Dias.Vi.name, 'comienzo2': '01:23:45', 'final2': '12:34:56'},
                         follow=True)
        self.assertEqual(self.turno11.horario_set.count(), 3)
        nuevo_horario = Horario.objects.get(turno=self.turno11, comienzo=datetime.time(1, 23, 45))
        self.assertEqual(nuevo_horario.dia, Dias.Vi.name)
        self.assertEqual(nuevo_horario.final, datetime.time(12, 34, 56))

    def test_borrar_horario(self):
        self.client.login(username='autorizado', password='1234')
        self.assertTrue(self.horario111 in self.turno11.horario_set.all())
        # borro el horario
        url = reverse('materias:borrar_horario', args=(self.horario111.id,))
        response = self.client.get(url, follow=True)
        # veo que no existe más
        self.assertFalse(self.horario111 in self.turno11.horario_set.all())
        # veo que redirige bien
        self.assertEqual(response.redirect_chain[0][0], reverse('materias:cambiar_turno', args=(self.turno11.id,)))

    def test_borrar_turno(self):
        self.client.login(username='autorizado', password='1234')
        self.assertTrue(self.turno11 in self.materia1.turno_set.all())
        # borro el turno
        url = reverse('materias:borrar_turno', args=(self.turno11.id,))
        response = self.client.get(url, follow=True)
        # no existe más
        self.assertFalse(self.turno11 in self.materia1.turno_set.all())
        # redirige bien
        self.assertEqual(response.redirect_chain[0][0], reverse('materias:administrar_materia',
                                                                args=(self.materia1.id, self.anno, self.cuatrimestre.name)))
