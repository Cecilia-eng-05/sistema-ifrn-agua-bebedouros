from django.test import TestCase
from django.core.management import call_command

from bebedouros.models import Bebedouro


class BebedouroTests(TestCase):
    def test_codigo_property(self):
        b = Bebedouro.objects.create(numero=7, local="Piscinas")
        self.assertEqual(b.codigo, "B7")
        self.assertEqual(str(b), "B7")

    def test_ordering_is_numeric_not_lexical(self):
        Bebedouro.objects.create(numero=10)
        Bebedouro.objects.create(numero=2)
        codigos = [b.codigo for b in Bebedouro.objects.all()]
        self.assertEqual(codigos, ["B2", "B10"])

    def test_seed_creates_15_and_is_idempotent(self):
        call_command("seed_bebedouros")
        self.assertEqual(Bebedouro.objects.count(), 15)
        call_command("seed_bebedouros")
        self.assertEqual(Bebedouro.objects.count(), 15)

    def test_seed_fills_real_locals(self):
        call_command("seed_bebedouros")
        self.assertEqual(Bebedouro.objects.get(numero=1).local, "Mesas verdes")
        self.assertEqual(Bebedouro.objects.get(numero=15).local, "DIAREN 2")
