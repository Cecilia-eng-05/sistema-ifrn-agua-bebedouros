from django.test import TestCase


class AbasPublicasTests(TestCase):
    def test_mapa_mostra_as_tres_abas(self):
        response = self.client.get("/")
        self.assertContains(response, ">Mapa<")
        self.assertContains(response, ">Entenda o IQA-B<")
        self.assertContains(response, ">Alertas<")

    def test_entenda_iqab_nao_exige_login(self):
        response = self.client.get("/entenda-o-iqab/")
        self.assertEqual(response.status_code, 200)

    def test_entenda_iqab_mostra_aba_ativa(self):
        response = self.client.get("/entenda-o-iqab/")
        self.assertContains(response, 'class="aba aba-ativa"')
        self.assertContains(response, ">Entenda o IQA-B<")

    def test_alertas_publico_nao_exige_login(self):
        response = self.client.get("/alertas/")
        self.assertEqual(response.status_code, 200)

    def test_alertas_publico_mostra_aba_ativa(self):
        response = self.client.get("/alertas/")
        self.assertContains(response, 'class="aba aba-ativa"')
        self.assertContains(response, ">Alertas<")

    def test_entrar_so_aparece_no_mapa(self):
        self.assertContains(self.client.get("/"), ">Entrar<")
        self.assertNotContains(self.client.get("/entenda-o-iqab/"), ">Entrar<")
        self.assertNotContains(self.client.get("/alertas/"), ">Entrar<")
