import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta


class LancamentoGetTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.ativo = Bebedouro.objects.create(numero=1, local="Mesas verdes")
        self.inativo = Bebedouro.objects.create(
            numero=2, local="Piscinas", desativado_em=datetime.date(2026, 1, 1)
        )

    def test_grid_shows_editable_row_for_active_and_locked_for_inactive(self):
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertEqual(response.status_code, 200)
        linhas = response.context["linhas"]
        por_codigo = {l["bebedouro"].codigo: l for l in linhas}
        self.assertIsNotNone(por_codigo["B1"]["form"])
        self.assertFalse(por_codigo["B1"]["bloqueada"])
        self.assertIsNone(por_codigo["B2"]["form"])
        self.assertTrue(por_codigo["B2"]["bloqueada"])
        self.assertContains(response, "Fora de operação (bebedouro desativado)")
