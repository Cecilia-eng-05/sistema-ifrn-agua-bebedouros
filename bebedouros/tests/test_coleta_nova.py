import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaNovaTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")

    def test_creates_collection_and_redirects_to_grid(self):
        response = self.client.post("/coletas/nova/", {"data": "2026-09-15"})
        coleta = Coleta.objects.get()
        self.assertEqual(coleta.data, datetime.date(2026, 9, 15))
        self.assertRedirects(response, f"/coletas/{coleta.pk}/lancamento/")

    def test_duplicate_date_is_rejected_with_message(self):
        Coleta.objects.create(data=datetime.date(2026, 9, 15))
        response = self.client.post("/coletas/nova/", {"data": "2026-09-15"}, follow=True)
        self.assertEqual(Coleta.objects.count(), 1)
        self.assertContains(response, "Já existe uma coleta")
