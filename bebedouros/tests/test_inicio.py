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


class InicioTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")

    def test_requer_login(self):
        self.client.logout()
        response = self.client.get("/inicio/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/entrar/", response["Location"])

    def test_lista_todos_os_bebedouros(self):
        Bebedouro.objects.create(numero=1, local="Mesas verdes")
        Bebedouro.objects.create(numero=2, local="Piscinas")
        response = self.client.get("/inicio/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "B1")
        self.assertContains(response, "Mesas verdes")
        self.assertContains(response, "B2")
        self.assertContains(response, "Piscinas")

    def test_bebedouro_sem_resultado_mostra_gota_vazia(self):
        Bebedouro.objects.create(numero=1)
        response = self.client.get("/inicio/")
        self.assertContains(response, 'class="gota gota-sm gota-vazia"')

    def test_bebedouro_com_iqab_mostra_gota_colorida_e_data(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get("/inicio/")
        self.assertContains(response, 'class="gota gota-sm gota-excelente"')
        self.assertContains(response, "01/09/2026")
        self.assertContains(response, "Excelente")

    def test_alerta_iqab_baixo_aparece(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        dados = {
            **RESULTADO_COMPLETO,
            "cloro": Decimal("0.1"),
            "ph": Decimal("5"),
            "nitrato": Decimal("20"),
            "ecoli": Resultado.PRESENTE,
        }
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get("/inicio/")
        self.assertNotContains(response, "Nenhum bebedouro abaixo de 40.")
        self.assertContains(response, "B1", count=2)

    def test_alerta_filtro_vencido_aparece(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get("/inicio/")
        self.assertNotContains(response, "Nenhum filtro vencido.")
        self.assertContains(response, "B1", count=2)

    def test_alerta_quinzena_sem_dados_aparece(self):
        Bebedouro.objects.create(numero=1)
        Coleta.objects.create(data=datetime.date(2026, 9, 1))
        response = self.client.get("/inicio/")
        self.assertNotContains(
            response, "Todos os bebedouros ativos têm dado na última coleta."
        )
        self.assertContains(response, "B1", count=2)

    def test_menu_tem_link_para_inicio(self):
        response = self.client.get("/inicio/")
        self.assertContains(response, 'href="/inicio/"')
