import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class EditarPublicadaTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        self.b1 = Bebedouro.objects.create(numero=1)
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.20"))

    def test_correcting_published_value_persists_and_keeps_status(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-ph": "6,90"},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("6.90"))
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
