import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class LancamentoPostTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def _post(self, **campos):
        dados = {f"b{self.b1.id}-{k}": v for k, v in campos.items()}
        return self.client.post(f"/coletas/{self.coleta.pk}/lancamento/", dados, follow=True)

    def test_saves_values_and_keeps_draft(self):
        self._post(ph="7,20", coliformes_totais="AUSENTE")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("7.20"))
        self.assertEqual(r.coliformes_totais, "AUSENTE")
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)

    def test_blank_row_creates_empty_result(self):
        self._post()
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertTrue(r.esta_vazio())

    def test_turbidez_below_limit_is_parsed(self):
        self._post(turbidez="<0,751")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.turbidez_valor, Decimal("0.751"))
        self.assertTrue(r.turbidez_abaixo_limite)

    def test_strange_ph_saves_with_warning(self):
        response = self._post(ph="20")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("20.00"))
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("pH" in m for m in mensagens))
