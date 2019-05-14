from django.test import TestCase
from django.test.utils import setup_test_environment
from django.urls import reverse
from django.forms import ValidationError

import re

from materias.models import (Docente, Cargos, Materia, Turno, TipoTurno, TipoMateria,
                             CargoDedicacion, Cuatrimestres)
from materias.misc import TipoDocentes
from .models import PreferenciasDocente, OtrosDatos
from .views import checkear_y_salvar


class TestEncuesta(TestCase):

    def setUp(self):
        self.anno = 2100
        self.docente = Docente.objects.create(nombre='juan', email='mail@nada.org',
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
        self.otros_datos = {'telefono': '+54911 1234-5678', 'email': 'nadie@gmail.com', 'cargas': 1}

    def test_sin_docente(self):
        datos = {}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos)

    def test_docente_no_existe(self):
        docente_inexistente_id = str(self.docente.id + 1)
        datos = {'docente': docente_inexistente_id}
        with self.assertRaises(Docente.DoesNotExist):
            checkear_y_salvar(datos)

    def test_docente_sin_opciones(self):
        datos = {'docente': self.docente.id}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos)

    def test_turno_no_existe(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            datos['opcion{}'.format(opcion)] = str(self.turno.id + opcion)
            datos['peso{}'.format(opcion)] = str(opcion)
        with self.assertRaises(Turno.DoesNotExist):
            checkear_y_salvar(datos)

    def test_docente_y_opciones_vacias(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            datos['opcion{}'.format(opcion)] = ''
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 0)

    def test_docente_y_opciones_con_sentido(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            datos['opcion{}'.format(opcion)] = turno.id
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 5)

    def test_algunas_opciones_vacias(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 3):
            turno = Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
            datos['opcion{}'.format(opcion)] = turno.id
            datos['peso{}'.format(opcion)] = str(opcion)
        for opcion in range(3, 6):
            datos['opcion{}'.format(opcion)] = ''
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 2)

    def test_titulo_correcto(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, 'J')))
        self.assertEqual(response.request['PATH_INFO'], f'/encuestas/encuesta/{self.anno}/P/J')
        self.assertContains(response, f'cuatrimestre {Cuatrimestres.P.value} de {self.anno}')

    def test_turnos_correctos(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.P.name, 'J')))
        self.assertContains(response, self.turno.materia.nombre)

    def test_turnos_otros_cuatrimestres(self):
        response = self.client.get(reverse('encuestas:encuesta', args=(str(self.anno), Cuatrimestres.S.name, 'J')))
        self.assertNotContains(response, self.turno.materia.nombre)

    def test_turnos_otros_annos(self):
        response = self.client.get(reverse('encuestas:encuesta',
                                           args=(str(self.anno + 1), Cuatrimestres.P.name, 'J')))
        self.assertNotContains(response, self.turno.materia.nombre)

    def test_turnos_repetidos(self):
        datos = {'docente': self.docente.id}
        turnos = [Turno.objects.create(materia=self.materia, anno=self.anno, cuatrimestre=Cuatrimestres.P.name,
                                          numero=t, tipo=TipoTurno.T.name,
                                         necesidad_prof=1, necesidad_jtp=0, necesidad_ay1=0, necesidad_ay2=0)
                  for t in range(1, 6)
                  ]

        for opcion, turno in enumerate(turnos, 1):
            datos[f'opcion{opcion}'] = turno.id
            datos[f'peso{opcion}'] = str(1)
        # repetimos la opcion 2
        datos['opcion2'] = turnos[0].id
        with self.assertRaises(ValidationError):
            checkear_y_salvar(datos)

    def test_encuesta_distingue_turnos_dificiles(self):
        '''Chequeamos que el turno dificil aparece 5 veces en la encuesta y el facil 3'''
        response = self.client.get(f'/encuestas/encuesta/{self.anno}/{Cuatrimestres.P.name}/{TipoDocentes.P.name}')
        opcion_reg_facil = re.compile('^.*<option value.*Teórico-Práctica 1', re.MULTILINE)
        opcion_reg_dificil = re.compile('^.*<option value.*Teórica 2', re.MULTILINE)
        self.assertEqual(len(opcion_reg_facil.findall(response.content.decode())), 3)
        self.assertEqual(len(opcion_reg_dificil.findall(response.content.decode())), 5)

    def test_encuesta_salva_otros_datos(self):
        opciones = {'opcion1': self.turno.id, 'peso1': 1}
        for o in range(2, 6):
            opciones[f'opcion{o}'] = ''
            opciones[f'peso{o}'] = 0
        response = self.client.post(f'/encuestas/encuesta/{self.anno}/{Cuatrimestres.P.name}/{TipoDocentes.P.name}',
                                    {'docente': self.docente.id,
                                     **opciones,
                                     'telefono': '+54911 1234-5678', 'email': 'juan@dm.uba.ar',
                                     'cargas': 1, 'comentario': 'pero qué corno'},
                                    follow=True)
        self.assertEqual(OtrosDatos.objects.count(), 1)
        od = OtrosDatos.objects.first()
        self.assertEqual(od.comentario, 'pero qué corno')
        self.assertEqual(od.cargas, 1)
        self.assertEqual(od.telefono,  '+54911 1234-5678')
        self.assertEqual(od.email,  'juan@dm.uba.ar')
