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
        # Se o bebedouro tinha um IQA-B válido antes de sair de operação,
        # a página não deve mostrar essa nota antiga como se fosse a
        # situação atual — o aviso de fora de operação tem prioridade.
        antiga = Coleta.objects.create(data=datetime.date(2026, 8, 1), status=Coleta.PUBLICADO)
        recente = Coleta.objects.create(data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, fora_de_operacao=True)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Fora de operação")
        self.assertNotContains(response, "Excelente")

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
        self.assertNotContains(response, "Composição da nota")

    def test_interno_mostra_cartoes_com_pesos_e_notas(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Composição da nota")
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
        self.assertContains(response, "O que é monitorado:")
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

    def test_grafico_padrao_e_12_meses_e_iqab(self):
        coleta = Coleta.objects.create(
            data=datetime.date.today(), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        # Escopado a 'grafico-ponto' (não '<circle' sozinho) porque o
        # ícone da foto também usa um <circle> (o "sol" do ícone de
        # imagem), sem relação com o gráfico.
        self.assertContains(response, 'class="grafico-ponto"', count=1)
        self.assertContains(response, 'class="grafico-faixa faixa-excelente"')
        self.assertContains(response, ">12 meses<")

    def test_coordenadas_do_grafico_usam_ponto_decimal(self):
        # As coordenadas do SVG são números (ex.: y="158.8") — se o Django
        # aplicar a formatação de número em português (vírgula decimal),
        # o atributo vira "158,8" e o navegador não consegue mais
        # entender o desenho.
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
            data=datetime.date.today() - datetime.timedelta(days=60),
            status=Coleta.PUBLICADO,
        )
        meio = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=30),
            status=Coleta.PUBLICADO,
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

    def test_sem_quinzenas_anteriores_mostra_mensagem(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Nenhuma coleta anterior nos últimos 12 meses.")

    def test_quinzena_anterior_aparece_fechada_so_com_a_data(self):
        atual = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        anterior = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=20),
            status=Coleta.PUBLICADO,
        )
        Resultado.objects.create(coleta=atual, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=anterior, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(atual)
        recalcular_coleta(anterior)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        data_formatada = anterior.data.strftime("%d/%m/%Y")
        self.assertContains(response, f"<summary>{data_formatada}</summary>")
        self.assertContains(response, "100 · Excelente")

    def test_quinzena_anterior_mostra_os_parametros(self):
        atual = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        anterior = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=20),
            status=Coleta.PUBLICADO,
        )
        Resultado.objects.create(coleta=atual, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=anterior, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(atual)
        recalcular_coleta(anterior)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        # Aparece uma vez em "O que é monitorado" (situação atual) e outra
        # dentro do item expandido da quinzena anterior.
        self.assertContains(response, "Cloro Residual Livre", count=2)
        self.assertContains(response, "Coliformes Totais", count=2)

    def test_situacao_atual_nao_aparece_duplicada_no_historico(self):
        atual = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=atual, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(atual)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        data_formatada = atual.data.strftime("%d/%m/%Y")
        self.assertNotContains(response, f"<summary>{data_formatada}</summary>")

    def test_quinzena_fora_de_operacao_mostra_aviso(self):
        atual = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        anterior = Coleta.objects.create(
            data=datetime.date.today() - datetime.timedelta(days=20),
            status=Coleta.PUBLICADO,
        )
        Resultado.objects.create(coleta=atual, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=anterior, bebedouro=self.b1, fora_de_operacao=True)
        recalcular_coleta(atual)
        recalcular_coleta(anterior)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Fora de operação nesta data.")
