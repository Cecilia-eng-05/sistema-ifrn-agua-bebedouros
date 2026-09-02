import datetime

from django.db import IntegrityError
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaModelTests(TestCase):
    def test_defaults_to_rascunho(self):
        c = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.assertEqual(c.status, Coleta.RASCUNHO)
        self.assertFalse(c.publicada)

    def test_data_is_unique(self):
        Coleta.objects.create(data=datetime.date(2026, 9, 1))
        with self.assertRaises(IntegrityError):
            Coleta.objects.create(data=datetime.date(2026, 9, 1))
