import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, TrocaFiltro


class LancamentoTrocaFiltroTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def _post(self, **campos):
        dados = {f"b{self.b1.id}-{k}": v for k, v in campos.items()}
        return self.client.post(f"/coletas/{self.coleta.pk}/lancamento/", dados, follow=True)

    def test_preencher_data_cria_troca(self):
        self._post(troca_filtro="2026-09-01")
        troca = TrocaFiltro.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(troca.data_troca, datetime.date(2026, 9, 1))

    def test_deixar_em_branco_nao_cria_troca(self):
        self._post(ph="7,20")
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_apagar_data_remove_troca(self):
        self._post(troca_filtro="2026-09-01")
        self._post(troca_filtro="")
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_relancar_a_grade_sem_mudar_nao_duplica(self):
        self._post(troca_filtro="2026-09-01")
        self._post(troca_filtro="2026-09-01")
        self.assertEqual(TrocaFiltro.objects.count(), 1)

    def test_grade_mostra_troca_ja_lancada(self):
        self._post(troca_filtro="2026-09-01")
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertContains(response, "2026-09-01")
