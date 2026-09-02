from decimal import Decimal

from django.test import SimpleTestCase

from bebedouros.forms import parse_turbidez


class ParseTurbidezTests(SimpleTestCase):
    def test_blank(self):
        self.assertEqual(parse_turbidez(""), (None, False))

    def test_plain_number_with_comma(self):
        self.assertEqual(parse_turbidez("0,751"), (Decimal("0.751"), False))

    def test_below_detection_limit(self):
        self.assertEqual(parse_turbidez("<0,751"), (Decimal("0.751"), True))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_turbidez("abc")
