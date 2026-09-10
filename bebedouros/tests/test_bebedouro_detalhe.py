import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado, TrocaFiltro
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

    def test_visitante_ve_menu_publico_nao_o_interno(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, ">Mapa<")
        self.assertNotContains(response, ">Sair<")
        self.assertNotContains(response, ">Coletas<")

    def test_logado_ve_menu_interno_nesta_pagina_tambem(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, ">Sair<")
        self.assertContains(response, ">Coletas<")

    def test_sem_dados_mostra_gota_vazia(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-vazia"')

    def test_fora_de_operacao_mostra_aviso_e_observacao(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(
            coleta=coleta,
            bebedouro=self.b1,
            fora_de_operacao=True,
            observacao="Bebedouro quebrado, aguardando manutenção.",
        )
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Fora de operação")
        self.assertContains(response, "Bebedouro quebrado, aguardando manutenção.")
        self.assertContains(response, "01/09/2026")

    def test_fora_de_operacao_mais_recente_sobrepoe_iqab_antigo(self):
        antiga = Coleta.objects.create(data=datetime.date(2026, 8, 1), status=Coleta.PUBLICADO)
        recente = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, fora_de_operacao=True)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Fora de operação")
        # "Excelente" pode aparecer legitimamente no histórico de coletas
        # recentes (a coleta antiga continua lá, com sua própria
        # classificação) — o que importa é o cabeçalho de status atual,
        # que deve refletir a coleta mais recente (fora de operação).
        self.assertNotContains(response, '<p class="cabecalho-classificacao">Excelente</p>')

    def test_fora_de_operacao_sem_observacao_nao_quebra(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, fora_de_operacao=True)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Fora de operação")

    def test_rascunho_fora_de_operacao_nao_aparece_para_visitante(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.RASCUNHO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, fora_de_operacao=True)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertNotContains(response, "Fora de operação")

    def test_com_dados_publicados_mostra_gota_colorida(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
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
        self.assertNotContains(response, "<summary>01/09/2026</summary>")
        self.assertContains(response, "Sem coletas para calcular a média.")

    def test_usuario_logado_ve_rascunho(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="gota gota-lg gota-excelente"')

    # --- Composição da nota agora é pública (correção pedida na conversa) ---

    def test_visitante_ve_composicao_da_nota(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Composição da nota")
        self.assertContains(response, "peso 30%")
        self.assertContains(response, "peso 50%")
        self.assertContains(response, "peso 20%")

    def test_motivo_aparece_so_quando_filtro_vencido(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Filtro fora da validade na data da coleta.")

    def test_sem_motivo_quando_filtro_em_dia(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertNotContains(response, "Filtro fora da validade na data da coleta.")

    # --- Manutenção do filtro ---

    def test_sem_registro_de_troca(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Sem registro de troca de filtro.")

    def test_troca_recente_mostra_check_verde(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=coleta, data_troca=datetime.date.today()
        )
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "✅")
        self.assertContains(response, "dentro da validade")

    def test_troca_vencida_mostra_x_vermelho_e_necessidade_de_troca(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        antiga = datetime.date.today() - datetime.timedelta(days=200)
        TrocaFiltro.objects.create(bebedouro=self.b1, coleta=coleta, data_troca=antiga)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "❌")
        self.assertContains(response, "Há necessidade de troca.")

    def test_troca_em_rascunho_nao_aparece_para_visitante(self):
        coleta = Coleta.objects.create(data=datetime.date.today())  # rascunho
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=coleta, data_troca=datetime.date.today()
        )
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Sem registro de troca de filtro.")

    # --- Coletas recentes ---

    def test_sem_coletas_mostra_mensagem(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Ainda não há coletas registradas para este bebedouro.")

    def test_mostra_no_maximo_5_coletas(self):
        for dias in [0, 15, 30, 45, 60, 75, 90]:
            data = datetime.date.today() - datetime.timedelta(days=dias)
            coleta = Coleta.objects.create(data=data, status=Coleta.PUBLICADO)
            Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
            recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<summary>", count=5)

    def test_primeira_coleta_aparece_aberta_as_outras_fechadas(self):
        atual = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        anterior = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=15), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=atual, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=anterior, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(atual)
        recalcular_coleta(anterior)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<details", count=2)
        self.assertContains(response, "<details open", count=1)

    def test_coleta_mostra_parametros_ao_abrir(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<summary>01/09/2026</summary>")
        self.assertContains(response, "Cloro Residual Livre")
        self.assertContains(response, "Ausente")

    def test_turbidez_abaixo_do_limite_mostra_menor_que(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        dados = {**RESULTADO_COMPLETO, "turbidez_valor": None, "turbidez_abaixo_limite": True}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "&lt;")

    def test_coleta_fora_de_operacao_nao_aparece_em_coletas_recentes(self):
        # A situação de fora de operação já aparece no topo da página —
        # não se repete em "Coletas recentes".
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, fora_de_operacao=True)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<summary>", count=0)
        self.assertContains(response, "Ainda não há coletas registradas para este bebedouro.")

    # --- Média das coletas recentes ---

    def test_sem_coletas_mostra_mensagem_de_media_vazia(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Sem coletas para calcular a média.")

    def test_media_aparece_aberta_sem_precisar_clicar(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Média das coletas recentes")
        self.assertContains(response, "Média do IQA-B")
        self.assertContains(response, "100 · Excelente")

    def test_media_de_duas_coletas(self):
        c1 = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        c2 = Coleta.objects.create(data=datetime.date(2026, 9, 15), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=c1, bebedouro=self.b1, **{**RESULTADO_COMPLETO, "cloro": Decimal("1.0")})
        Resultado.objects.create(coleta=c2, bebedouro=self.b1, **{**RESULTADO_COMPLETO, "cloro": Decimal("2.0")})
        recalcular_coleta(c1)
        recalcular_coleta(c2)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "1,500 mg/L Cl")

    # --- Gráfico (evolução) ---

    def test_grafico_padrao_e_12_meses_e_iqab(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'class="grafico-ponto"', count=1)
        self.assertContains(response, 'class="grafico-faixa faixa-excelente"')
        self.assertContains(response, ">12 meses<")

    def test_coordenadas_do_grafico_usam_ponto_decimal(self):
        import re

        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        conteudo = response.content.decode()
        self.assertIsNone(re.search(r'(cx|cy|x|y|width|height)="[0-9]+,[0-9]+"', conteudo))

    def test_seletor_de_periodo_muda_a_janela(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, 'href="?janela=6m"')

    def test_sem_dados_mostra_mensagem_no_lugar_do_grafico(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Ainda não há dados suficientes para o gráfico.")

    def test_gap_gera_dois_segmentos_de_linha(self):
        antiga = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=60), status=Coleta.PUBLICADO
        )
        meio = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=30), status=Coleta.PUBLICADO
        )
        recente = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=meio, bebedouro=self.b1, ph=Decimal("7.0"))  # incompleto
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        for c in (antiga, meio, recente):
            recalcular_coleta(c)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<polyline", count=2)
        self.assertContains(response, 'class="grafico-ponto"', count=2)
