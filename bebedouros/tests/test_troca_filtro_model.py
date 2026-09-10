import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, TrocaFiltro


class TrocaFiltroModelTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))

    def test_cria_troca_filtro(self):
        troca = TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        self.assertEqual(troca.bebedouro, self.b1)
        self.assertEqual(str(troca), "B1 — troca em 01/09/2026")

    def test_uma_troca_por_bebedouro_por_coleta(self):
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrocaFiltro.objects.create(
                bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 2)
            )

    def test_apagar_coleta_apaga_trocas(self):
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        self.coleta.delete()
        self.assertEqual(TrocaFiltro.objects.count(), 0)
