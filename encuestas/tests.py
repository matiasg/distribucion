from django.test import TestCase
from django.test.utils import setup_test_environment

from materias.models import Docente, Cargos, Materia, TipoMateria, Cuatrimestres
from .views import checkear_y_salvar


class TestEncuesta(TestCase):

    def setUp(self):
        Docente.objects.create(nombre='juan', email='mail@nada.org', telefono='1234', cargo=Cargos.JTP, cargas=1)
        Materia.objects.create(nombre='epistemologia', obligatoriedad=TipoMateria.B)
        self.docente_id = str(Docente.objects.first().id)
        self.materia_id = str(Materia.objects.first().id)

    def test_sin_docente(self):
        datos = {}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_no_existe(self):
        docente_inexistente_id = str(int(self.docente_id) + 1)
        datos = {'docente': docente_inexistente_id}
        with self.assertRaises(Docente.DoesNotExist):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_sin_opciones(self):
        datos = {'docente': self.docente_id}
        with self.assertRaises(KeyError):
            checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)

    def test_docente_y_opciones_vacias(self):
        datos = {'docente': self.docente_id}
        for opcion in range(1, 6):
            datos['opcion{}'.format(opcion)] = ''
            datos['peso{}'.format(opcion)] = str(opcion)
        checkear_y_salvar(datos, 2100, Cuatrimestres.P.name)


