import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado, formatar_turbidez


class ResultadoModelTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_blank_result_is_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        self.assertTrue(r.esta_vazio())

    def test_any_value_makes_it_not_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.20"))
        self.assertFalse(r.esta_vazio())

    def test_fora_de_operacao_alone_still_counts_as_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, fora_de_operacao=True)
        self.assertTrue(r.esta_vazio())

    def test_one_result_per_bebedouro_per_coleta(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)

    def test_deleting_coleta_deletes_results(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        self.coleta.delete()
        self.assertEqual(Resultado.objects.count(), 0)


class FormatarTurbidezTests(TestCase):
    def test_sem_valor_e_sem_marcador(self):
        self.assertEqual(formatar_turbidez(None, False), "")

    def test_valor_normal(self):
        self.assertEqual(formatar_turbidez(Decimal("0.751"), False), "0,751")

    def test_abaixo_do_limite_com_valor(self):
        self.assertEqual(formatar_turbidez(Decimal("0.751"), True), "<0,751")

    def test_abaixo_do_limite_sem_valor(self):
        self.assertEqual(formatar_turbidez(None, True), "<")
