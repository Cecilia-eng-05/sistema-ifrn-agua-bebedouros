import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado, TrocaFiltro


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

    def test_filtro_incompativel_com_troca_registrada_avisa(self):
        # Troca em janeiro; esta coleta é de setembro (bem mais de 6
        # meses depois) — deveria estar "vencido", mas o bolsista marca
        # "dentro da validade".
        troca_coleta = Coleta.objects.create(
            data=datetime.date(2026, 1, 1), status=Coleta.PUBLICADO
        )
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 1, 1)
        )
        response = self._post(filtro="dentro")
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("esperado aqui seria" in m for m in mensagens))

    def test_filtro_compativel_nao_avisa(self):
        troca_coleta = Coleta.objects.create(
            data=datetime.date(2026, 8, 20), status=Coleta.PUBLICADO
        )
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 8, 20)
        )
        response = self._post(filtro="dentro")  # 12 dias depois — dentro da validade
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertFalse(any("esperado aqui seria" in m for m in mensagens))

    def test_sem_troca_registrada_nao_avisa(self):
        response = self._post(filtro="vencido")
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertFalse(any("esperado aqui seria" in m for m in mensagens))

    def test_troca_lancada_na_mesma_grade_ja_entra_na_comparacao(self):
        # O bolsista troca o filtro nesta mesma coleta (12 dias antes —
        # bem dentro da validade), mas marca "vencido" por engano. O
        # aviso deve usar a troca recém-lançada nesta mesma gravação,
        # não só as que já existiam antes.
        response = self._post(filtro="vencido", troca_filtro="2026-08-20")
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("esperado aqui seria" in m for m in mensagens))
