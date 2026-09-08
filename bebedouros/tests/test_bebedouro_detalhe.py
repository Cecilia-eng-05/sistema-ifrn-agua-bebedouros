import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import recalcular_coleta

RESULTADO_COMPLETO = dict(
    cloro=Decimal("1.0"),
    turbidez_valor=Decimal("0.5"),
    ph=Decimal("7.0"),
    nitrato=Decimal("5.0"),
    coliformes_totais=Resultado.AUSENTE,
    ecoli=Resultado.AUSENTE,
    filtro=Resultado.FILTRO_DENTRO,
)


class BebedouroDetalheTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1, local="Mesas verdes")

    def test_pagina_publica_nao_exige_login(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "B1")
        self.assertContains(response, "Mesas verdes")

    def test_bebedouro_inexistente_da_404(self):
        response = self.client.get("/bebedouros/9999/")
        self.assertEqual(response.status_code, 404)

    def test_sem_dados_mostra_gota_vazia(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-vazia"')

    def test_com_dados_publicados_mostra_gota_colorida(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-excelente"')
        self.assertContains(response, "Excelente")
        self.assertContains(response, "01/09/2026")

    def test_visitante_nao_ve_rascunho(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-vazia"')
        self.assertNotContains(response, 'class="gota gota-lg gota-excelente"')

    def test_usuario_logado_ve_rascunho(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-excelente"')

    def test_filtro_vencido_mostra_aviso(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Filtro fora da validade na última coleta.")

    def test_sem_filtro_vencido_nao_mostra_aviso(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertNotContains(response, "Filtro fora da validade na última coleta.")

    def test_publico_nao_mostra_cartoes_internos(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertNotContains(response, "De onde vem a nota")

    def test_interno_mostra_cartoes_com_pesos_e_notas(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "De onde vem a nota")
        self.assertContains(response, "peso 30%")
        self.assertContains(response, "peso 50%")
        self.assertContains(response, "peso 20%")

    def test_motivo_aparece_so_quando_filtro_vencido(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Filtro fora da validade na data da coleta.")

    def test_sem_motivo_quando_filtro_em_dia(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertNotContains(response, "Filtro fora da validade na data da coleta.")

    def test_tabela_de_parametros_mostra_valores_da_ultima_coleta(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "O que é monitorado nesta água")
        self.assertContains(response, "Cloro Residual Livre")
        self.assertContains(response, "Ausente")

    def test_turbidez_abaixo_do_limite_mostra_menor_que(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        dados = {**RESULTADO_COMPLETO, "turbidez_valor": None, "turbidez_abaixo_limite": True}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "&lt;")
