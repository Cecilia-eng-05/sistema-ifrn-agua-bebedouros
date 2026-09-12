import datetime
from decimal import Decimal

from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import publicar_coleta, recalcular_coleta

RESULTADO_COMPLETO = dict(
    cloro=Decimal("1.0"),
    turbidez_valor=Decimal("0.5"),
    ph=Decimal("7.0"),
    nitrato=Decimal("5.0"),
    coliformes_totais=Resultado.AUSENTE,
    ecoli=Resultado.AUSENTE,
    filtro=Resultado.FILTRO_DENTRO,
)
RESULTADO_CRITICO = {
    **RESULTADO_COMPLETO,
    "cloro": Decimal("0.1"),
    "ph": Decimal("5"),
    "nitrato": Decimal("20"),
    "ecoli": Resultado.PRESENTE,
}


def _coleta_publicada(data, bebedouro, **dados):
    coleta = Coleta.objects.create(data=data)
    Resultado.objects.create(
        coleta=coleta, bebedouro=bebedouro, **{**RESULTADO_COMPLETO, **dados}
    )
    recalcular_coleta(coleta)
    publicar_coleta(coleta)
    return coleta


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


class EntendaIqabConteudoTests(TestCase):
    def setUp(self):
        self.response = self.client.get("/entenda-o-iqab/")

    def test_nao_esta_mais_em_construcao(self):
        self.assertNotContains(self.response, "em construção")

    def test_mostra_os_sete_parametros(self):
        for nome in [
            "Cloro residual livre",
            "Turbidez",
            "pH",
            "Nitrato",
            "Condutividade elétrica",
            "Coliformes totais",
            "Escherichia coli",
        ]:
            self.assertContains(self.response, nome)

    def test_mostra_a_formula_com_os_pesos(self):
        self.assertContains(self.response, "(QFQ × 0,3)")
        self.assertContains(self.response, "(QM × 0,5)")
        self.assertContains(self.response, "(CO × 0,2)")

    def test_mostra_a_tabela_de_classificacao(self):
        for nome in ["Excelente", "Boa", "Regular", "Ruim", "Crítica"]:
            self.assertContains(self.response, nome)
        self.assertContains(self.response, "80 a 100")
        self.assertContains(self.response, "abaixo de 20")

    def test_explica_que_a_condutividade_nao_entra_no_calculo(self):
        self.assertContains(self.response, "não entra no cálculo")

    def test_cita_a_portaria_888(self):
        self.assertContains(self.response, "888/2021")


class AlertasPublicoConteudoTests(TestCase):
    VAZIO_IQAB = "Nenhum bebedouro em situação ruim ou crítica no momento."
    VAZIO_FILTRO = "Nenhum filtro fora da validade no momento."

    def test_nao_esta_mais_em_construcao(self):
        self.assertNotContains(self.client.get("/alertas/"), "em construção")

    def test_sem_dados_mostra_as_duas_mensagens_vazias(self):
        Bebedouro.objects.create(numero=1, local="Mesas verdes")
        response = self.client.get("/alertas/")
        self.assertContains(response, self.VAZIO_IQAB)
        self.assertContains(response, self.VAZIO_FILTRO)

    def test_lista_bebedouro_ruim_ou_critico(self):
        b1 = Bebedouro.objects.create(numero=1, local="Marcenaria")
        _coleta_publicada(datetime.date(2026, 9, 1), b1, **RESULTADO_CRITICO)
        response = self.client.get("/alertas/")
        self.assertNotContains(response, self.VAZIO_IQAB)
        self.assertContains(response, "B1")
        self.assertContains(response, "Marcenaria")
        self.assertContains(response, "Crítica")
        self.assertContains(response, f'href="/bebedouros/{b1.pk}/"')

    def test_lista_filtro_fora_da_validade(self):
        b1 = Bebedouro.objects.create(numero=1, local="Piscinas")
        _coleta_publicada(
            datetime.date(2026, 9, 1), b1, filtro=Resultado.FILTRO_VENCIDO
        )
        response = self.client.get("/alertas/")
        self.assertNotContains(response, self.VAZIO_FILTRO)
        self.assertContains(response, "B1")
        self.assertContains(response, "Piscinas")
        self.assertContains(response, f'href="/bebedouros/{b1.pk}/"')

    def test_coleta_em_rascunho_nao_aparece(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **RESULTADO_CRITICO)
        recalcular_coleta(coleta)  # sem publicar
        response = self.client.get("/alertas/")
        self.assertContains(response, self.VAZIO_IQAB)
        self.assertNotContains(response, ">B1<")

    def test_bebedouro_desativado_nao_aparece(self):
        b1 = Bebedouro.objects.create(
            numero=1, desativado_em=datetime.date(2020, 1, 1)
        )
        _coleta_publicada(datetime.date(2026, 9, 1), b1, **RESULTADO_CRITICO)
        response = self.client.get("/alertas/")
        self.assertContains(response, self.VAZIO_IQAB)
