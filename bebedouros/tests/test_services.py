import datetime

from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import linhas_faltantes


class LinhasFaltantesTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)
        self.b3 = Bebedouro.objects.create(
            numero=3, desativado_em=datetime.date(2026, 1, 1)
        )

    def test_missing_when_no_result_or_empty_result(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        self.assertEqual(linhas_faltantes(self.coleta), ["B2"])

    def test_fora_de_operacao_is_not_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, fora_de_operacao=True)
        self.assertEqual(linhas_faltantes(self.coleta), [])

    def test_inactive_fountain_never_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.assertNotIn("B3", linhas_faltantes(self.coleta))
