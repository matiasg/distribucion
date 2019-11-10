from django.test import TestCase
from unittest.mock import patch

import re
import datetime
from locale import strxfrm
from django.utils import timezone

from materias.models import (Cargos, Carga, Dedicaciones, CargoDedicacion, Docente, TipoDocentes,
                             Materia, AliasDeMateria, Turno, TipoMateria, TipoTurno, Dias,
                             Cuatrimestres, Horario, Pabellon)
from materias.misc import Mapeos
from encuestas.models import PreferenciasDocente, OtrosDatos, CargasPedidas, GrupoCuatrimestral
from dborrador.models import Asignacion
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
                                   cargos=[CargoDedicacion.Ay2Par.name, CargoDedicacion.Ay2Par.name])
        o = Docente.objects.create(na_nombre='ovidio',
                                   cargos=[CargoDedicacion.Ay2Par.name])
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

    def test_horario_sin_aula_o_pabellon(self):
        siete, nueve = datetime.time(7), datetime.time(9)
        horario1 = Horario.objects.create(turno=self.turno, dia=Dias.Lu.name, comienzo=siete, final=nueve,
                                          aula='', pabellon=Pabellon.Uno.value[0])
        horario2 = Horario.objects.create(turno=self.turno, dia=Dias.Lu.name, comienzo=siete, final=nueve,
                                          aula='1', pabellon='')
        horario3 = Horario.objects.create(turno=self.turno, dia=Dias.Lu.name, comienzo=siete, final=nueve,
                                          aula='2', pabellon=Pabellon.Uno.value[0])
        horario4 = Horario.objects.create(turno=self.turno, dia=Dias.Lu.name, comienzo=siete, final=nueve,
                                          aula='3', pabellon=Pabellon.Cero_infinito.value[0])
        self.assertEquals(horario1.aula_y_pabellon(), '')
        self.assertEquals(horario2.aula_y_pabellon(), '')
        self.assertEquals(horario3.aula_y_pabellon(), f'2 (P.{Pabellon.Uno.value[1]})')
        self.assertEquals(horario4.aula_y_pabellon(), f'3 (P.{Pabellon.Cero_infinito.value[1]})')

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

    def horarios_sin_dos_puntos_si_no_hay(self):
        self.assertEquals(self.turno.horarios_info().diayhora, '')
        Horario.objects.create(turno=self.turno, dia=Dias.Lu.name, comienzo=datetime.time(7), final=datetime.time(9),
                               aula='', pabellon='0')
        self.assertEquals(self.turno.horarios_info().diayhora, 'Lu: 7 a 9')

    def test_ordenar_cargas_por_tipo_docente(self):
        a = 2100
        c = Cuatrimestres.P.name
        n = Docente.objects.create(na_nombre='nemo', telefono='00 0000', email='nemo@nautilus.org', cargos=[])
        m = Docente.objects.create(na_nombre='momo', telefono='00 0000', email='momo@nautilus.org', cargos=[])
        carga_pn = Carga.objects.create(docente=n, anno=a, cuatrimestre=c, cargo=CargoDedicacion.TitExc.name)
        carga_jn = Carga.objects.create(docente=n, anno=a, cuatrimestre=c, cargo=CargoDedicacion.JTPPar.name)
        carga_an = Carga.objects.create(docente=n, anno=a, cuatrimestre=c, cargo=CargoDedicacion.Ay1Par.name)
        carga_bn = Carga.objects.create(docente=n, anno=a, cuatrimestre=c, cargo=CargoDedicacion.Ay2Par.name)
        carga_pm = Carga.objects.create(docente=m, anno=a, cuatrimestre=c, cargo=CargoDedicacion.TitExc.name)
        carga_jm = Carga.objects.create(docente=m, anno=a, cuatrimestre=c, cargo=CargoDedicacion.JTPPar.name)
        carga_am = Carga.objects.create(docente=m, anno=a, cuatrimestre=c, cargo=CargoDedicacion.Ay1Par.name)
        carga_bm = Carga.objects.create(docente=m, anno=a, cuatrimestre=c, cargo=CargoDedicacion.Ay2Par.name)

        ordenadas = sorted(Carga.objects.all(), key=Mapeos.key_orden_por_tipo_docente)
        self.assertEquals(ordenadas, [carga_pm, carga_pn,
                                      carga_jm, carga_jn,
                                      carga_am, carga_an,
                                      carga_bm, carga_bn])


class TestPaginas(TestCase):

    def setUp(self):
        self.anno = 2100
        self.cuatrimestre = Cuatrimestres.P
        self.materia1 = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        self.materia2 = Materia.objects.create(nombre='lacan 2', obligatoriedad=TipoMateria.B.name)
        self.materia3 = Materia.objects.create(nombre='lacan 3', obligatoriedad=TipoMateria.B.name)

        self.dict_nec = {'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        self.turno11 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=1, tipo=TipoTurno.T.name, **self.dict_nec)
        self.turno12 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=2, tipo=TipoTurno.T.name, **self.dict_nec)
        self.turno13 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=3, tipo=TipoTurno.T.name, **self.dict_nec)
        self.turno14 = Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=4, tipo=TipoTurno.T.name, **self.dict_nec)
        self.turno21 = Turno.objects.create(materia=self.materia2, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=1, tipo=TipoTurno.T.name, **self.dict_nec)
        self.turno22 = Turno.objects.create(materia=self.materia2, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                            numero=2, tipo=TipoTurno.T.name, **self.dict_nec)

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

    def _agrega_docentes(self):
        self.n = Docente.objects.create(na_nombre='nemo', na_apellido='X', telefono='00 0000', email='nemo@nautilus.org',
                                        cargos=[CargoDedicacion.TitExc.name])
        self.m = Docente.objects.create(na_nombre='mario', na_apellido='Y', telefono='00 0000', email='mario@nautilus.org',
                                        cargos=[CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name])

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

    def test_pagina_principal_ordena_cargas_por_tipo_docente(self):
        cargos = (CargoDedicacion.AdjPar, CargoDedicacion.JTPPar, CargoDedicacion.Ay1Par, CargoDedicacion.Ay2Par)
        prenombres = ('y', 'x', 'z')
        for prenombre in prenombres:
            for cargo in cargos:
                docente = Docente.objects.create(na_nombre=f'{prenombre}_{cargo.name}', telefono='', email='', cargos=[])
                carga = Carga.objects.create(docente=docente, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                             turno=self.turno11, cargo=cargo.name)

        response = self.client.get(reverse('materias:por_anno_y_cuatrimestre', args=(f'{self.anno}{self.cuatrimestre.value}',)),
                                   follow=True)
        todos = r'\s*-\s*'.join(f'{prenombre}_{cargo.name}' for cargo in cargos for prenombre in sorted(prenombres))
        self.assertRegex(response.content.decode(), todos)

    def test_administrar_permisos(self):
        response = self.client.get('/materias/administrar', follow=True)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/materias/administrar', 302))

        self.client.login(username='desautorizado', password='123')
        response = self.client.get('/materias/administrar', follow=True)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/materias/administrar', 302))

        self.client.login(username='autorizado', password='1234')
        response = self.client.get('/materias/administrar', follow=True)
        self.assertContains(response, 'administrar materias: alumnos y turnos')
        self.assertContains(response, 'administrar necesidades docentes')
        self.assertContains(response, 'retocar materias')
        self.assertContains(response, 'administrar encuestas')
        self.assertContains(response, 'distribuir docentes')
        self.assertEqual(len(response.redirect_chain), 0)

    def test_administrar_dirige_bien(self):
        self.client.login(username='autorizado', password='1234')
        botones_urls = {
            'turnos_docentes': 'materias/administrar_necesidades_docentes',
            'turnos_alumnos': 'materias/administrar_alumnos',
            'cargas_docentes': 'materias/administrar_cargas_docentes',
            'administrar_docentes': 'materias/administrar_docentes',
            'exportar_informacion': 'materias/exportar_informacion',
            'cargas_docentes_publicadas': 'materias/administrar_cargas_publicadas',
            'administrar_encuestas': 'encuestas/administrar_habilitadas',
            'dborrador': 'dborrador/distribucion',
            'retocar_materias': 'materias/retocar_materias',
            'generar_cuatrimestre': 'materias/generar_cuatrimestre',
            'ver_materias': f'materias/{self.anno}{self.cuatrimestre.value}',
            'cargas_docentes_anuales': 'materias/cargas_docentes_anuales',
        }
        for boton, url in botones_urls.items():
            response = self.client.post('/materias/administrar',
                                        {boton: True, 'anno': self.anno, 'cuatrimestre': self.cuatrimestre.name},
                                        follow=True)
            ultima = response.redirect_chain[-1]
            self.assertTrue(ultima[0].startswith(f'/{url}'))
            self.assertEqual(ultima[1], 302, f'No está redirigiendo bien a {url}')

    def test_administrar_necesidades_docentes(self):
        self.client.login(username='autorizado', password='1234')

        self.turno11.dificil_de_cubrir = True
        self.turno11.save()

        url = f'/materias/administrar_necesidades_docentes/{self.anno}/{self.cuatrimestre.name}'
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
        post[f'necesidadprof_{self.turno12.id}'] = 2
        post['cambiar'] = True
        self.client.post(url, post)

        nturno11 = Turno.objects.get(pk=self.turno11.id)
        nturno12 = Turno.objects.get(pk=self.turno12.id)
        self.assertFalse(nturno11.dificil_de_cubrir)
        self.assertTrue(nturno12.dificil_de_cubrir)
        self.assertEqual(nturno12.necesidad_prof, 2)

        response = self.client.get(url, follow=True)
        self.assertContains(response, '<mark id=mal>2</mark>')
        self.assertContains(response, '<mark id=mal>0</mark>')
        self.assertContains(response, '<mark id=bien>0</mark>')

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

    def test_administrar_converte_vacio_a_0_en_int(self):
        self.client.login(username='autorizado', password='1234')

        model_to_ktf = {Turno: {'alumnos': ('alumnos', int)},
                        Horario: {'aula': ('aula', str),
                                  'pabellon': ('pabellon', int)}}
        post = dict()
        for model, key_to_field in model_to_ktf.items():
            for k_field, (t_attr, _) in key_to_field.items():
                for o in model.objects.all():
                    post[f'{k_field}_{o.id}'] = getattr(o, t_attr)
        # primero pasamos valor vacío, tiene que quedar en 0
        post[f'alumnos_{self.turno12.id}'] = ''
        post['cambiar'] = True
        url = f'/materias/administrar_alumnos/{self.anno}/{self.cuatrimestre.name}'
        self.client.post(url, post)
        self.assertEqual(self.turno12.alumnos, 0)
        # ahora pasamos valor no parseable, tiene que tirar excepción
        # Eso resulta en un 500 Internal Server Error. No está bueno pero sería raro que llegue algo
        # que no es número ni es vacío hasta ahí.
        post[f'alumnos_{self.turno12.id}'] = 'x'
        with self.assertRaises(ValueError):
            self.client.post(url, post)

    def test_administrar_cargas_docentes(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()
        now = timezone.now()
        cuatris = GrupoCuatrimestral.VPS
        Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        Carga.objects.create(docente=self.m, cargo=CargoDedicacion.TitExc.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        Carga.objects.create(docente=self.m, cargo=CargoDedicacion.Ay1Smx.name,
                             anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        PreferenciasDocente.objects.create(docente=self.n, turno=self.turno11,
                                           cargo=Cargos.Tit.name, peso=2, fecha_encuesta=now)
        OtrosDatos.objects.create(docente=self.n, fecha_encuesta=now,
                                  anno=self.anno, cuatrimestre=cuatris.name,
                                  comentario='_esto deberia aparecer_')
        CargasPedidas.objects.create(docente=self.n, fecha_encuesta=now,
                                     anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                     cargas=2)

        response = self.client.get(f'/materias/administrar_cargas_docentes/{self.anno}/{self.cuatrimestre.name}', follow=True)
        self.assertContains(response, '>nemo X<')
        self.assertContains(response, '_esto deberia aparecer_')
        self.assertContains(response, '>mario Y<')

    def test_administrar_cargas_de_un_docente(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()
        self.n.cargos = [CargoDedicacion.TitExc.name, CargoDedicacion.Ay1Smx.name]
        self.n.save()
        c1 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        c2 = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        now = timezone.now()
        OtrosDatos.objects.create(docente=self.n, fecha_encuesta=now,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        CargasPedidas.objects.create(docente=self.n, fecha_encuesta=now,
                                     anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                     cargas=2)
        cm = Carga.objects.create(docente=self.m, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)

        url = f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{self.n.id}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'cargo_TitExc')
        self.assertContains(response, 'cargo_Ay1Smx')

        response = self.client.post(f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{self.n.id}',
                                    {'salvar': True, 'anno': self.anno, 'cuatrimestre': self.cuatrimestre.name,
                                     'cargo_TitExc': 1, 'cargo_Ay1Smx': 1},
                                    follow=True)
        self.assertEquals(Carga.objects.filter(docente=self.n, cargo='TitExc').count(), 1)
        self.assertEquals(Carga.objects.filter(docente=self.n, cargo='Ay1Smx').count(), 1)

        url = f'/materias/administrar_cargas_un_docente/{self.anno}/{self.cuatrimestre.name}/{self.m.id}'
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
        self.assertRegex(response.content.decode(), f'{TipoTurno.T.value}\s*\n.*value=5')
        nuevo_turno = Turno.objects.get(materia=self.materia1, tipo=TipoTurno.T.name, numero=5)
        # no tiene horarios
        self.assertEqual(nuevo_turno.horario_set.count(), 0)

    def test_cambiar_turno(self):
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:cambiar_turno', args=(self.turno11.id,))
        response = self.client.post(url, follow=True)
        # hay botones para borrar horarios, cambiar y cancelar
        for horario in self.turno11.horario_set.all():
            boton = f'input type="button" id="borrar_horario" data-horario="{horario.id}" value="Borrar horario">'
            self.assertContains(response, boton)
        self.assertContains(response, '<input type="submit" name="cambiar" value="cambiar">')
        self.assertContains(response, '<input type="submit" name="cancelar" value="cancelar">')
        # se puede agregar un horario
        self.assertEqual(self.turno11.horario_set.count(), 2)
        self.client.post(url, {'nuevo_2_dia': Dias.Vi.name, 'nuevo_2_comienzo': '01:23:45', 'nuevo_2_final': '12:34:56',
                               'numero_turno': self.turno11.numero, 'subnumero_turno': self.turno11.subnumero,
                               'cambiar': True},
                         follow=True)
        self.assertEqual(self.turno11.horario_set.count(), 3)
        nuevo_horario = Horario.objects.get(turno=self.turno11, comienzo=datetime.time(1, 23, 45))
        self.assertEqual(nuevo_horario.dia, Dias.Vi.name)
        self.assertEqual(nuevo_horario.final, datetime.time(12, 34, 56))
        # se puede cambiar un horario existente
        data = {f'existente_{nuevo_horario.id}_dia': Dias.Ju.name,
                f'existente_{nuevo_horario.id}_comienzo': '10:47:41',
                f'existente_{nuevo_horario.id}_final': '10:47:42',
                'numero_turno': self.turno11.numero, 'subnumero_turno': self.turno11.subnumero,
                'cambiar': True}
        self.client.post(url, data, follow=True)
        self.assertEqual(self.turno11.horario_set.count(), 3)
        nuevo_horario.refresh_from_db()
        self.assertEqual(nuevo_horario.dia, Dias.Ju.name)
        self.assertEqual(nuevo_horario.comienzo, datetime.time(10, 47, 41))
        self.assertEqual(nuevo_horario.final, datetime.time(10, 47, 42))

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
        self.assertEqual(response.redirect_chain[0][0],
                         reverse('materias:administrar_materia',
                                 args=(self.materia1.id, self.anno, self.cuatrimestre.name)))

    def test_cambiar_cargas_publicadas(self):
        self._agrega_docentes()
        cn = Carga.objects.create(docente=self.n, cargo=CargoDedicacion.TitExc.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        cm = Carga.objects.create(docente=self.m, cargo=CargoDedicacion.JTPPar.name,
                                  anno=self.anno, cuatrimestre=self.cuatrimestre.name, turno=self.turno11)
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:administrar_cargas_publicadas', args=(self.anno, self.cuatrimestre.name))
        response = self.client.get(url, follow=True)
        # veo que aparece la carga distribuida y el cargo con su nombre largo
        self.assertContains(response, reverse('materias:cambiar_una_carga_publicada', args=(cn.id,)))
        self.assertContains(response, CargoDedicacion[cm.cargo].value)
        # veo que aparece la carga no distribuida y el cargo
        self.assertContains(response, reverse('materias:cambiar_una_carga_publicada', args=(cm.id,)))
        self.assertContains(response, CargoDedicacion[cn.cargo].value)

    def test_exportar_materias_a_excel(self):
        self.client.login(username='autorizado', password='1234')
        response = self.client.post(reverse('materias:exportar_informacion', args=(self.anno, self.cuatrimestre.name)),
                                    {'info_anual': True},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/ms-excel')

    def test_juntar_materias(self):
        self.client.login(username='autorizado', password='1234')
        duplicada = Materia.objects.create(nombre='lacán 3', obligatoriedad=TipoMateria.B.name)
        # priemro consultamos la página
        response = self.client.get(reverse('materias:retocar_materias'))
        for materia in [self.materia1, self.materia2, self.materia3,  duplicada]:
            self.assertContains(response, materia.nombre)
        # le decimos de juntar materias
        response = self.client.post(reverse('materias:retocar_materias'),
                                    {f'juntar_{self.materia3.id}': True, f'juntar_{duplicada.id}': True})
        for materia, debe_estar in {self.materia1: False, self.materia2: False, self.materia3: True,  duplicada: True}.items():
            if debe_estar:
                self.assertContains(response, materia.nombre)
            else:
                self.assertNotContains(response, materia.nombre)
        # pido juntarlas
        turno = Turno.objects.create(materia=self.materia3, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                     numero=2, tipo=TipoTurno.T.name, **self.dict_nec)
        response = self.client.post(reverse('materias:retocar_materias'),
                                    {f'juntar_{self.materia3.id}': True, f'juntar_{duplicada.id}': True,
                                     'nombre': f'nombre_{duplicada.id}',
                                     'confirmar': True})
        self.assertEqual(Materia.objects.count(), 3)
        self.assertEqual(AliasDeMateria.objects.count(), 1)
        self.assertEqual(AliasDeMateria.objects.first().materia, duplicada)
        turno = Turno.objects.get(pk=turno.id)
        self.assertEqual(turno.materia, duplicada)

    def test_copiar_turnos(self):
        # agrego una materia optativa
        materia4 = Materia.objects.create(nombre='lacan 4', obligatoriedad=TipoMateria.N.name)
        turno41 = Turno.objects.create(materia=materia4, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                       numero=1, tipo=TipoTurno.T.name, **self.dict_nec)

        self.client.login(username='autorizado', password='1234')
        response = self.client.get(reverse('materias:generar_cuatrimestre', args=(self.anno, self.cuatrimestre.name)))
        self.assertContains(response, f'value="{self.cuatrimestre.name}" selected>{self.cuatrimestre.value}')
        response = self.client.post(reverse('materias:generar_cuatrimestre', args=(self.anno, self.cuatrimestre.name)),
                                    {'nuevo_anno': self.anno+1, 'nuevo_cuatrimestre': self.cuatrimestre.name,
                                     f'copiar_{TipoMateria.B.name}': True,
                                     f'copiar_{TipoMateria.R.name}': True})
        for tipo in (TipoMateria.B, TipoMateria.R):
            self.assertEqual(
                Turno.objects.filter(anno=self.anno, cuatrimestre=self.cuatrimestre.name, materia__obligatoriedad=tipo.name).count(),
                Turno.objects.filter(anno=self.anno+1, cuatrimestre=self.cuatrimestre.name, materia__obligatoriedad=tipo.name).count())

        self.assertEqual(Turno.objects.filter(anno=self.anno,
                                              cuatrimestre=self.cuatrimestre.name,
                                              materia__obligatoriedad=TipoMateria.N.name).count(),
                         1)
        self.assertEqual(Turno.objects.filter(anno=self.anno+1,
                                              cuatrimestre=self.cuatrimestre.name,
                                              materia__obligatoriedad=TipoMateria.N.name).count(),
                         0)

        nuevo_turno11 = Turno.objects.get(anno=self.anno+1, cuatrimestre=self.cuatrimestre.name,
                                          materia=self.materia1, numero=1)
        self.assertEqual(Horario.objects.filter(turno=nuevo_turno11).count(), 2)

        for horario in Horario.objects.filter(turno=nuevo_turno11):
            self.assertIsNotNone(horario.aula)

    def test_administrar_docentes(self):
        self.client.login(username='autorizado', password='1234')
        response = self.client.get(reverse('materias:administrar_docentes'))
        self.assertContains(response, 'type="submit" name="juntar"')
        self.assertContains(response, 'type="submit" name="cambiar_cargo"')
        # sin docentes no hay nadie
        checkboxes = re.findall('<input type="checkbox" name="juntar_(\d+)">', response.content.decode())
        self.assertEqual(len(checkboxes), 0)
        # ahora con docentes y tres cargos
        self._agrega_docentes()
        response = self.client.get(reverse('materias:administrar_docentes'))
        checkboxes = re.findall('<input type="checkbox" name="juntar_(\d+)">', response.content.decode())
        self.assertEqual(len(checkboxes), 3)
        self.assertEqual(set(checkboxes), {f'{self.n.id}', f'{self.m.id}'})

    def test_juntar_docentes(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()
        post = {f'juntar_{self.n.id}': True, f'juntar_{self.m.id}': True, 'juntar': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        self.assertContains(response, '<select id="nombre" name="nombre">')
        self.assertContains(response, f'<option value="nombre_{self.n.id}">')
        self.assertContains(response, f'<option value="nombre_{self.m.id}">')
        # confirmo juntar
        now = timezone.now()
        carga = Carga.objects.create(docente=self.m, cargo=CargoDedicacion.TitExc.name,
                                     anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        pref = PreferenciasDocente.objects.create(docente=self.m, turno=self.turno11,
                                                  cargo=Cargos.Tit.name, peso=2, fecha_encuesta=now)
        otrosdatos = OtrosDatos.objects.create(docente=self.m, fecha_encuesta=now,
                                               anno=self.anno, cuatrimestre=self.cuatrimestre.name, comentario='')
        pedidas = CargasPedidas.objects.create(docente=self.m, fecha_encuesta=now,
                                               anno=self.anno, cuatrimestre=self.cuatrimestre.name, cargas=2)
        post = {f'juntar_{self.n.id}': True, f'juntar_{self.m.id}': True, 'nombre': f'nombre_{self.n.id}', 'confirmar': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        with self.assertRaises(Docente.DoesNotExist):
            self.m.refresh_from_db()
        id_anterior = self.n.id
        self.n.refresh_from_db()
        self.assertEqual(self.n.id, id_anterior)
        self.assertEqual(self.n.nombre, 'nemo X')

        for objeto in [carga, pref, otrosdatos, pedidas]:
            objeto.refresh_from_db()
            self.assertEqual(objeto.docente, self.n)

    def test_cambiar_cargo(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()
        post = {f'juntar_{self.n.id}': True, f'juntar_{self.m.id}': True, 'cambiar_cargo': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        self.assertContains(response, '<select name="cargo">')
        self.assertContains(response, f'<input type="hidden" name="juntar_{self.n.id}">')
        self.assertContains(response, f'<input type="hidden" name="juntar_{self.m.id}">')
        # confirmo cambiar
        post = {f'juntar_{self.n.id}': True, f'juntar_{self.m.id}': True,
                'cargo': f'cargo_{CargoDedicacion.Ay2Par.name}', 'confirma_cambiar': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        self.m.refresh_from_db()
        self.n.refresh_from_db()
        self.assertEquals(self.m.cargos, [CargoDedicacion.Ay2Par.name])
        self.assertEquals(self.n.cargos, [CargoDedicacion.Ay2Par.name])

    def test_administrar_un_docente(self):
        self.client.login(username='autorizado', password='1234')
        n = Docente.objects.create(na_nombre='nemo', na_apellido='X', telefono='00 0000', email='nemo@nautilus.org',
                                   cargos=[CargoDedicacion.TitExc.name])
        response = self.client.get(reverse('materias:administrar_un_docente', args=(n.id,)))
        self.assertTrue(re.search('<input type="text" name="na_nombre" value="nemo" .*>', response.content.decode()))
        self.assertTrue(re.search('<input type="text" name="na_apellido" value="X" .*>', response.content.decode()))
        self.assertTrue(re.search(f'<input type="text" name="telefono" value="{n.telefono}" .*>', response.content.decode()))
        self.assertTrue(re.search(f'<input type="email" name="email" value="{n.email}" .*>', response.content.decode()))
        self.assertTrue(re.search('<select name="cargo0" id="id_cargo0">', response.content.decode()))
        self.assertTrue(re.search('<select name="cargo1" id="id_cargo1">', response.content.decode()))
        self.assertTrue(re.search('<select name="cargo2" id="id_cargo2">', response.content.decode()))
        # le cambio el apellido
        self.client.post(reverse('materias:administrar_un_docente', args=(n.id,)),
                         {'na_nombre': n.nombre, 'na_apellido': 'nuevo apellido',
                          'telefono': '0123456789', 'email': n.email,
                          'cargo0': CargoDedicacion.TitExc.name, 'cargo1': '', 'cargo2': '',
                          'salvar': True,
                          })
        n.refresh_from_db()
        self.assertEqual(n.na_apellido, 'nuevo apellido')

    def test_agregar_y_modificar_materias(self):
        # miramos que modificar materias tiene links a todas las materias
        self.client.login(username='autorizado', password='1234')
        response = self.client.get(reverse('materias:retocar_materias'))
        for materia in (self.materia1, self.materia2, self.materia3):
            url = reverse('materias:modificar_materia', args=(materia.id,))
            self.assertContains(response, f'href="{url}">{materia.nombre}')
        # ahora modificamos una sola
        url = reverse('materias:modificar_materia', args=(self.materia1.id,))
        response = self.client.post(url, {'salvar': True, 'obligatoriedad': TipoMateria.R.name,
                                          'nombre': 'lacan 1 - freud 0'})
        self.materia1.refresh_from_db()
        self.assertEqual(self.materia1.nombre, 'lacan 1 - freud 0')
        self.assertEqual(self.materia1.obligatoriedad, TipoMateria.R.name)
        # y ahora creamos una nueva materia
        response = self.client.post(reverse('materias:agregar_materia'), follow=True)
        redirect_url, status = response.redirect_chain[-1]
        self.assertEqual(status, 302)
        nueva_materia_id = int(redirect_url.split('/')[-1])
        for materia in (self.materia1, self.materia2, self.materia3):
            self.assertNotEqual(nueva_materia_id, materia.id)
        nueva_materia = Materia.objects.get(pk=nueva_materia_id)
        self.assertEqual(nueva_materia.obligatoriedad, TipoMateria.N.name)
        # y la borramos
        response = self.client.post(redirect_url, {'borrar': True, 'obligatoriedad': '?', 'nombre': 'no importa'}, follow=True)
        with self.assertRaises(Materia.DoesNotExist):
            nueva_materia.refresh_from_db()
        self.assertEqual(response.redirect_chain[-1][0], reverse('materias:retocar_materias'))

    def test_agregar_y_borrar_docente(self):
        self.client.login(username='autorizado', password='1234')
        # lo agregamos
        response = self.client.post(reverse('materias:administrar_docentes'), {'agregar': True}, follow=True)
        redirect_url, status = response.redirect_chain[-1]
        self.assertEqual(status, 302)
        nuevo_docente_id = int(redirect_url.split('/')[-1])
        nuevo_docente = Docente.objects.get(pk=nuevo_docente_id)
        self.assertEqual(nuevo_docente.cargos, [])
        # y lo borramos
        response = self.client.post(redirect_url, {'borrar': True}, follow=True)
        with self.assertRaises(Docente.DoesNotExist):
            nuevo_docente.refresh_from_db()
        self.assertEqual(response.redirect_chain[-1][0], reverse('materias:administrar_docentes'))

    def test_agregar_cargas_y_distribuir(self):
        self.client.login(username='autorizado', password='1234')
        anno = 2345
        cuatrimestre = Cuatrimestres.P
        self._agrega_docentes()

        turno = Turno.objects.create(materia=self.materia1, anno=anno, cuatrimestre=cuatrimestre.name,
                                      numero=1, tipo=TipoTurno.T.name, **self.dict_nec)

        url = reverse('materias:agregar_carga_y_distribuir', args=(self.m.id, anno, cuatrimestre.name))
        response = self.client.get(url)
        # se crearon dos cargas sin turno
        cargas_nuevas = Carga.objects.filter(docente=self.m, anno=anno, cuatrimestre=cuatrimestre.name)
        self.assertEqual(cargas_nuevas.count(), 2)
        for carga in cargas_nuevas.all():
            self.assertContains(response, f'<select name="carga_{carga.id}">')
        # cancelo la generación
        response = self.client.post(url, {'cancelar': 'cancelar'})
        # se borran las cargas
        cargas_nuevas = Carga.objects.filter(docente=self.m, anno=anno, cuatrimestre=cuatrimestre.name)
        self.assertEqual(cargas_nuevas.count(), 0)

        # vuelvo a generarlas y distribuyo en turno
        self.client.get(url)
        cargas_nuevas = Carga.objects.filter(docente=self.m, anno=anno, cuatrimestre=cuatrimestre.name)
        self.assertEqual(cargas_nuevas.count(), 2)
        post_data = {f'carga_{carga.id}': str(turno.id) for carga in cargas_nuevas}
        post_data['cambiar'] = 'salvar'
        response = self.client.post(url, post_data)
        for carga in cargas_nuevas:
            carga.refresh_from_db()
            self.assertEqual(carga.turno, turno)

    def test_cargas_docentes_anuales(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()

        now = timezone.now()
        CargasPedidas.objects.create(docente=self.n, anno=self.anno, cuatrimestre=Cuatrimestres.V.name,
                                     cargas=331, tipo_docente=TipoDocentes.P.name, fecha_encuesta=now)
        comentario = '_este comentario debe aparecer_'
        OtrosDatos.objects.create(docente=self.n, anno=self.anno, cuatrimestre=Cuatrimestres.V.name,
                                  comentario=comentario, cargas_declaradas=571, fecha_encuesta=now,)

        response = self.client.get(reverse('materias:cargas_docentes_anuales', args=(self.anno,)))
        self.assertRegex(response.content.decode(), r'<mark id="mal">\s*331\s*</mark>')
        self.assertContains(response, comentario)
        self.assertContains(response, 571)

    def test_cambio_cargas_docentes_anuales(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()

        turnos = {cuat: Turno.objects.create(materia=self.materia1, anno=self.anno, cuatrimestre=cuat.name,
                                             numero=1, tipo=TipoTurno.T.name, **self.dict_nec)
                  for cuat in Cuatrimestres}

        # una carga para n, dos para m por cuatrimestre
        for cuat in Cuatrimestres:
            Carga.objects.create(docente=self.n, anno=self.anno, cuatrimestre=cuat.name, cargo=self.n.cargos[0])
            Carga.objects.create(docente=self.m, anno=self.anno, cuatrimestre=cuat.name, cargo=self.m.cargos[0])
            asignada = Carga.objects.create(docente=self.m, anno=self.anno, cuatrimestre=cuat.name, cargo=self.m.cargos[0])
            # le pongo una asignación a una de las de self.m
            Asignacion.objects.create(intentos=(0, 1), carga=asignada, turno=turnos[cuat], cargo_que_ocupa=TipoDocentes.P.name)

        response = self.client.get(reverse('materias:cargas_docentes_anuales', args=(self.anno,)))
        for cuat in Cuatrimestres:
            self.assertContains(response, f'<input type="number" name="cargas_{self.n.id}_{self.n.cargos[0]}_{cuat.name}"')
            self.assertContains(response, f'<input type="number" name="cargas_{self.m.id}_{self.m.cargos[0]}_{cuat.name}"')

        cambios = {
            **{f'cargas_{self.n.id}_{self.n.cargos[0]}_{cuat.name}': i  for i, cuat in enumerate(Cuatrimestres)},
            **{f'cargas_{self.m.id}_{self.m.cargos[0]}_{cuat.name}': 1  for i, cuat in enumerate(Cuatrimestres)},
            'salvar': True,
        }
        self.client.post(reverse('materias:cargas_docentes_anuales', args=(self.anno,)), cambios)
        for i, cuat in enumerate(Cuatrimestres):
            self.assertEqual(Carga.objects.filter(docente=self.n, anno=self.anno, cuatrimestre=cuat.name).count(), i)
            self.assertEqual(Carga.objects.filter(docente=self.m, anno=self.anno, cuatrimestre=cuat.name).count(), 1)
            # chequeo que la que quedó sin borrar es la que tiene asignación
            self.assertEqual(Asignacion.objects.filter(carga__docente=self.m,  turno=turnos[cuat]).count(), 1)

    def test_generar_cargas_docentes_anuales(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_docentes()
        context = {'generar': True}
        response = self.client.post(reverse('materias:cargas_docentes_anuales', args=(self.anno + 1,)), context)
        for docente in (self.n, self.m):
            for cuatrimestre in Cuatrimestres:
                for cargo in docente.cargos:
                    cargas = Carga.objects.filter(docente=docente, anno=self.anno+1, cuatrimestre=cuatrimestre.name, cargo=cargo)
                    self.assertEquals(cargas.count(), 0 if cuatrimestre is Cuatrimestres.V else 1)



class TestCasosBorde(TestCase):

    def setUp(self):
        self.anno = 2345
        self.cuatrimestre = Cuatrimestres.V
        self.materia = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        dict_nec = {'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        self.turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                          numero=1, tipo=TipoTurno.T.name, **dict_nec)
        Usuario.objects.create_user(username='desautorizado', password='123')
        autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='materias', codename='add_turno'))
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='dborrador', codename='add_asignacion'))
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='materias', codename='view_docente'))

    def test_juntar_docentes_con_carga_sin_turno(self):
        self.client.login(username='autorizado', password='1234')
        n1 = Docente.objects.create(na_nombre='nemo', na_apellido='X',
                                    telefono='00 0000', email='nemo@nautilus.org', cargos=[CargoDedicacion.TitExc.name])
        n2 = Docente.objects.create(na_nombre='nemo', na_apellido='Y',
                                    telefono='00 0000', email='nemo@nautilus.org', cargos=[CargoDedicacion.JTPExc.name])
        c1 = Carga.objects.create(docente=n1, cargo=CargoDedicacion.TitExc.name, anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        c2 = Carga.objects.create(docente=n2, cargo=CargoDedicacion.TitExc.name, anno=self.anno, cuatrimestre=self.cuatrimestre.name)
        post = {f'juntar_{n1.id}': True, f'juntar_{n2.id}': True, 'juntar': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        self.assertEqual(response.status_code, 200)
        post = {f'juntar_{n1.id}': True, f'juntar_{n2.id}': True, 'nombre': f'nombre_{n1.id}', 'confirmar': True}
        response = self.client.post(reverse('materias:administrar_docentes'), post)
        self.assertEqual(response.status_code, 200)
        c2.refresh_from_db()
        self.assertEqual(c2.docente, n1)
        self.assertEqual(c2.turno, None)

    def test_administrar_materia_sin_turnos(self):
        self.client.login(username='autorizado', password='1234')
        url = reverse('materias:administrar_materia', args=(self.materia.id, self.anno + 8, self.cuatrimestre.name))
        # miro materia sin turnos
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # ahora intento agregar un turno
        response = self.client.post(url, {'agregar_turno_T': True}, follow=True)
        self.assertEqual(response.status_code, 200)
