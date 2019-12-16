from django.test import TestCase
from django.test.utils import setup_test_environment
from django.utils import timezone
from django.urls import reverse
from django.forms import ValidationError
from django.contrib.auth.models import Permission

import re
import datetime
import time

from materias.models import (Docente, Carga, Cargos, Materia, Turno, TipoTurno, TipoMateria,
                             CargoDedicacion, Cuatrimestres)
from materias.misc import TipoDocentes, Mapeos, Cargos, Docente
from usuarios.models import Usuario
from .models import PreferenciasDocente, OtrosDatos, CargasPedidas, EncuestasHabilitadas, GrupoCuatrimestral
from .views import checkear_y_salvar
from usuarios.models import Usuario


class TestEncuesta(TestCase):

    def setUp(self):
        self.anno = 2100
        self.docente = Docente.objects.create(na_nombre='juan', email='mail@nada.org',
                                              telefono='1234',
                                              cargos=[CargoDedicacion.JTPSmx.name])
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B.name)
        self.turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                          numero=1, tipo=TipoTurno.A.name,
                                          necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
        self.turno_dificil = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                                  numero=2, tipo=TipoTurno.T.name,
                                                  necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0,
                                                  dificil_de_cubrir=True)
        self.otros_datos = {'telefono': '+54911 1234-5678', 'email': 'nadie@gmail.com', 'comentario': '',
                            f'cargas{Cuatrimestres.P.name}': 1, 'cargas_declaradas': 1}
        now = timezone.now()
        for tipo in TipoDocentes:
            EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=Cuatrimestres.P.name, tipo_docente=tipo.name,
                                                desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        Usuario.objects.create_user(username='desautorizado', password='123')
        autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='dborrador', codename='add_asignacion'))

    def test_pocos_turnos(self):
        datos = self.otros_datos
        datos['docente'] = self.docente.id
        datos[f'opcion{Cuatrimestres.P.name}1'] = str(self.turno.id)
        datos[f'peso{Cuatrimestres.P.name}1'] = 2
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, f'{Cuatrimestres.P.name}', TipoDocentes.J.name)

    def test_sin_docente(self):
        datos = self.otros_datos
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)

    def test_docente_no_existe(self):
        docente_inexistente_id = str(self.docente.id + 1)
        datos = {'docente': docente_inexistente_id, **self.otros_datos}
        with self.assertRaises(Docente.DoesNotExist):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)

    def test_docente_sin_opciones(self):
        datos = {'docente': self.docente.id}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)

    def test_turno_no_existe(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        c = Cuatrimestres.P.name
        for opcion in range(1, 6):
            datos[f'opcion{c}{opcion}'] = str(self.turno.id + opcion)
            datos[f'peso{c}{opcion}'] = str(opcion)
        with self.assertRaises(Turno.DoesNotExist):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)

    def test_docente_y_opciones_vacias(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        c = Cuatrimestres.P.name
        for opcion in range(1, 6):
            datos[f'opcion{c}{opcion}'] = '-1'
            datos[f'peso{c}{opcion}'] = str(opcion)
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 0)

    def test_docente_y_opciones_con_sentido(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        c = Cuatrimestres.P.name
        for opcion in range(1, 6):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            datos[f'opcion{c}{opcion}'] = turno.id
            datos[f'peso{c}{opcion}'] = str(opcion)
        datos[f'cargas{c}'] = 1
        checkear_y_salvar(datos, self.anno, c, TipoDocentes.J.name)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 5)

    def test_algunas_opciones_vacias(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        for opcion in range(1, 3):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            datos['opcion{}'.format(opcion)] = turno.id
            datos['peso{}'.format(opcion)] = str(opcion)
        for opcion in range(3, 6):
            datos['opcion{}'.format(opcion)] = '-1'
            datos['peso{}'.format(opcion)] = str(opcion)
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name, TipoDocentes.J.name)

    def test_titulo_correcto(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, TipoDocentes.J.name)))
        self.assertEqual(response.request['PATH_INFO'], f'/encuestas/encuesta/{self.anno}/P/J')
        self.assertTrue(re.search('Preferencias para el\s*primer cuatrimestre', response.content.decode(), re.DOTALL))

    def test_turnos_correctos(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, TipoDocentes.J.name)))
        self.assertContains(response, self.turno.materia.nombre)
        self.assertContains(response, f'{self.turno} (sin horario)')

    def test_turnos_otros_cuatrimestres(self):
        now = timezone.now()
        EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=Cuatrimestres.S.name,
                                            tipo_docente=TipoDocentes.J.name,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.S.name, TipoDocentes.J.name)))
        self.assertNotContains(response, self.turno.materia.nombre)

    def test_turnos_otros_annos(self):
        now = timezone.now()
        EncuestasHabilitadas.objects.create(anno=self.anno+1, cuatrimestres=Cuatrimestres.P.name,
                                            tipo_docente=TipoDocentes.J.name,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(reverse('encuestas:encuesta',
                                           args=(str(self.anno + 1), Cuatrimestres.P.name, TipoDocentes.J.name)))
        self.assertNotContains(response, self.turno.materia.nombre)

    def test_turnos_repetidos(self):
        datos = {'docente': self.docente.id}
        turnos = [Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                          numero=t, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
                  for t in range(1, 6)
                  ]

        c = Cuatrimestres.P.name
        datos[f'cargas{c}'] = 1
        datos[f'email'] = 'sarasa@com.ar'
        datos[f'telefono'] = '1 2345 6789'
        datos[f'comentario'] = ''
        for opcion, turno in enumerate(turnos, 1):
            datos[f'opcion{c}{opcion}'] = turno.id
            datos[f'peso{c}{opcion}'] = str(1)
        # repetimos la opcion 2
        datos[f'opcion{c}2'] = turnos[0].id
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, c, TipoDocentes.J.name)

    def test_encuesta_distingue_turnos_dificiles(self):
        '''Chequeamos que el turno dificil aparece 5 veces en la encuesta y el facil 3'''
        response = self.client.get(f'/encuestas/encuesta/{self.anno}/{Cuatrimestres.P.name}/{TipoDocentes.P.name}')
        opcion_reg_facil = re.compile(f'^.*<option value="{self.turno.id}"[ \n]*>', re.MULTILINE)
        opcion_reg_dificil = re.compile(f'^.*<option value="{self.turno_dificil.id}"[ \n]*>', re.MULTILINE)
        self.assertEqual(len(opcion_reg_facil.findall(response.content.decode())), 3)
        self.assertEqual(len(opcion_reg_dificil.findall(response.content.decode())), 5)

    def test_encuesta_salva_otros_datos(self):
        c = Cuatrimestres.P.name
        opciones = {f'opcion{c}1': self.turno.id, f'peso{c}1': 1}
        for opcion in range(2, 6):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            opciones[f'opcion{c}{opcion}'] = turno.id
            opciones[f'peso{c}{opcion}'] = 0
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{c}/{TipoDocentes.P.name}',
                                    {'docente': self.docente.id,
                                     'cargas_declaradas': 1,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno'},
                                    follow=True)
        self.assertEqual(OtrosDatos.objects.count(), 1)
        od = OtrosDatos.objects.first()
        self.assertEqual(od.comentario, 'pero qué corno')
        self.assertEqual(od.telefono,  '+54911 1234-5678')
        self.assertEqual(od.email,  'juan@dm.uba.ar')
        self.assertContains(response, 'Gracias')
        self.assertEqual(od.cargas_declaradas, 1)

        cp = CargasPedidas.objects.get(anno=self.anno, cuatrimestre=c, docente=self.docente)
        self.assertEqual(cp.cargas, 1)

    def test_orden_docentes(self):
        for docente in [5, 1, 3, 8, 9, 6, 0, 7, 2, 4]:
            d = Docente.objects.create(na_nombre=f'doc{docente}', na_apellido='X', email='mail@nada.org', telefono='1234',
                                   cargos=[CargoDedicacion.JTPSmx.name])
            Carga.objects.create(docente=d, cargo=CargoDedicacion.JTPSmx.name, anno=self.anno, cuatrimestre=Cuatrimestres.P.name)
        response = self.client.get(f'/encuestas/encuesta/{self.anno}/{Cuatrimestres.P.name}/{TipoDocentes.J.name}')

        docentes_en_desplegable = re.findall('>X, (doc[0-9])<', response.content.decode())
        self.assertEqual(docentes_en_desplegable, [f'doc{d}' for d in range(10)])

    def test_orden_materias_y_turnos(self):
        desorden = [4, 1, 3, 5, 2]
        orden = sorted(desorden)
        anno = 2107

        for materia in desorden:
            m = Materia.objects.create(nombre=f'materia{materia}', obligatoriedad=TipoMateria.B.name)
            for turno in desorden:
                Turno.objects.create(materia=m, anno=anno, cuatrimestre=Cuatrimestres.P.name,
                                     numero=turno, tipo=TipoTurno.T.name, dificil_de_cubrir=True,
                                     necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)

        now = timezone.now()
        EncuestasHabilitadas.objects.create(anno=anno, cuatrimestres=Cuatrimestres.P.name,
                                            tipo_docente=TipoDocentes.P.name,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(f'/encuestas/encuesta/{anno}/{Cuatrimestres.P.name}/{TipoDocentes.P.name}')

        materias = re.findall('materia([0-9]),', response.content.decode())
        self.assertEqual(materias, [f'{materia}' for opcion in range(5)
                                                 for materia in orden
                                                 for turno in orden])

        turnos = re.findall(f'materia[0-9],.*, {TipoTurno.T.value} ([0-9]) ', response.content.decode())
        # por alguna razón, unittest se cuelga con un assertEqual para turnos igual al de materias, así que los convierto en str
        esperados = [f'{turno}' for opcion in range(5)
                                for materia in orden
                                for turno in orden]
        self.assertEqual(''.join(turnos), ''.join(esperados))

    def test_orden_materias_argentina(self):
        desorden = ['b', 'á', 'ñ', 'ü', 't']
        orden = ['á', 'b', 'ñ', 't', 'ü']
        anno = 2107

        for materia in desorden:
            m = Materia.objects.create(nombre=f'materia{materia}', obligatoriedad=TipoMateria.B.name)
            Turno.objects.create(materia=m, anno=anno, cuatrimestre=Cuatrimestres.P.name,
                                 numero=1, tipo=TipoTurno.T.name, dificil_de_cubrir=True,
                                 necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)

        now = timezone.now()
        EncuestasHabilitadas.objects.create(anno=anno, cuatrimestres=Cuatrimestres.P.name,
                                            tipo_docente=TipoDocentes.P.name,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(f'/encuestas/encuesta/{anno}/{Cuatrimestres.P.name}/{TipoDocentes.P.name}')

        materias = re.findall('materia(.),', response.content.decode())
        self.assertEqual(materias, [f'{materia}' for opcion in range(5)
                                                 for materia in orden])

    def test_encuesta_mas_de_un_cuatri(self):
        now = timezone.now()
        EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=f'{Cuatrimestres.V.name}{Cuatrimestres.P.name}{Cuatrimestres.S.name}',
                                            tipo_docente=TipoDocentes.P.name,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(reverse('encuestas:encuesta', args=(self.anno,
                                                                       f'{Cuatrimestres.V.name}{Cuatrimestres.P.name}{Cuatrimestres.S.name}',
                                                                       'P')), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_habilitar_encuesta(self):
        self.client.login(username='autorizado', password='1234')
        now = timezone.now()
        response = self.client.get(reverse('encuestas:administrar_habilitadas'), follow=True)
        self.assertContains(response, 'Habilitar otra encuesta')

        cuatrimestres = f'{Cuatrimestres.V.name}{Cuatrimestres.P.name}{Cuatrimestres.S.name}'
        response = self.client.post(reverse('encuestas:agregar_habilitacion'),
                                    {'anno': 2050, 'cuatrimestres': cuatrimestres,
                                     'tipo_docente': TipoDocentes.J.name,
                                     'desde': '01/01/2050 00:00', 'hasta': '07/01/2050 12:34',
                                     },
                                    follow=True)
        self.assertEqual(EncuestasHabilitadas.objects.filter(anno=2050).count(), 1)
        habilitacion = EncuestasHabilitadas.objects.get(anno=2050)
        self.assertEqual(habilitacion.cuatrimestres, cuatrimestres)
        self.assertEqual(habilitacion.tipo_docente, TipoDocentes.J.name)
        self.assertEqual(habilitacion.desde, datetime.datetime(2050, 1, 1, 0, 0, 0).astimezone(datetime.timezone.utc))
        self.assertEqual(habilitacion.hasta, datetime.datetime(2050, 1, 7, 12, 34, 0).astimezone(datetime.timezone.utc))

    def test_encuesta_no_habilitada(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(2100, 'VPS', 'P')), follow=True)
        self.assertEqual(response.status_code, 403)

    def test_encuesta_sin_docente_declarado(self):
        c = Cuatrimestres.P.name
        opciones = {}
        for opcion in range(1, 6):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            opciones[f'opcion{c}{opcion}'] = turno.id
            opciones[f'peso{c}{opcion}'] = 0
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{c}/{TipoDocentes.P.name}',
                                    {'docente': -1,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno'},
                                    follow=True)
        self.assertNotContains(response, 'Gracias')
        self.assertContains(response, '[error]  No me dijiste quién sos')

    def test_encuesta_dos_veces(self):
        c = Cuatrimestres.P.name
        opciones = {}
        for opcion in range(1, 6):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            opciones[f'opcion{c}{opcion}'] = turno.id
            opciones[f'peso{c}{opcion}'] = 0
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{c}/{TipoDocentes.P.name}',
                                    {'docente': self.docente.id,
                                     'cargas_declaradas': 1,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno 1'},
                                    follow=True)
        self.assertEqual(PreferenciasDocente.objects.count(), 5)
        time.sleep(0.1)
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{c}/{TipoDocentes.P.name}',
                                    {'docente': self.docente.id,
                                     'cargas_declaradas': 2,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno 2'},
                                    follow=True)
        self.assertEqual(PreferenciasDocente.objects.count(), 10)
        self.assertEqual(OtrosDatos.objects.count(), 2)
        # esto asume que el orden es por fecha
        self.assertEqual(OtrosDatos.objects.first().cargas_declaradas, 1)
        self.assertEqual(OtrosDatos.objects.last().cargas_declaradas, 2)
        for od in OtrosDatos.objects.all():
            self.assertEqual(od.email, 'juan@dm.uba.ar')
            self.assertEqual(od.telefono, '+54911 1234-5678')
            self.assertRegexpMatches(od.comentario, 'pero qué corno \d')

    def test_encuesta_con_pocos_turnos(self):
        c = Cuatrimestres.P.name
        opciones = {}
        for opcion in range(1, 3):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=opcion, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            opciones[f'opcion{c}{opcion}'] = turno.id
            opciones[f'peso{c}{opcion}'] = 0
        for opcion in range(3, 6):
            opciones[f'opcion{c}{opcion}'] = -1
            opciones[f'peso{c}{opcion}'] = 0
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{c}/{TipoDocentes.P.name}',
                                    {'docente': self.docente.id,
                                     'cargas_declaradas': 1,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno 1'},
                                    follow=True)
        self.assertContains(response, 'La cantidad mínima de turnos')

    def test_texto_como_pedido(self):
        cs = GrupoCuatrimestral.VPS
        now = timezone.now()
        tipo = TipoDocentes.P.name
        EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=cs.name, tipo_docente=tipo,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        self.turno.dificil_de_cubrir = True
        self.turno.save()
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), cs.name, tipo)))

        # no hay más opciones que las esperadas
        opciones_esperadas = {Cuatrimestres.V: 2, Cuatrimestres.P: 5, Cuatrimestres.S: 5}
        for cuatri, esperadas in opciones_esperadas.items():
            for opcion in range(1, esperadas + 1):
                self.assertContains(response, f'opcion{cuatri.name}{opcion}')
                self.assertContains(response, f'peso{cuatri.name}{opcion}')
            self.assertNotContains(response, f'opcion{cuatri.name}{esperadas + 1}')

        # hay una explicación de los pesos
        self.assertContains(response, 'Cuanto mayor es el peso')
        # si un turnoo no necesita docentes no se debe poder elegir
        self.assertNotContains(response, 'disabled')
        self.turno.necesidad_prof = 0
        self.turno.save()
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), cs.name, tipo)))
        self.assertContains(response, 'disabled')

    def test_turnos_con_docentes_distribuidos_van_disabled(self):
        cs = GrupoCuatrimestral.VPS
        now = timezone.now()
        tipo = TipoDocentes.P.name
        EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=cs.name, tipo_docente=tipo,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), cs.name, tipo)))

        self.assertContains(response, 'disabled', count=0)

        Carga.objects.create(turno=self.turno, anno=self.turno.anno, cuatrimestre=self.turno.cuatrimestre,
                             docente=self.docente, cargo=CargoDedicacion.TitExc.name)

        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), cs.name, tipo)))
        # como no es dificil de cubrir, no aparece en las primeras dos opciones
        # y aparece como disabled en las otras tres porque está cubierto
        self.assertContains(response, 'disabled', count=3)

    def test_otros_datos_comentario_con_periodo(self):
        cs = GrupoCuatrimestral.VPS
        now = timezone.now()
        tipo = TipoDocentes.P.name
        EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=cs.name, tipo_docente=tipo,
                                            desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))
        opciones = {}
        for cuatri in cs.name:
            for opcion in range(1, 6):
                turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=cuatri,
                                             numero=1, tipo=TipoTurno.T.name,
                                             necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
                opciones[f'opcion{cuatri}{opcion}'] = turno.id
                opciones[f'peso{cuatri}{opcion}'] = 0

        cargas = {f'cargas{cuatri}': 1 for cuatri in cs.name}
        self.client.post(f'/encuestas/encuesta/{self.anno}/{cs.name}/{TipoDocentes.P.name}',
                         {'docente': self.docente.id,
                          'cargas_declaradas': 1,
                          **opciones,
                          'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                          **cargas,
                          'comentario': 'pero qué corno'},
                         follow=True)
        self.assertEqual(OtrosDatos.objects.filter(docente=self.docente.id).count(), 1)
        od = OtrosDatos.objects.get(docente=self.docente.id)
        self.assertEqual(od.cuatrimestre, cs.name)


class TestPaginas(TestCase):

    def setUp(self):
        self.anno = 2080
        self.cuatrimestre = Cuatrimestres.S
        self.materia = Materia.objects.create(nombre='lacan 1', obligatoriedad=TipoMateria.B.name)
        self.dict_nec = {'necesidad_prof': 0, 'necesidad_jtp': 0, 'necesidad_ay1': 0, 'necesidad_ay2': 0}
        self.turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                          numero=1, tipo=TipoTurno.T.name, **self.dict_nec)
        self.n = Docente.objects.create(na_nombre='nemo', na_apellido='X', telefono='00 0000',
                                        email='nemo@nautilus.org',
                                        cargos=[CargoDedicacion.TitExc.name])

        Usuario.objects.create_user(username='desautorizado', password='123')
        autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        autorizado.user_permissions.add(Permission.objects.get(content_type__app_label='dborrador',
                                                               codename='add_asignacion'))

    def _agrega_preferencias(self):
        now = timezone.now()
        now_mas_delta = now + datetime.timedelta(seconds=10)
        pref1 = PreferenciasDocente.objects.create(docente=self.n, turno=self.turno,
                                                   tipo_docente=TipoDocentes.P.name,
                                                   peso=1, fecha_encuesta=now)
        cargas1 = CargasPedidas.objects.create(docente=self.n, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                               cargas=1, fecha_encuesta=now)
        datos = OtrosDatos.objects.create(docente=self.n, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                          fecha_encuesta=now_mas_delta, comentario='importante comentario',
                                          cargas_declaradas=1)

        pref2 = PreferenciasDocente.objects.create(docente=self.n, turno=self.turno, tipo_docente=TipoDocentes.P.name,
                                                   peso=2, fecha_encuesta=now_mas_delta)
        cargas2 = CargasPedidas.objects.create(docente=self.n, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                               cargas=1,
                                               fecha_encuesta=now_mas_delta)

    def test_ver_resultados_de_encuestas(self):
        self._agrega_preferencias()
        self.client.login(username='autorizado', password='1234')

        response = self.client.get(reverse('encuestas:ver_resultados_de_encuestas',
                                           args=(self.anno, self.cuatrimestre.name)))
        self.assertContains(response, self.n.apellido_nombre)

        response = self.client.get(reverse('encuestas:encuestas_de_un_docente',
                                           args=(self.n.id, self.anno, self.cuatrimestre.name)))
        self.assertContains(response, self.n.nombre)
        self.assertContains(response, str(self.turno), count=2)

    def test_dos_encuestas_no_provocan_excepciones(self):
        self.client.login(username='autorizado', password='1234')
        self._agrega_preferencias()
        primera = PreferenciasDocente.objects.order_by('fecha_encuesta').first()
        primeros_otros_datos = OtrosDatos.objects.create(docente=self.n, anno=self.anno, cuatrimestre=self.cuatrimestre.name,
                                                         fecha_encuesta=primera.fecha_encuesta, comentario='estúpido comentario',
                                                         cargas_declaradas=2)
        response = self.client.get(reverse('encuestas:encuestas_de_un_docente',
                                           args=(self.n.id, self.anno, self.cuatrimestre.name)),
                                   follow=True)


    def test_agregar_habilitacion(self):
        self.client.login(username='autorizado', password='1234')
        now = datetime.datetime(2101, 2, 3, 4, 5, 0, tzinfo=datetime.timezone.utc)
        cuatrimestres = f'{Cuatrimestres.P.name}'
        tipo_docente = f'{TipoDocentes.P.name}'
        post = {'anno': self.anno, 'cuatrimestres': cuatrimestres,
                'tipo_docente': tipo_docente,
                'desde': f'{now:%d/%m/%Y %H:%M}',
                'hasta': f'{now:%d/%m/%Y %H:%M}'
                }
        response = self.client.post(reverse('encuestas:agregar_habilitacion'), post, follow=True)
        self.assertEqual(EncuestasHabilitadas.objects.count(), 1)
        encuesta = EncuestasHabilitadas.objects.first()
        self.assertEqual(encuesta.anno, self.anno)
        self.assertEqual(encuesta.cuatrimestres, cuatrimestres)
        self.assertEqual(encuesta.tipo_docente, tipo_docente)
        self.assertAlmostEqual(encuesta.desde, now, delta=datetime.timedelta(days=1))
        self.assertAlmostEqual(encuesta.hasta, now, delta=datetime.timedelta(days=1))

    def test_borrar_habilitacion(self):
        self.client.login(username='autorizado', password='1234')
        fecha = datetime.datetime(2101, 2, 3, 4, 5, 0, tzinfo=datetime.timezone.utc)
        habilitacion = EncuestasHabilitadas.objects.create(anno=2101, cuatrimestres=Cuatrimestres.P.name,
                                                           tipo_docente=TipoDocentes.P.name,
                                                           desde=fecha, hasta=fecha)
        response = self.client.get(reverse('encuestas:borrar_habilitacion', args=(habilitacion.id,)), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EncuestasHabilitadas.objects.count(), 0)
