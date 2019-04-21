from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Permission

from .models import Usuario

class Usuarios(TestCase):

    def setUp(self):
        self.desautorizado = Usuario.objects.create_user(username='desau', password='1234', )
        self.autorizado = Usuario.objects.create_user(username='auto', password='1234')
        permiso = Permission.objects.get(codename='add_asignacion')
        self.autorizado.user_permissions.add(permiso)

    def test_puede_distribuir_deslogueado(self):
        client = Client()
        response = client.get(reverse('dborrador:distribuir'))
        self.assertEqual(response.status_code, 302)

    def test_puede_distribuir_logueado_autorizado(self):
        client = Client()
        client.login(username='auto', password='1234')
        response = client.get(reverse('dborrador:distribuir'))
        self.assertEqual(response.status_code, 200)

    def test_puede_distribuir_logueado_desautorizado(self):
        client = Client()
        client.login(username='desau', password='1234')
        response = client.get(reverse('dborrador:distribuir'))
        self.assertEqual(response.status_code, 302)
