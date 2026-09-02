import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import linhas_faltantes

DESATIVACAO = datetime.date(2026, 6, 1)


class DesativacaoComDataTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b7 = Bebedouro.objects.create(numero=7, desativado_em=DESATIVACAO)

    def test_ativo_em(self):
        self.assertTrue(self.b7.ativo_em(datetime.date(2026, 5, 31)))
        self.assertFalse(self.b7.ativo_em(DESATIVACAO))
        self.assertFalse(self.b7.ativo_em(datetime.date(2026, 9, 1)))
        self.assertTrue(self.b1.ativo_em(datetime.date(2026, 9, 1)))

    def test_past_collection_keeps_bebedouro_editable_with_history(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 3, 15))
        Resultado.objects.create(coleta=antiga, bebedouro=self.b7, ph=Decimal("7.10"))
        response = self.client.get(f"/coletas/{antiga.pk}/lancamento/")
        linha = {l["bebedouro"].codigo: l for l in response.context["linhas"]}["B7"]
        self.assertFalse(linha["bloqueada"])
        self.assertIsNotNone(linha["form"])
        self.assertEqual(linha["form"].initial["ph"], Decimal("7.10"))

    def test_later_collection_locks_the_bebedouro(self):
        nova = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        response = self.client.get(f"/coletas/{nova.pk}/lancamento/")
        linha = {l["bebedouro"].codigo: l for l in response.context["linhas"]}["B7"]
        self.assertTrue(linha["bloqueada"])
        self.assertIsNone(linha["form"])

    def test_missing_check_respects_the_deactivation_date(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 3, 15))
        nova = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, ph="7")
        Resultado.objects.create(coleta=nova, bebedouro=self.b1, ph="7")
        self.assertIn("B7", linhas_faltantes(antiga))
        self.assertNotIn("B7", linhas_faltantes(nova))
