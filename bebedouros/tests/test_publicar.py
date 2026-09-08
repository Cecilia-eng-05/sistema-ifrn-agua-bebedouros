import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class PublicarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)

    def test_publish_blocked_and_lists_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        # Simula a grade real: o campo de B1 volta preenchido (não foi mexido);
        # B2 nunca teve dado, então volta em branco.
        response = self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/",
            {f"b{self.b1.id}-ph": "7.2"},
            follow=True,
        )
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)
        self.assertContains(response, "B2")

    def test_publish_with_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        response = self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/", {"confirmar": "1"}, follow=True
        )
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
        self.assertRedirects(response, "/inicio/")

    def test_publish_complete_without_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/",
            {f"b{self.b1.id}-ph": "7.2", f"b{self.b2.id}-ph": "7.0"},
        )
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)

    def test_publish_saves_an_edit_made_without_clicking_salvar_rascunho_first(self):
        """O botão Publicar salva a grade antes de checar/publicar, para não
        descartar em silêncio uma edição feita direto nele."""
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/",
            # B1 chega em branco (apagado na tela); B2 continua preenchido.
            {f"b{self.b2.id}-ph": "7.0"},
            follow=True,
        )
        r1 = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertTrue(r1.esta_vazio())
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)

    def test_confirming_publish_does_not_touch_the_grade_again(self):
        """A re-submissão da tela de confirmação só tem 'confirmar=1' — não
        pode ser tratada como uma grade em branco."""
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/", {"confirmar": "1"}
        )
        r1 = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertFalse(r1.esta_vazio())
        self.assertEqual(str(r1.ph), "7.20")

    def test_publicar_grava_a_data_da_publicacao(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.assertIsNone(self.coleta.publicada_em)
        self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/",
            {f"b{self.b1.id}-ph": "7.2", f"b{self.b2.id}-ph": "7.0"},
        )
        self.coleta.refresh_from_db()
        self.assertIsNotNone(self.coleta.publicada_em)

    def test_rascunho_nao_tem_data_de_publicacao(self):
        response = self.client.get("/")
        self.assertNotContains(response, "Publicado em")
