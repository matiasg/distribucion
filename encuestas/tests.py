from django.test import TestCase
from django.test.utils import setup_test_environment
from django.utils import timezone
from django.urls import reverse
from django.forms import ValidationError

import re
import datetime

from materias.models import (Docente, Carga, Cargos, Materia, Turno, TipoTurno, TipoMateria,
                             CargoDedicacion, Cuatrimestres)
from materias.misc import TipoDocentes
from .models import PreferenciasDocente, OtrosDatos, CargasPedidas, EncuestasHabilitadas
from .views import checkear_y_salvar


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
                            f'cargas{Cuatrimestres.P.name}': 1}
        now = timezone.now()
        for tipo in TipoDocentes:
            EncuestasHabilitadas.objects.create(anno=self.anno, cuatrimestres=Cuatrimestres.P.name, tipo_docente=tipo.name,
                                                desde=now-datetime.timedelta(minutes=1), hasta=now+datetime.timedelta(minutes=1))

    def test_pocos_turnos(self):
        datos = self.otros_datos
        datos['docente'] = self.docente.id
        datos[f'opcion{Cuatrimestres.P.name}1'] = str(self.turno.id)
        datos[f'peso{Cuatrimestres.P.name}1'] = 2
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, f'{Cuatrimestres.P.name}')

    def test_sin_docente(self):
        datos = self.otros_datos
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)

    def test_docente_no_existe(self):
        docente_inexistente_id = str(self.docente.id + 1)
        datos = {'docente': docente_inexistente_id, **self.otros_datos}
        with self.assertRaises(Docente.DoesNotExist):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)

    def test_docente_sin_opciones(self):
        datos = {'docente': self.docente.id}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)

    def test_turno_no_existe(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        c = Cuatrimestres.P.name
        for opcion in range(1, 6):
            datos[f'opcion{c}{opcion}'] = str(self.turno.id + opcion)
            datos[f'peso{c}{opcion}'] = str(opcion)
        with self.assertRaises(Turno.DoesNotExist):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)

    def test_docente_y_opciones_vacias(self):
        datos = {'docente': self.docente.id, **self.otros_datos}
        c = Cuatrimestres.P.name
        for opcion in range(1, 6):
            datos[f'opcion{c}{opcion}'] = '-1'
            datos[f'peso{c}{opcion}'] = str(opcion)
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)
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
        checkear_y_salvar(datos, self.anno, c)
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
            checkear_y_salvar(datos, self.anno, Cuatrimestres.P.name)

    def test_titulo_correcto(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, TipoDocentes.J.name)))
        self.assertEqual(response.request['PATH_INFO'], f'/encuestas/encuesta/{self.anno}/P/J')
        self.assertTrue(re.search('Preferencias para el\s*primer cuatrimestre', response.content.decode(), re.DOTALL))

    def test_turnos_correctos(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, TipoDocentes.J.name)))
        self.assertContains(response, self.turno.materia.nombre)

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
            checkear_y_salvar(datos, self.anno, c)

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
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     f'cargas{c}': 1, 'comentario': 'pero qué corno'},
                                    follow=True)
        self.assertEqual(OtrosDatos.objects.count(), 1)
        od = OtrosDatos.objects.first()
        self.assertEqual(od.comentario, 'pero qué corno')
        self.assertEqual(od.telefono,  '+54911 1234-5678')
        self.assertEqual(od.email,  'juan@dm.uba.ar')

        cp = CargasPedidas.objects.get(anno=self.anno, cuatrimestre=c, docente=self.docente)
        self.assertEqual(cp.cargas, 1)

    def test_orden_docentes(self):
        for docente in [5, 1, 3, 8, 9, 6, 0, 7, 2, 4]:
            d = Docente.objects.create(na_nombre=f'doc{docente}', na_apellido='X', email='mail@nada.org', telefono='1234',
                                   cargos=[CargoDedicacion.JTPSmx.name])
            Carga.objects.create(docente=d, cargo=CargoDedicacion.JTPSmx.name, anno=self.anno, cuatrimestre=Cuatrimestres.P.name)
        response = self.client.get(f'/encuestas/encuesta/{self.anno}/{Cuatrimestres.P.name}/{TipoDocentes.J.name}')

        docentes_en_desplegable = re.findall('>(doc[0-9]) X<', response.content.decode())
        self.assertEqual(docentes_en_desplegable, [f'doc{d}' for d in range(10)])

    def test_orden_materias_y_turnos(self):
        desorden = [4, 1, 3, 5, 2]
        orden = sorted(desorden)
        anno = 2107

        for materia in desorden:
            m = Materia.objects.create(nombre=f'materia{materia}', obligatoriedad=TipoMateria.B.name)
            for turno in desorden:
                Turno.objects.create(materia=m, anno=anno, cuatrimestre=Cuatrimestres.P.name,
                                     numero=turno, tipo=TipoTurno.T.name,
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
                                 numero=1, tipo=TipoTurno.T.name,
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

    def test_encuesta_no_habilitada(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(2100, 'VPS', 'P')), follow=True)
        self.assertEqual(response.status_code, 403)
