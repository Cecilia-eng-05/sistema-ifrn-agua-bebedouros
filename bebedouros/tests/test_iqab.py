import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from bebedouros import iqab
from bebedouros.models import Bebedouro, Coleta, Resultado


class ClassificarTests(SimpleTestCase):
    def test_faixas(self):
        casos = [
            (Decimal("100"), "Excelente"),
            (Decimal("80"), "Excelente"),
            (Decimal("79"), "Boa"),
            (Decimal("60"), "Boa"),
            (Decimal("59"), "Regular"),
            (Decimal("40"), "Regular"),
            (Decimal("39"), "Ruim"),
            (Decimal("20"), "Ruim"),
            (Decimal("19"), "Crítica"),
            (Decimal("0"), "Crítica"),
        ]
        for nota, esperado in casos:
            self.assertEqual(iqab.classificar(nota), esperado, nota)

    def test_none(self):
        self.assertEqual(iqab.classificar(None), "")


# Combinação de parâmetros em que nenhum derruba nota: QFQ = QM = CO = 100.
RESULTADO_PERFEITO = dict(
    cloro=Decimal("1.0"),
    turbidez_valor=Decimal("0.5"),
    ph=Decimal("7.0"),
    nitrato=Decimal("5.0"),
    coliformes_totais=Resultado.AUSENTE,
    ecoli=Resultado.AUSENTE,
    filtro=Resultado.FILTRO_DENTRO,
)


class CalcularTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def _criar(self, **overrides):
        dados = {**RESULTADO_PERFEITO, **overrides}
        return Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, **dados)

    def test_linha_vazia_sem_dados(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.SEM_DADOS)
        self.assertIsNone(d["iqab"])

    def test_fora_de_operacao_sem_dados(self):
        r = Resultado.objects.create(
            coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7"), fora_de_operacao=True
        )
        self.assertEqual(iqab.calcular(r)["status"], iqab.SEM_DADOS)

    def test_dados_parciais_fica_incompleto(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.2"))
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.INCOMPLETO)
        self.assertIsNone(d["iqab"])
        self.assertEqual(d["versao"], iqab.VERSAO_METODOLOGIA)

    def test_falta_so_o_filtro_tambem_fica_incompleto(self):
        # É o caso do histórico 2024/2025: nunca anotaram a situação do filtro.
        r = self._criar(filtro="")
        self.assertEqual(iqab.calcular(r)["status"], iqab.INCOMPLETO)

    def test_tudo_dentro_dos_limites_calcula_100(self):
        r = self._criar()
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.CALCULADO)
        self.assertEqual(d["iqab"], Decimal("100"))
        self.assertEqual(d["classificacao"], "Excelente")
        self.assertEqual(d["qfq"], Decimal("100"))
        self.assertEqual(d["qm"], Decimal("100"))
        self.assertEqual(d["co"], Decimal("100"))
        self.assertEqual(d["versao"], iqab.VERSAO_METODOLOGIA)

    def test_condutividade_nao_entra_na_formula(self):
        r = self._criar(condutividade=Decimal("9999"))
        self.assertEqual(iqab.calcular(r)["iqab"], Decimal("100"))

    def test_cloro_fora_da_faixa_ideal_derruba_qfq(self):
        r = self._criar(cloro=Decimal("0.1"))  # abaixo de 0,20
        d = iqab.calcular(r)
        # nota_cloro=0 => QFQ = 0,25*100 + 0,20*100 + 0,20*100 = 65
        self.assertEqual(d["qfq"], Decimal("65"))
        # IQA-B = 0,3*65 + 0,5*100 + 0,2*100 = 89,5 -> arredonda p/ 90
        self.assertEqual(d["iqab"], Decimal("90"))

    def test_turbidez_faixa_intermediaria_pontua_50(self):
        r = self._criar(turbidez_valor=Decimal("3"))  # 1,01 a 5 NTU
        d = iqab.calcular(r)
        # QFQ = 0,35*100 + 0,25*50 + 0,20*100 + 0,20*100 = 87,5 -> arredonda p/ 88
        self.assertEqual(d["qfq"], Decimal("88"))
        # IQA-B (calculado com o QFQ cheio, sem arredondar antes) = 96,25 -> 96
        self.assertEqual(d["iqab"], Decimal("96"))

    def test_turbidez_acima_do_limite_zera(self):
        r = self._criar(turbidez_valor=Decimal("6"))
        d = iqab.calcular(r)
        self.assertEqual(d["qfq"], Decimal("75"))
        self.assertEqual(d["iqab"], Decimal("93"))  # 92,5 -> arredonda p/ cima

    def test_turbidez_abaixo_do_limite_de_deteccao_conta_como_otima(self):
        r = self._criar(turbidez_valor=None, turbidez_abaixo_limite=True)
        d = iqab.calcular(r)
        self.assertEqual(d["status"], iqab.CALCULADO)
        self.assertEqual(d["qfq"], Decimal("100"))

    def test_ph_fora_da_faixa_ideal_zera(self):
        r = self._criar(ph=Decimal("5"))
        d = iqab.calcular(r)
        self.assertEqual(d["qfq"], Decimal("80"))
        self.assertEqual(d["iqab"], Decimal("94"))

    def test_nitrato_acima_do_limite_zera(self):
        r = self._criar(nitrato=Decimal("12"))
        d = iqab.calcular(r)
        self.assertEqual(d["qfq"], Decimal("80"))
        self.assertEqual(d["iqab"], Decimal("94"))

    def test_ecoli_presente_zera_qm_mesmo_com_coliformes_ausente(self):
        r = self._criar(ecoli=Resultado.PRESENTE)
        d = iqab.calcular(r)
        self.assertEqual(d["qm"], Decimal("0"))
        self.assertEqual(d["iqab"], Decimal("50"))  # 0,3*100 + 0,5*0 + 0,2*100
        self.assertEqual(d["classificacao"], "Regular")

    def test_coliformes_presente_sem_ecoli_usa_media_ponderada(self):
        r = self._criar(coliformes_totais=Resultado.PRESENTE)
        d = iqab.calcular(r)
        # QM = 0,70*100 (E. coli ausente) + 0,30*0 (coliformes presente) = 70
        self.assertEqual(d["qm"], Decimal("70"))
        self.assertEqual(d["iqab"], Decimal("85"))  # 0,3*100 + 0,5*70 + 0,2*100

    def test_filtro_vencido_zera_co(self):
        r = self._criar(filtro=Resultado.FILTRO_VENCIDO)
        d = iqab.calcular(r)
        self.assertEqual(d["co"], Decimal("0"))
        self.assertEqual(d["iqab"], Decimal("80"))  # 0,3*100 + 0,5*100 + 0,2*0
        self.assertEqual(d["classificacao"], "Excelente")


class RecalculoAoSalvarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_salvar_grade_com_dados_parciais_grava_incompleto(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-ph": "7,2"},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.iqab_status, iqab.INCOMPLETO)
        self.assertEqual(r.metodologia_versao, iqab.VERSAO_METODOLOGIA)
        self.assertEqual(r.iqab_texto(), "incompleto")

    def test_linha_em_branco_fica_sem_dados(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-observacao": ""},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.iqab_status, iqab.SEM_DADOS)
        self.assertEqual(r.iqab_texto(), "—")

    def test_grade_mostra_coluna_iqab(self):
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertContains(response, "IQA-B")

    def test_salvar_grade_completa_calcula_iqab(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {
                f"b{self.b1.id}-cloro": "1,0",
                f"b{self.b1.id}-turbidez": "0,5",
                f"b{self.b1.id}-ph": "7,0",
                f"b{self.b1.id}-nitrato": "5,0",
                f"b{self.b1.id}-coliformes_totais": Resultado.AUSENTE,
                f"b{self.b1.id}-ecoli": Resultado.AUSENTE,
                f"b{self.b1.id}-filtro": Resultado.FILTRO_DENTRO,
            },
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.iqab_status, iqab.CALCULADO)
        self.assertEqual(r.iqab, Decimal("100"))
        self.assertEqual(r.iqab_classificacao, "Excelente")
        # Sem casa decimal (é inteiro) e sem ponto (vírgula é o separador em pt-br).
        self.assertEqual(r.iqab_texto(), "100 · Excelente")

    def test_turbidez_reaparece_na_grade_com_virgula_nao_ponto(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-turbidez": "0,751"},
            follow=True,
        )
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        form = {l["bebedouro"].codigo: l["form"] for l in response.context["linhas"]}["B1"]
        self.assertEqual(form.initial["turbidez"], "0,751")
