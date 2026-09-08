import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from bebedouros import grafico


class MontarGraficoTests(SimpleTestCase):
    def test_lista_vazia_retorna_none(self):
        self.assertIsNone(grafico.montar_grafico([]))

    def test_sem_nenhum_valor_retorna_none(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": None}]
        self.assertIsNone(grafico.montar_grafico(pontos))

    def test_um_ponto_fica_num_unico_segmento(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": Decimal("80")}]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertEqual(len(g["segmentos"]), 1)
        self.assertEqual(len(g["segmentos"][0]), 1)

    def test_gap_no_meio_quebra_em_dois_segmentos(self):
        pontos = [
            {"data": datetime.date(2026, 1, 1), "valor": Decimal("80")},
            {"data": datetime.date(2026, 2, 1), "valor": None},
            {"data": datetime.date(2026, 3, 1), "valor": Decimal("70")},
        ]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertEqual(len(g["segmentos"]), 2)
        self.assertEqual(len(g["segmentos"][0]), 1)
        self.assertEqual(len(g["segmentos"][1]), 1)

    def test_dominio_fixo_gera_5_faixas_na_ordem_certa(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": Decimal("80")}]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertEqual(
            [f["slug"] for f in g["faixas"]],
            ["critica", "ruim", "regular", "boa", "excelente"],
        )

    def test_sem_dominio_fixo_nao_gera_faixas(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": Decimal("1.2")}]
        g = grafico.montar_grafico(pontos)
        self.assertIsNone(g["faixas"])

    def test_primeiro_ponto_fica_na_margem_esquerda(self):
        pontos = [
            {"data": datetime.date(2026, 1, 1), "valor": Decimal("80")},
            {"data": datetime.date(2026, 6, 1), "valor": Decimal("90")},
        ]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertAlmostEqual(g["segmentos"][0][0]["x"], g["area_esq"])

    def test_ultimo_ponto_fica_na_margem_direita(self):
        pontos = [
            {"data": datetime.date(2026, 1, 1), "valor": Decimal("80")},
            {"data": datetime.date(2026, 6, 1), "valor": Decimal("90")},
        ]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertAlmostEqual(g["segmentos"][-1][-1]["x"], g["area_dir"])

    def test_valor_maximo_do_dominio_fica_no_topo_da_area(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": Decimal("100")}]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertAlmostEqual(g["segmentos"][0][0]["y"], g["area_topo"])

    def test_valor_minimo_do_dominio_fica_na_base_da_area(self):
        pontos = [{"data": datetime.date(2026, 1, 1), "valor": Decimal("0")}]
        g = grafico.montar_grafico(pontos, dominio_y=(0, 100))
        self.assertAlmostEqual(g["segmentos"][0][0]["y"], g["area_base"])

    def test_dominio_automatico_desce_ate_zero(self):
        pontos = [
            {"data": datetime.date(2026, 1, 1), "valor": Decimal("5")},
            {"data": datetime.date(2026, 2, 1), "valor": Decimal("7")},
        ]
        g = grafico.montar_grafico(pontos)
        # Com domínio automático indo até 0 (não até o próprio 5), o
        # ponto de valor 5 fica acima da base da área, não em cima dela.
        self.assertLess(g["segmentos"][0][0]["y"], g["area_base"])
