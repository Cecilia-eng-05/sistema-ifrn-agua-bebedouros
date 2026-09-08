import datetime
from decimal import Decimal

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


class MapaTests(TestCase):
    def test_nao_exige_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_mostra_link_para_bebedouro_com_posicao_mapeada(self):
        b1 = Bebedouro.objects.create(numero=1, local="Mesas verdes")
        response = self.client.get("/")
        self.assertContains(response, f'href="/bebedouros/{b1.pk}/"')

    def test_titulo_do_ponto_mostra_codigo_e_local(self):
        Bebedouro.objects.create(numero=1, local="Mesas verdes")
        response = self.client.get("/")
        self.assertContains(response, 'title="B1 — Mesas verdes"')

    def test_ponto_mostra_o_codigo_visivel_junto_da_gota(self):
        Bebedouro.objects.create(numero=1)
        response = self.client.get("/")
        self.assertContains(response, '<span class="mapa-ponto-rotulo">B1</span>')

    def test_sem_resultado_mostra_gota_vazia(self):
        Bebedouro.objects.create(numero=1)
        response = self.client.get("/")
        self.assertContains(response, 'class="gota gota-md gota-vazia"')

    def test_com_resultado_publicado_mostra_gota_colorida(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get("/")
        self.assertContains(response, 'class="gota gota-md gota-excelente"')

    def test_rascunho_nao_aparece_no_mapa(self):
        Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.RASCUNHO)
        Resultado.objects.create(coleta=coleta, bebedouro=Bebedouro.objects.first(), **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get("/")
        self.assertContains(response, 'class="gota gota-md gota-vazia"')
        self.assertNotContains(response, 'class="gota gota-md gota-excelente"')

    def test_visitante_ve_menu_publico_nao_o_interno(self):
        response = self.client.get("/")
        self.assertContains(response, ">Mapa<")
        self.assertContains(response, ">Entrar<")
        self.assertNotContains(response, ">Coletas<")
        self.assertNotContains(response, ">Sair<")
