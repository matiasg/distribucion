from django.test import TestCase, Client

import re

class TestPreparar(TestCase):

    def test_no_falla_si_no_hay_preferencias(self):
        c = Client()
        response = c.get('/dborrador/preparar')
        self.assertEqual(response.status_code, 200)

        response = c.post('/dborrador/preparar', {'anno': '2100', 'cuatrimestre': 'P', 'tipo': 'P'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertTrue(re.search('Copiadas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se copiaron 0 preferencias')
        self.assertTrue(re.search('Borradas:[^0-9]*0[^0-9]*\n', content),
                        'La página deberia decir que se borraron 0 preferencias')
        self.assertTrue('Preferencias copiadas' in response.content.decode(),
                        'La página debería decir "Preferencias copiadas" y dice {}'.format(
                            response.content.decode()))

    def test_copia_docentes(self):
        pass
