from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Permission

from .models import Usuario

class Usuarios(TestCase):

    def setUp(self):
        self.desautorizado = Usuario.objects.create_user(username='desautorizado', password='1234', )
        self.autorizado = Usuario.objects.create_user(username='autorizado', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)
        self.args = (2100, 'P', 'P', 1, 0)

    def test_puede_distribuir_deslogueado(self):
        client = Client()
        response = client.get(reverse('dborrador:distribuir', args=self.args), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/dborrador/distribuir/2100/P/P/1/0', 302))

    def test_puede_distribuir_logueado_autorizado(self):
        client = Client()
        client.login(username='autorizado', password='1234')
        response = client.get(reverse('dborrador:distribuir', args=self.args), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][0], '/dborrador/distribucion/2100/P/2/0')

    def test_puede_distribuir_logueado_desautorizado(self):
        client = Client()
        client.login(username='desautorizado', password='1234')
        response = client.get(reverse('dborrador:distribuir', args=self.args), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0], ('/admin/login?next=/dborrador/distribuir/2100/P/P/1/0', 302))
        self.assertEqual(response.redirect_chain[-1], ('/admin/', 302))
