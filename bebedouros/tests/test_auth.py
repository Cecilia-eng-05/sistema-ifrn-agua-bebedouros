from django.test import TestCase
from django.contrib.auth.models import User


class AuthGateTests(TestCase):
    def test_coletas_redirects_anonymous_to_login(self):
        response = self.client.get("/coletas/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/entrar/", response["Location"])

    def test_login_page_shows_system_title(self):
        response = self.client.get("/entrar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sistema de Monitoramento e Gestão da Água")

    def test_coletas_ok_when_logged_in(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        response = self.client.get("/coletas/")
        self.assertEqual(response.status_code, 200)

    def test_login_redirects_to_inicio(self):
        User.objects.create_user("nucleo", password="segredo")
        response = self.client.post(
            "/entrar/", {"username": "nucleo", "password": "segredo"}
        )
        self.assertRedirects(response, "/inicio/")

    def test_mapa_nao_exige_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
