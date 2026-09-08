import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class ApagarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.b1 = Bebedouro.objects.create(numero=1)
        self.alvo = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.outra = Coleta.objects.create(data=datetime.date(2026, 8, 1))
        Resultado.objects.create(coleta=self.alvo, bebedouro=self.b1, ph="7.2")

    def test_get_shows_confirmation(self):
        response = self.client.get(f"/coletas/{self.alvo.pk}/apagar/")
        self.assertContains(response, "todos os bebedouros")

    def test_post_deletes_collection_and_its_results_only(self):
        response = self.client.post(f"/coletas/{self.alvo.pk}/apagar/", follow=True)
        self.assertRedirects(response, "/coletas/")
        self.assertFalse(Coleta.objects.filter(pk=self.alvo.pk).exists())
        self.assertEqual(Resultado.objects.count(), 0)
        self.assertTrue(Coleta.objects.filter(pk=self.outra.pk).exists())
