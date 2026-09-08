import datetime
from decimal import Decimal

from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import (
    alertas_internos,
    linhas_faltantes,
    recalcular_coleta,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
)

RESULTADO_COMPLETO = dict(
    cloro=Decimal("1.0"),
    turbidez_valor=Decimal("0.5"),
    ph=Decimal("7.0"),
    nitrato=Decimal("5.0"),
    coliformes_totais=Resultado.AUSENTE,
    ecoli=Resultado.AUSENTE,
    filtro=Resultado.FILTRO_DENTRO,
)


class LinhasFaltantesTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)
        self.b3 = Bebedouro.objects.create(
            numero=3, desativado_em=datetime.date(2026, 1, 1)
        )

    def test_missing_when_no_result_or_empty_result(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        self.assertEqual(linhas_faltantes(self.coleta), ["B2"])

    def test_fora_de_operacao_is_not_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, fora_de_operacao=True)
        self.assertEqual(linhas_faltantes(self.coleta), [])

    def test_inactive_fountain_never_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.assertNotIn("B3", linhas_faltantes(self.coleta))


class SituacaoAtualBebedourosTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)

    def test_bebedouro_sem_nenhuma_coleta_fica_sem_resultado(self):
        situacoes = situacao_atual_bebedouros()
        s1 = situacoes[0]
        self.assertEqual(s1["bebedouro"], self.b1)
        self.assertIsNone(s1["resultado"])
        self.assertIsNone(s1["data"])

    def test_pega_o_resultado_da_coleta_mais_recente(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 8, 1))
        recente = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, ph=Decimal("7.0"))
        r_recente = Resultado.objects.create(coleta=recente, bebedouro=self.b1, ph=Decimal("7.5"))
        situacoes = situacao_atual_bebedouros()
        s1 = [s for s in situacoes if s["bebedouro"] == self.b1][0]
        self.assertEqual(s1["resultado"], r_recente)
        self.assertEqual(s1["data"], datetime.date(2026, 9, 1))

    def test_ignora_linha_vazia_e_fora_de_operacao_mais_recentes(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 8, 1))
        recente = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        r_antiga = Resultado.objects.create(coleta=antiga, bebedouro=self.b1, ph=Decimal("7.0"))
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, fora_de_operacao=True)
        situacoes = situacao_atual_bebedouros()
        s1 = [s for s in situacoes if s["bebedouro"] == self.b1][0]
        self.assertEqual(s1["resultado"], r_antiga)
        self.assertEqual(s1["data"], datetime.date(2026, 8, 1))


class AlertasInternosTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2, desativado_em=datetime.date(2026, 1, 1))
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))

    def test_sem_coletas_alertas_vazios(self):
        Coleta.objects.all().delete()
        alertas = alertas_internos(situacao_atual_bebedouros())
        self.assertEqual(alertas["iqab_ruim"], [])
        self.assertEqual(alertas["filtro_vencido"], [])
        self.assertEqual(alertas["quinzena_sem_dados"], [])

    def test_iqab_abaixo_de_40_entra_no_alerta(self):
        dados = {
            **RESULTADO_COMPLETO,
            "cloro": Decimal("0.1"),
            "ph": Decimal("5"),
            "nitrato": Decimal("20"),
            "ecoli": Resultado.PRESENTE,
        }
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(self.coleta)
        alertas = alertas_internos(situacao_atual_bebedouros())
        codigos = [s["bebedouro"].codigo for s in alertas["iqab_ruim"]]
        self.assertIn("B1", codigos)

    def test_iqab_bom_nao_entra_no_alerta(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(self.coleta)
        alertas = alertas_internos(situacao_atual_bebedouros())
        self.assertEqual(alertas["iqab_ruim"], [])

    def test_filtro_vencido_entra_no_alerta_mesmo_com_iqab_bom(self):
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(self.coleta)
        situacoes = situacao_atual_bebedouros()
        s1 = [s for s in situacoes if s["bebedouro"] == self.b1][0]
        self.assertEqual(s1["resultado"].iqab_classificacao, "Excelente")
        alertas = alertas_internos(situacoes)
        codigos = [s["bebedouro"].codigo for s in alertas["filtro_vencido"]]
        self.assertIn("B1", codigos)

    def test_desativado_nao_entra_nos_alertas(self):
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, **dados)
        recalcular_coleta(self.coleta)
        alertas = alertas_internos(situacao_atual_bebedouros())
        codigos = [s["bebedouro"].codigo for s in alertas["filtro_vencido"]]
        self.assertNotIn("B2", codigos)

    def test_quinzena_sem_dados_lista_ativo_sem_lancamento(self):
        b3 = Bebedouro.objects.create(numero=3)
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(self.coleta)
        alertas = alertas_internos(situacao_atual_bebedouros())
        self.assertEqual(alertas["quinzena_sem_dados"], [b3.codigo])


class SituacaoAtualBebedouroTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_sem_nenhuma_coleta(self):
        situacao = situacao_atual_bebedouro(self.b1)
        self.assertEqual(situacao["bebedouro"], self.b1)
        self.assertIsNone(situacao["resultado"])
        self.assertIsNone(situacao["data"])

    def test_pega_o_mais_recente(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 8, 1))
        recente = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, ph=Decimal("7.0"))
        r_recente = Resultado.objects.create(coleta=recente, bebedouro=self.b1, ph=Decimal("7.5"))
        situacao = situacao_atual_bebedouro(self.b1)
        self.assertEqual(situacao["resultado"], r_recente)

    def test_apenas_publicadas_ignora_rascunho(self):
        rascunho = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=rascunho, bebedouro=self.b1, **RESULTADO_COMPLETO)
        situacao = situacao_atual_bebedouro(self.b1, apenas_publicadas=True)
        self.assertIsNone(situacao["resultado"])

    def test_apenas_publicadas_usa_a_publicada(self):
        publicada = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        r = Resultado.objects.create(coleta=publicada, bebedouro=self.b1, **RESULTADO_COMPLETO)
        situacao = situacao_atual_bebedouro(self.b1, apenas_publicadas=True)
        self.assertEqual(situacao["resultado"], r)

    def test_apenas_publicadas_pula_rascunho_mais_recente(self):
        publicada = Coleta.objects.create(
            data=datetime.date(2026, 8, 1), status=Coleta.PUBLICADO
        )
        rascunho = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        r_publicada = Resultado.objects.create(
            coleta=publicada, bebedouro=self.b1, **RESULTADO_COMPLETO
        )
        Resultado.objects.create(coleta=rascunho, bebedouro=self.b1, **RESULTADO_COMPLETO)
        situacao = situacao_atual_bebedouro(self.b1, apenas_publicadas=True)
        self.assertEqual(situacao["resultado"], r_publicada)
