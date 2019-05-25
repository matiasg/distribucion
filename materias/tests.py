from django.test import TestCase
from unittest.mock import patch

import datetime
from django.utils import timezone

from materias.models import (Cargos, Dedicaciones, CargoDedicacion, Docente,
                             Materia, Turno, TipoMateria, TipoTurno, Dias, Cuatrimestres,
                             Horario)
from usuarios.models import Usuario
from django.contrib.auth.models import Permission

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

    def test_turno_0(self):
        turno0 = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=0, tipo=TipoTurno.T.name,
                                      necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.assertTrue('Teórica' in str(turno0))
        self.assertTrue('Teórica 0' not in str(turno0))
        self.assertTrue('Teórica 1' in str(self.turno))


class TestPaginas(TestCase):

    def setUp(self):
        self.materia1 = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        self.materia2 = Materia.objects.create(nombre='lacan 2', obligatoriedad=TipoMateria.B.name)
        self.materia3 = Materia.objects.create(nombre='lacan 3', obligatoriedad=TipoMateria.B.name)

        dict_nec = {'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        self.turno11 = Turno.objects.create(materia=self.materia1, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=1, tipo=TipoTurno.T.name, **dict_nec)
        self.turno12 = Turno.objects.create(materia=self.materia1, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=2, tipo=TipoTurno.T.name, **dict_nec)
        self.turno13 = Turno.objects.create(materia=self.materia1, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=3, tipo=TipoTurno.T.name, **dict_nec)
        self.turno14 = Turno.objects.create(materia=self.materia1, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=4, tipo=TipoTurno.T.name, **dict_nec)
        self.turno21 = Turno.objects.create(materia=self.materia2, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=1, tipo=TipoTurno.T.name, **dict_nec)
        self.turno22 = Turno.objects.create(materia=self.materia2, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                            numero=2, tipo=TipoTurno.T.name, **dict_nec)

        siete, ocho, nueve, diez = datetime.time(7), datetime.time(8), datetime.time(9), datetime.time(10)
        self.horario111 = Horario.objects.create(turno=self.turno11, dia=Dias.Lu.name, comienzo=ocho, final=nueve)
        self.horario112 = Horario.objects.create(turno=self.turno11, dia=Dias.Ju.name, comienzo=siete, final=ocho)
        self.horario121 = Horario.objects.create(turno=self.turno12, dia=Dias.Lu.name, comienzo=siete, final=nueve)
        self.horario122 = Horario.objects.create(turno=self.turno12, dia=Dias.Ju.name, comienzo=ocho, final=ocho)

        self.horario131 = Horario.objects.create(turno=self.turno13, dia=Dias.Ju.name, comienzo=ocho, final=ocho)
        self.horario141 = Horario.objects.create(turno=self.turno14, dia=Dias.Mi.name, comienzo=siete, final=ocho)

        self.horario211 = Horario.objects.create(turno=self.turno21, dia=Dias.Vi.name, comienzo=diez, final=diez,
                                                 aula='3', pabellon=1)

    def test_pagina_principal_con_y_sin_turnos(self):
        response = self.client.get('/materias/21001')
        self.assertContains(response, '<div class="seccion">Obligatorias</div>' )
        self.assertContains(response, '<table' )
        self.assertContains(response, self.materia1.nombre.upper())
        self.assertContains(response, self.materia2.nombre.upper())
        self.assertNotContains(response, self.materia3.nombre.upper())

        response = self.client.get('/materias/21002')
        self.assertNotContains(response, '<table' )

        response = self.client.get('/materias/21011')
        self.assertNotContains(response, '<table' )

    def test_turnos_en_orden(self):
        response = self.client.get('/materias/21001')
        ubicacion_t11 = response.content.decode().index('Lu y Ju: 8 a 9 y 7 a 8')
        ubicacion_t12 = response.content.decode().index('Lu y Ju: 7 a 9 y 8 a 8')
        ubicacion_t13 = response.content.decode().index('Ju: 8 a 8')
        ubicacion_t14 = response.content.decode().index('Mi: 7 a 8')
        self.assertLess(ubicacion_t12, ubicacion_t11)
        self.assertLess(ubicacion_t11, ubicacion_t14)
        self.assertLess(ubicacion_t14, ubicacion_t13)

    def test_tabla_dice_aula(self):
        response = self.client.get('/materias/21001')
        self.assertContains(response, '<td class="aula">Aula: 3 (P.1)</td>')

    def test_turno_no_tiene_0(self):
        turno0 = Turno.objects.create(materia=self.materia1, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                      numero=0, tipo=TipoTurno.T.name,
                                      necesidad_prof=0, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        response = self.client.get('/materias/21001')
        self.assertNotContains(response, 'Teórica 0')
        self.assertContains(response, 'Teórica 1')

    def test_ac_mal_formado(self):
        for ac in ['abc', '1234', '1234a', '0x231', '10005', '1000Y']:
            response = self.client.get(f'/materias/{ac}')
            self.assertEqual(response.status_code, 404)

    def test_pagina_principal_sin_ac(self):
        response = self.client.get('/materias/')
        self.assertNotContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(2100, 1, 1)):
            response = self.client.get('/materias/')
            self.assertNotContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(2100, 5, 1)):
            response = self.client.get('/materias/')
            self.assertContains(response, 'Teórica')
        with patch.object(timezone, 'now', return_value=datetime.datetime(2100, 10, 1)):
            response = self.client.get('/materias/')
            self.assertNotContains(response, 'Teórica')



    def test_administrar(self):
        autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(content_type__app_label='materias', codename='add_turno')
        autorizado.user_permissions.add(permiso)
        self.client.login(username='autorizado', password='1234')

        self.turno11.dificil_de_cubrir = True
        self.turno11.save()

        url = '/materias/administrar_turnos/2100/P'
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
