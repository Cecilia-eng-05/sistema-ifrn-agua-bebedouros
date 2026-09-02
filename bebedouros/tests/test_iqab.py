import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from bebedouros import iqab
from bebedouros.models import Bebedouro, Coleta, Resultado


class ClassificarTests(SimpleTestCase):
    def test_faixas(self):
        casos = [
            (Decimal("100"), "Excelente"),
            (Decimal("80"), "Excelente"),
            (Decimal("79.9"), "Boa"),
            (Decimal("60"), "Boa"),
            (Decimal("59"), "Regular"),
            (Decimal("40"), "Regular"),
            (Decimal("39"), "Ruim"),
            (Decimal("20"), "Ruim"),
            (Decimal("19"), "Crítica"),
            (Decimal("0"), "Crítica"),
        ]
        for nota, esperado in casos:
            self.assertEqual(iqab.classificar(nota), esperado, nota)

    def test_none(self):
        self.assertEqual(iqab.classificar(None), "")


class CalcularTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_linha_vazia_sem_dados(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.SEM_DADOS)
        self.assertIsNone(d["iqab"])

    def test_fora_de_operacao_sem_dados(self):
        r = Resultado.objects.create(
            coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7"), fora_de_operacao=True
        )
        self.assertEqual(iqab.calcular(r)["status"], iqab.SEM_DADOS)

    def test_com_dados_fica_pendente(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.2"))
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.PENDENTE)
        self.assertEqual(d["versao"], iqab.VERSAO_METODOLOGIA)


class RecalculoAoSalvarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_salvar_grade_grava_status_e_versao(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-ph": "7,2"},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.iqab_status, iqab.PENDENTE)
        self.assertEqual(r.metodologia_versao, iqab.VERSAO_METODOLOGIA)
        self.assertEqual(r.iqab_texto(), "pendente")

    def test_linha_em_branco_fica_sem_dados(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-observacao": ""},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.iqab_status, iqab.SEM_DADOS)
        self.assertEqual(r.iqab_texto(), "—")

    def test_grade_mostra_coluna_iqab(self):
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertContains(response, "IQA-B")
