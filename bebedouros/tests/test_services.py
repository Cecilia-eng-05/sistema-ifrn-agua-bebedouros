import datetime
from decimal import Decimal

from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado, TrocaFiltro
from bebedouros.services import (
    alertas_internos,
    aviso_filtro_incompativel,
    coletas_recentes,
    linhas_faltantes,
    media_coletas,
    recalcular_coleta,
    salvar_troca_filtro,
    serie_historica,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
    situacao_filtro,
    ultima_troca_filtro,
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

    def test_apenas_publicadas_ignora_rascunho(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.RASCUNHO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        situacoes = situacao_atual_bebedouros(apenas_publicadas=True)
        s1 = [s for s in situacoes if s["bebedouro"] == self.b1][0]
        self.assertIsNone(s1["resultado"])

    def test_apenas_publicadas_usa_a_publicada(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        resultado = Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        situacoes = situacao_atual_bebedouros(apenas_publicadas=True)
        s1 = [s for s in situacoes if s["bebedouro"] == self.b1][0]
        self.assertEqual(s1["resultado"], resultado)


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


class SerieHistoricaTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def _coleta(self, dias_atras, **overrides):
        data = datetime.date.today() - datetime.timedelta(days=dias_atras)
        coleta = Coleta.objects.create(data=data, **overrides)
        return coleta

    def test_usa_a_nota_quando_calculado(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual(len(pontos), 1)
        self.assertEqual(pontos[0]["valor"], Decimal("100"))

    def test_fica_none_quando_incompleto(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual(len(pontos), 1)
        self.assertIsNone(pontos[0]["valor"])

    def test_linha_totalmente_vazia_nao_entra_na_serie(self):
        self._coleta(10)  # coleta existe, mas sem nenhum Resultado criado
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual(pontos, [])

    def test_fora_de_operacao_nao_entra_na_serie(self):
        coleta = self._coleta(10)
        Resultado.objects.create(
            coleta=coleta, bebedouro=self.b1, fora_de_operacao=True, **RESULTADO_COMPLETO
        )
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual(pontos, [])

    def test_janela_6m_exclui_coleta_mais_antiga(self):
        antiga = self._coleta(400)
        recente = self._coleta(10)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        pontos = serie_historica(self.b1, "6m")
        self.assertEqual(len(pontos), 1)
        self.assertEqual(pontos[0]["data"], recente.data)

    def test_janela_tudo_inclui_tudo(self):
        antiga = self._coleta(400)
        recente = self._coleta(10)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual(len(pontos), 2)

    def test_pontos_em_ordem_cronologica(self):
        recente = self._coleta(5)
        antiga = self._coleta(50)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(recente)
        recalcular_coleta(antiga)
        pontos = serie_historica(self.b1, "tudo")
        self.assertEqual([p["data"] for p in pontos], [antiga.data, recente.data])

    def test_apenas_publicadas_ignora_rascunho(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "tudo", apenas_publicadas=True)
        self.assertEqual(pontos, [])


class ColetasRecentesTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def _coleta_com_resultado(self, dias_atras, **campos):
        data = datetime.date.today() - datetime.timedelta(days=dias_atras)
        coleta = Coleta.objects.create(data=data, status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **campos)
        return coleta

    def test_sem_coletas_retorna_lista_vazia(self):
        self.assertEqual(coletas_recentes(self.b1), [])

    def test_traz_no_maximo_5_mais_recentes(self):
        for dias in [0, 15, 30, 45, 60, 75, 90]:
            self._coleta_com_resultado(dias, ph=Decimal("7.0"))
        recentes = coletas_recentes(self.b1)
        self.assertEqual(len(recentes), 5)
        datas = [r.coleta.data for r in recentes]
        self.assertEqual(datas, sorted(datas, reverse=True))
        self.assertEqual(datas[0], datetime.date.today())

    def test_inclui_a_situacao_atual(self):
        self._coleta_com_resultado(0, ph=Decimal("7.0"))
        recentes = coletas_recentes(self.b1)
        self.assertEqual(len(recentes), 1)
        self.assertEqual(recentes[0].coleta.data, datetime.date.today())

    def test_pula_linha_vazia_sem_fora_de_operacao(self):
        self._coleta_com_resultado(0)  # sem nenhum dado
        self._coleta_com_resultado(15, ph=Decimal("7.0"))
        recentes = coletas_recentes(self.b1)
        self.assertEqual(len(recentes), 1)

    def test_fora_de_operacao_nao_entra_na_lista(self):
        # Fora de operação não é um resultado — a situação atual já
        # aparece no topo da página, então não há por que repetir aqui.
        self._coleta_com_resultado(0, fora_de_operacao=True)
        recentes = coletas_recentes(self.b1)
        self.assertEqual(recentes, [])

    def test_fora_de_operacao_com_observacao_tambem_nao_entra(self):
        # Mesmo com uma observação preenchida (o que faz esta_vazio()
        # retornar False), uma linha fora de operação continua de fora.
        self._coleta_com_resultado(0, fora_de_operacao=True, observacao="Quebrado")
        recentes = coletas_recentes(self.b1)
        self.assertEqual(recentes, [])

    def test_fora_de_operacao_no_meio_do_historico_e_pulada(self):
        # As duas mais recentes ficam de fora por estarem fora de
        # operação; a lista busca mais pra trás até achar 5 com dado.
        self._coleta_com_resultado(0, fora_de_operacao=True)
        self._coleta_com_resultado(15, fora_de_operacao=True)
        for dias in [30, 45, 60, 75, 90]:
            self._coleta_com_resultado(dias, ph=Decimal("7.0"))
        recentes = coletas_recentes(self.b1)
        self.assertEqual(len(recentes), 5)
        datas = [r.coleta.data for r in recentes]
        esperado_mais_recente = datetime.date.today() - datetime.timedelta(days=30)
        self.assertEqual(datas[0], esperado_mais_recente)

    def test_apenas_publicadas_ignora_rascunho(self):
        coleta = Coleta.objects.create(data=datetime.date.today())  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        self.assertEqual(coletas_recentes(self.b1, apenas_publicadas=True), [])
        self.assertEqual(len(coletas_recentes(self.b1, apenas_publicadas=False)), 1)


class MediaColetasTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def _resultado(self, coleta_num, **campos):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 1, coleta_num), status=Coleta.PUBLICADO
        )
        r = Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **campos)
        recalcular_coleta(coleta)
        return Resultado.objects.get(pk=r.pk)

    def test_lista_vazia(self):
        media = media_coletas([])
        self.assertEqual(media["quantidade"], 0)
        self.assertEqual(media["cloro"], "—")
        self.assertEqual(media["iqab_texto"], "—")

    def test_media_simples_de_cloro(self):
        r1 = self._resultado(1, cloro=Decimal("1.0"))
        r2 = self._resultado(2, cloro=Decimal("2.0"))
        media = media_coletas([r1, r2])
        self.assertEqual(media["cloro"], "1,500")
        self.assertEqual(media["quantidade"], 2)

    def test_valor_em_branco_fica_de_fora_da_media(self):
        r1 = self._resultado(1, cloro=Decimal("2.0"))
        r2 = self._resultado(2)  # cloro em branco
        media = media_coletas([r1, r2])
        self.assertEqual(media["cloro"], "2,000")

    def test_fora_de_operacao_fica_de_fora_da_media(self):
        r1 = self._resultado(1, cloro=Decimal("2.0"))
        r2 = self._resultado(2, fora_de_operacao=True)
        media = media_coletas([r1, r2])
        self.assertEqual(media["cloro"], "2,000")
        self.assertEqual(media["quantidade"], 1)

    def test_media_que_nao_fecha_redondo_e_arredondada_nao_esticada(self):
        # 1 + 1 + 2 = 4 / 3 = 1,3333... — sem arredondar pra 3 casas isso
        # viraria uma dízima gigante na tela (bug real, achado na revisão
        # do plano antes de implementar).
        r1 = self._resultado(1, cloro=Decimal("1.0"))
        r2 = self._resultado(2, cloro=Decimal("1.0"))
        r3 = self._resultado(3, cloro=Decimal("2.0"))
        media = media_coletas([r1, r2, r3])
        self.assertEqual(media["cloro"], "1,333")

    def test_turbidez_abaixo_do_limite_marca_menor_que(self):
        r1 = self._resultado(1, turbidez_valor=Decimal("0.751"), turbidez_abaixo_limite=True)
        r2 = self._resultado(2, turbidez_valor=Decimal("0.601"))
        media = media_coletas([r1, r2])
        self.assertEqual(media["turbidez"], "<0,676")

    def test_coliformes_ausente_em_todas(self):
        r1 = self._resultado(1, coliformes_totais=Resultado.AUSENTE)
        r2 = self._resultado(2, coliformes_totais=Resultado.AUSENTE)
        media = media_coletas([r1, r2])
        self.assertEqual(media["coliformes_totais"], "Ausente em 2 de 2 coletas")
        self.assertFalse(media["coliformes_totais_alerta"])

    def test_coliformes_presente_em_uma_ativa_alerta(self):
        r1 = self._resultado(1, coliformes_totais=Resultado.PRESENTE)
        r2 = self._resultado(2, coliformes_totais=Resultado.AUSENTE)
        media = media_coletas([r1, r2])
        self.assertEqual(media["coliformes_totais"], "Presente em 1 de 2 coletas")
        self.assertTrue(media["coliformes_totais_alerta"])

    def test_coliformes_singular_quando_total_e_1(self):
        r1 = self._resultado(1, coliformes_totais=Resultado.AUSENTE)
        media = media_coletas([r1])
        self.assertEqual(media["coliformes_totais"], "Ausente em 1 de 1 coleta")

    def test_coliformes_presente_singular_quando_total_e_1(self):
        r1 = self._resultado(1, coliformes_totais=Resultado.PRESENTE)
        media = media_coletas([r1])
        self.assertEqual(media["coliformes_totais"], "Presente em 1 de 1 coleta")

    def test_micro_sem_dado_nenhum_mostra_travessao(self):
        r1 = self._resultado(1, ph=Decimal("7.0"))
        media = media_coletas([r1])
        self.assertEqual(media["coliformes_totais"], "—")

    def test_media_do_iqab(self):
        completo = dict(
            cloro=Decimal("1.0"), turbidez_valor=Decimal("0.5"), ph=Decimal("7.0"),
            nitrato=Decimal("5.0"), coliformes_totais=Resultado.AUSENTE,
            ecoli=Resultado.AUSENTE, filtro=Resultado.FILTRO_DENTRO,
        )
        r1 = self._resultado(1, **completo)  # 100 · Excelente
        r2 = self._resultado(2, ph=Decimal("7.0"))  # incompleto -> fora da média
        media = media_coletas([r1, r2])
        self.assertEqual(media["iqab_texto"], "100 · Excelente")


class SituacaoFiltroTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.coleta = Coleta.objects.create(
            data=datetime.date.today(), status=Coleta.PUBLICADO
        )

    def test_sem_registro(self):
        situacao = situacao_filtro(self.b1)
        self.assertEqual(situacao["status"], "sem_registro")
        self.assertIsNone(situacao["data_troca"])

    def test_troca_recente_esta_ok(self):
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date.today()
        )
        situacao = situacao_filtro(self.b1)
        self.assertEqual(situacao["status"], "ok")
        self.assertEqual(situacao["data_troca"], datetime.date.today())

    def test_troca_vencida(self):
        antiga = datetime.date.today() - datetime.timedelta(days=200)
        TrocaFiltro.objects.create(bebedouro=self.b1, coleta=self.coleta, data_troca=antiga)
        situacao = situacao_filtro(self.b1)
        self.assertEqual(situacao["status"], "vencido")
        self.assertEqual(situacao["data_vencimento"], antiga + datetime.timedelta(days=182))

    def test_usa_a_troca_mais_recente(self):
        outra_coleta = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=10), status=Coleta.PUBLICADO
        )
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=outra_coleta,
            data_troca=datetime.date.today() - datetime.timedelta(days=10),
        )
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date.today()
        )
        situacao = situacao_filtro(self.b1)
        self.assertEqual(situacao["data_troca"], datetime.date.today())

    def test_rascunho_nao_conta_para_visitante(self):
        # data diferente da de self.coleta (setUp) — Coleta.data é unique=True
        rascunho = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=1)
        )  # rascunho
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=rascunho, data_troca=datetime.date.today()
        )
        publico = situacao_filtro(self.b1, apenas_publicadas=True)
        interno = situacao_filtro(self.b1, apenas_publicadas=False)
        self.assertEqual(publico["status"], "sem_registro")
        self.assertEqual(interno["status"], "ok")


class SalvarTrocaFiltroTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.coleta = Coleta.objects.create(data=datetime.date.today())

    def test_cria_troca(self):
        salvar_troca_filtro(self.coleta, self.b1, datetime.date.today())
        self.assertEqual(TrocaFiltro.objects.count(), 1)

    def test_data_none_nao_cria_nada(self):
        salvar_troca_filtro(self.coleta, self.b1, None)
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_atualiza_troca_existente(self):
        nova_data = datetime.date.today() - datetime.timedelta(days=1)
        salvar_troca_filtro(self.coleta, self.b1, datetime.date.today())
        salvar_troca_filtro(self.coleta, self.b1, nova_data)
        self.assertEqual(TrocaFiltro.objects.count(), 1)
        self.assertEqual(TrocaFiltro.objects.first().data_troca, nova_data)

    def test_data_none_remove_troca_existente(self):
        salvar_troca_filtro(self.coleta, self.b1, datetime.date.today())
        salvar_troca_filtro(self.coleta, self.b1, None)
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_relancar_mesma_data_nao_duplica(self):
        salvar_troca_filtro(self.coleta, self.b1, datetime.date.today())
        salvar_troca_filtro(self.coleta, self.b1, datetime.date.today())
        self.assertEqual(TrocaFiltro.objects.count(), 1)


class AvisoFiltroIncompativelTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def _coleta(self, data):
        return Coleta.objects.create(data=data, status=Coleta.PUBLICADO)

    def test_sem_troca_registrada_nao_avisa(self):
        coleta = self._coleta(datetime.date(2026, 9, 1))
        aviso = aviso_filtro_incompativel(self.b1, coleta, Resultado.FILTRO_VENCIDO)
        self.assertIsNone(aviso)

    def test_filtro_em_branco_nao_avisa(self):
        troca_coleta = self._coleta(datetime.date(2026, 1, 1))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 1, 1)
        )
        coleta = self._coleta(datetime.date(2026, 9, 1))
        aviso = aviso_filtro_incompativel(self.b1, coleta, "")
        self.assertIsNone(aviso)

    def test_bate_com_o_esperado_nao_avisa(self):
        troca_coleta = self._coleta(datetime.date(2026, 8, 1))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 8, 1)
        )
        coleta = self._coleta(datetime.date(2026, 9, 1))  # 31 dias depois — dentro
        aviso = aviso_filtro_incompativel(self.b1, coleta, Resultado.FILTRO_DENTRO)
        self.assertIsNone(aviso)

    def test_diverge_do_esperado_avisa(self):
        troca_coleta = self._coleta(datetime.date(2026, 1, 1))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 1, 1)
        )
        coleta = self._coleta(datetime.date(2026, 9, 1))  # bem mais de 182 dias — vencido
        aviso = aviso_filtro_incompativel(self.b1, coleta, Resultado.FILTRO_DENTRO)
        self.assertIsNotNone(aviso)
        self.assertIn("B1", aviso)
        self.assertIn("Vencido", aviso)
        self.assertIn("Dentro da validade", aviso)

    def test_ignora_troca_registrada_depois_desta_coleta(self):
        # A troca é de outubro; a coleta sendo lançada é de setembro —
        # não dá pra usar uma troca do futuro pra julgar o passado.
        coleta = self._coleta(datetime.date(2026, 9, 1))
        troca_coleta = self._coleta(datetime.date(2026, 10, 1))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=troca_coleta, data_troca=datetime.date(2026, 10, 1)
        )
        aviso = aviso_filtro_incompativel(self.b1, coleta, Resultado.FILTRO_VENCIDO)
        self.assertIsNone(aviso)

    def test_usa_a_troca_mais_proxima_antes_da_coleta(self):
        antiga = self._coleta(datetime.date(2026, 1, 1))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=antiga, data_troca=datetime.date(2026, 1, 1)
        )
        recente = self._coleta(datetime.date(2026, 8, 15))
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=recente, data_troca=datetime.date(2026, 8, 15)
        )
        coleta = self._coleta(datetime.date(2026, 9, 1))  # 17 dias após a troca de agosto — dentro
        aviso = aviso_filtro_incompativel(self.b1, coleta, Resultado.FILTRO_DENTRO)
        self.assertIsNone(aviso)
