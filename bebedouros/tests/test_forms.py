import datetime

from django.test import SimpleTestCase

from bebedouros.forms import ResultadoRowForm


class ResultadoRowFormTrocaFiltroTests(SimpleTestCase):
    def test_campo_em_branco_e_valido(self):
        form = ResultadoRowForm(data={}, prefix="b1")
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["troca_filtro"])

    def test_aceita_data_iso(self):
        form = ResultadoRowForm(data={"b1-troca_filtro": "2026-09-01"}, prefix="b1")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["troca_filtro"], datetime.date(2026, 9, 1))

    def test_valor_inicial_renderiza_em_iso_nao_no_formato_brasileiro(self):
        # Trap: o widget de data padrão do Django, com LANGUAGE_CODE='pt-br',
        # renderiza o valor inicial como "01/09/2026" — um <input type="date">
        # ignora isso silenciosamente (exige yyyy-mm-dd). Sem forçar o formato
        # do widget, uma troca já lançada pareceria "esquecida" ao reabrir a
        # grade, mesmo estando salva.
        form = ResultadoRowForm(initial={"troca_filtro": datetime.date(2026, 9, 1)}, prefix="b1")
        self.assertIn('value="2026-09-01"', str(form["troca_filtro"]))
