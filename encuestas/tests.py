from django.test import TestCase, tag
from django.test.utils import setup_test_environment
from django.urls import reverse

from materias.models import Docente, Cargos, Materia, Turno, TipoTurno, TipoMateria, Cuatrimestres
from .models import PreferenciasDocente
from .views import checkear_y_salvar


class TestEncuesta(TestCase):

    def setUp(self):
        self.docente = Docente.objects.create(nombre='juan', email='mail@nada.org',
                                              telefono='1234', cargo=Cargos.JTP, cargas=1)
        self.materia = Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B)
        self.turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                          numero=1, tipo=TipoTurno.A.name, necesidades='1,0,0')

    def test_sin_docente(self):
        datos = {}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_no_existe(self):
        docente_inexistente_id = str(self.docente.id + 1)
        datos = {'docente': docente_inexistente_id}
        with self.assertRaises(Docente.DoesNotExist):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_sin_opciones(self):
        datos = {'docente': self.docente.id}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_turno_no_existe(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            datos['opcion{}'.format(opcion)] = str(self.turno.id + 1)
            datos['peso{}'.format(opcion)] = str(opcion)
        with self.assertRaises(Turno.DoesNotExist):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_y_opciones_vacias(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            datos['opcion{}'.format(opcion)] = ''
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 0)

    def test_docente_y_opciones_con_sentido(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 6):
            turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name, necesidades='1,0,0')
            datos['opcion{}'.format(opcion)] = turno.id
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 5)

    def test_algunas_opciones_vacias(self):
        datos = {'docente': self.docente.id}
        for opcion in range(1, 3):
            turno = Turno.objects.create(materia=self.materia, anno=2100, cuatrimestre=Cuatrimestres.P.name,
                                         numero=1, tipo=TipoTurno.T.name, necesidades='1,0,0')
            datos['opcion{}'.format(opcion)] = turno.id
            datos['peso{}'.format(opcion)] = str(opcion)
        for opcion in range(3, 6):
            datos['opcion{}'.format(opcion)] = ''
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)
        self.assertEqual(len(PreferenciasDocente.objects.all()), 2)

    def test_titulo_correcto(self):
        response = self.client.get(reverse('encuestas:encuesta', args=('2100', Cuatrimestres.P.name, 'J')))
        self.assertEqual(response.request['PATH_INFO'], '/encuestas/encuesta/2100/P/J')
        self.assertContains(response, 'cuatrimestre 1 de 2100')

    def test_turnos_correctos(self):
        response = self.client.get(reverse('encuestas:encuesta', args=('2100', Cuatrimestres.P.name, 'J')))
        self.assertContains(response, self.turno.materia.nombre)

    def test_turnos_otros_cuatrimestres(self):
        response = self.client.get(reverse('encuestas:encuesta', args=('2100', Cuatrimestres.S.name, 'J')))
        self.assertNotContains(response, self.turno.materia.nombre)

    def test_turnos_otros_annos(self):
        response = self.client.get(reverse('encuestas:encuesta', args=('2101', Cuatrimestres.P.name, 'J')))
        self.assertNotContains(response, self.turno.materia.nombre)
