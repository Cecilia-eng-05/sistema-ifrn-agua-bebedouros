import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class PublicarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)

    def test_publish_blocked_and_lists_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        response = self.client.post(f"/coletas/{self.coleta.pk}/publicar/", follow=True)
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)
        self.assertContains(response, "B2")

    def test_publish_with_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        response = self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/", {"confirmar": "1"}, follow=True
        )
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
        self.assertRedirects(response, "/")

    def test_publish_complete_without_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.client.post(f"/coletas/{self.coleta.pk}/publicar/")
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
