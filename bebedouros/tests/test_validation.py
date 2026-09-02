from decimal import Decimal

from django.test import SimpleTestCase

from bebedouros.validation import avisos_para_resultado


class AvisosTests(SimpleTestCase):
    def test_ph_out_of_range_warns(self):
        avisos = avisos_para_resultado({"ph": Decimal("20")})
        self.assertTrue(any("pH" in a for a in avisos))

    def test_negative_value_warns(self):
        avisos = avisos_para_resultado({"cloro": Decimal("-1")})
        self.assertTrue(any("negativo" in a for a in avisos))

    def test_normal_values_no_warnings(self):
        self.assertEqual(
            avisos_para_resultado({"ph": Decimal("7.2"), "cloro": Decimal("0.8")}),
            [],
        )
