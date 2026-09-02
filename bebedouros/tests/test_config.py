from django.test import SimpleTestCase

import dj_database_url


class ConfigTests(SimpleTestCase):
    def test_database_url_parses_to_postgres(self):
        cfg = dj_database_url.parse("postgres://u:p@host:5432/dbname")
        self.assertIn("postgresql", cfg["ENGINE"])

    def test_whitenoise_is_installed(self):
        from django.conf import settings

        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE
        )
