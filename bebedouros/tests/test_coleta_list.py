import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaListTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")

    def test_lists_collections_newest_first(self):
        Coleta.objects.create(data=datetime.date(2026, 8, 1))
        Coleta.objects.create(data=datetime.date(2026, 9, 1))
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        corpo = response.content.decode()
        self.assertLess(corpo.index("01/09/2026"), corpo.index("01/08/2026"))
        self.assertIn("Rascunho", corpo)
