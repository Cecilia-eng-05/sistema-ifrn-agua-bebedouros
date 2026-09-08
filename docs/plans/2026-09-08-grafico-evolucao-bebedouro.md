# Gráfico de Evolução do Bebedouro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the evolution graph on the página do bebedouro
(`DESENHO-PARTE-VISUAL.md` §5 item 5) — a hand-drawn inline SVG line
chart of the IQA-B or a single parameter over time, with a time-window
selector (6 meses / 12 meses / tudo) and a series selector (IQA-B or one
of the five numeric parameters), colored classification bands behind the
IQA-B line, and true gaps (no bridging line) wherever the selected series
has no value for a coleta.

**Architecture:** Three layers, same separation the rest of the project
already uses (`iqab.py` = pure calculation, `services.py` = DB queries,
`views.py`/templates = wiring and rendering):

1. `services.serie_historica(bebedouro, serie, janela, apenas_publicadas)`
   — a DB query returning chronological `{"data": date, "valor": Decimal | None}`
   points for one bebedouro. `valor` is `None` wherever that coleta has no
   usable value for the requested series — for `serie="iqab"` that means
   the row's IQA-B status isn't `CALCULADO` (matches the existing
   "incompleto" mechanism); for a parameter series it means that field is
   empty on that row. Reuses the same `apenas_publicadas` gate as
   `situacao_atual_bebedouro` (Task 1 of the previous plan), so the public
   and internal versions of the graph see exactly the data they're
   supposed to.
2. A new, Django-free module `bebedouros/grafico.py` — pure geometry.
   `montar_grafico(pontos, dominio_y=None)` turns a list of those points
   into SVG-ready pixel coordinates: x proportional to actual elapsed time
   (not just point index, so a real gap between two coletas reads as a gap
   on the axis), y scaled to a fixed 0–100 domain for the IQA-B (so the
   classification bands line up) or auto-scaled to the data for a
   parameter. Points are grouped into **segments**, broken wherever
   `valor` is `None` — the template draws one `<polyline>` per segment,
   which is what keeps a gap from being silently bridged by a straight
   line. This module has no Django imports, so its tests need no
   database — pure input/output, easy to reason about without a browser.
3. The view reads `?janela=` and `?serie=` query parameters (defaulting
   to `12m`/`iqab`), calls the two functions above, and passes the result
   to the template. The window/series switches are plain links with a
   query string — a full page reload, no JavaScript — consistent with the
   rest of this project, which has none.

**Tech Stack:** Same as the rest of the project — Django 5.2,
server-rendered HTML, inline SVG (same technique already used for the
wave decoration in `base.html`), no JS, no charting library, no new
dependencies. `SimpleTestCase` (no DB) for the pure geometry module,
`TestCase` + `self.client` for everything else — matching this project's
existing test style throughout.

**Spec:** `DESENHO-PARTE-VISUAL.md` §5 item 5 and §8 decision 5. Builds on
`docs/plans/2026-09-08-pagina-do-bebedouro-essenciais.md` (already
implemented) — this plan only adds the graph section to the existing
`bebedouro_detalhe` view/template, no new URL.

## Global Constraints

(Same as the two previous plans — Portuguese UI text, no external
JS/CSS/dependencies, reuse the shared `.gota`/faixa color tokens rather
than inventing new ones, `apenas_publicadas` gates public visitors the
same way it already does for the rest of the page.)

- The window filter is an approximation, not calendar-exact: "6 meses" =
  182 days, "12 meses" = 365 days, counted back from today. Good enough
  for a display filter; documented here so nobody mistakes it for a
  precise calendar calculation later.
- Only the five numeric QFQ/monitoring parameters are chartable as their
  own series: Cloro, Condutividade, Nitrato, Turbidez, pH. Coliformes
  Totais, E. coli (AUSENTE/PRESENTE, not numeric) and Situação do Filtro
  (categorical) are not — matches what `DESENHO-PARTE-VISUAL.md` §5 item 5
  says ("cloro, turbidez, pH, etc.").
- The colored classification bands only make sense on the IQA-B's fixed
  0–100 scale — they are never drawn behind a parameter series, whose
  y-axis is a different unit and range entirely.

---

### Task 1: Data layer — `serie_historica`

**Files:**
- Modify: `bebedouros/services.py`
- Test: `bebedouros/tests/test_services.py`

**Interfaces:**
- Produces: `serie_historica(bebedouro, serie, janela, apenas_publicadas=False) -> list[dict]`
  — chronological list of `{"data": date, "valor": Decimal | None}`.
  `serie` is one of `"iqab"`, `"cloro"`, `"condutividade"`, `"nitrato"`,
  `"turbidez"`, `"ph"`. `janela` is `"6m"`, `"12m"`, or `"tudo"`.
- Produces: `SERIES_LABELS` (dict, série key → display label) and
  `JANELAS_LABELS` (dict, janela key → display label) — used by Task 3 to
  build the selector links without hardcoding labels twice.

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_services.py`:

```python
from bebedouros.services import serie_historica
```

(add `serie_historica` to the existing multi-line import block)

```python
class SerieHistoricaTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)

    def _coleta(self, dias_atras, **overrides):
        data = datetime.date.today() - datetime.timedelta(days=dias_atras)
        coleta = Coleta.objects.create(data=data, **overrides)
        return coleta

    def test_serie_iqab_usa_a_nota_quando_calculado(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "iqab", "tudo")
        self.assertEqual(len(pontos), 1)
        self.assertEqual(pontos[0]["valor"], Decimal("100"))

    def test_serie_iqab_fica_none_quando_incompleto(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "iqab", "tudo")
        self.assertEqual(len(pontos), 1)
        self.assertIsNone(pontos[0]["valor"])

    def test_serie_de_parametro_aparece_mesmo_com_iqab_incompleto(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.2"))
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "ph", "tudo")
        self.assertEqual(pontos[0]["valor"], Decimal("7.2"))

    def test_linha_totalmente_vazia_nao_entra_na_serie(self):
        self._coleta(10)  # coleta existe, mas sem nenhum Resultado criado
        pontos = serie_historica(self.b1, "iqab", "tudo")
        self.assertEqual(pontos, [])

    def test_fora_de_operacao_nao_entra_na_serie(self):
        coleta = self._coleta(10)
        Resultado.objects.create(
            coleta=coleta, bebedouro=self.b1, fora_de_operacao=True, ph=Decimal("7.0")
        )
        pontos = serie_historica(self.b1, "ph", "tudo")
        self.assertEqual(pontos, [])

    def test_janela_6m_exclui_coleta_mais_antiga(self):
        antiga = self._coleta(400)
        recente = self._coleta(10)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        pontos = serie_historica(self.b1, "iqab", "6m")
        self.assertEqual(len(pontos), 1)
        self.assertEqual(pontos[0]["data"], recente.data)

    def test_janela_tudo_inclui_tudo(self):
        antiga = self._coleta(400)
        recente = self._coleta(10)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(antiga)
        recalcular_coleta(recente)
        pontos = serie_historica(self.b1, "iqab", "tudo")
        self.assertEqual(len(pontos), 2)

    def test_pontos_em_ordem_cronologica(self):
        recente = self._coleta(5)
        antiga = self._coleta(50)
        Resultado.objects.create(coleta=recente, bebedouro=self.b1, **RESULTADO_COMPLETO)
        Resultado.objects.create(coleta=antiga, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(recente)
        recalcular_coleta(antiga)
        pontos = serie_historica(self.b1, "iqab", "tudo")
        self.assertEqual([p["data"] for p in pontos], [antiga.data, recente.data])

    def test_apenas_publicadas_ignora_rascunho(self):
        coleta = self._coleta(10)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        pontos = serie_historica(self.b1, "iqab", "tudo", apenas_publicadas=True)
        self.assertEqual(pontos, [])

    def test_turbidez_abaixo_do_limite_ainda_entra_com_o_numero(self):
        coleta = self._coleta(10)
        dados = {**RESULTADO_COMPLETO, "turbidez_valor": Decimal("0.751"), "turbidez_abaixo_limite": True}
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **dados)
        pontos = serie_historica(self.b1, "turbidez", "tudo")
        self.assertEqual(pontos[0]["valor"], Decimal("0.751"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'serie_historica'`.

- [ ] **Step 3: Implement**

In `bebedouros/services.py`, add `import datetime` at the very top of the
file (before the `django.utils` import). Then add, at the end of the
file:

```python
CAMPO_SERIE = {
    "cloro": "cloro",
    "condutividade": "condutividade",
    "nitrato": "nitrato",
    "turbidez": "turbidez_valor",
    "ph": "ph",
}

SERIES_LABELS = {
    "iqab": "IQA-B",
    "cloro": "Cloro",
    "condutividade": "Condutividade",
    "nitrato": "Nitrato",
    "turbidez": "Turbidez",
    "ph": "pH",
}

JANELA_DIAS = {"6m": 182, "12m": 365}
JANELAS_LABELS = {"6m": "6 meses", "12m": "12 meses", "tudo": "Tudo"}


def serie_historica(bebedouro, serie, janela, apenas_publicadas=False):
    """Pontos da série 'serie' ('iqab' ou uma chave de CAMPO_SERIE) deste
    bebedouro, para o gráfico de evolução. 'janela' é uma chave de
    JANELA_DIAS ou 'tudo'. Retorna uma lista, em ordem cronológica, de
    {"data": date, "valor": Decimal ou None} — valor None marca um
    intervalo sem dado (o gráfico não deve emendar uma linha por cima
    desse ponto)."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro, fora_de_operacao=False)
        .select_related("coleta")
        .order_by("coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    if janela in JANELA_DIAS:
        limite = datetime.date.today() - datetime.timedelta(days=JANELA_DIAS[janela])
        resultados = resultados.filter(coleta__data__gte=limite)

    pontos = []
    for resultado in resultados:
        if resultado.esta_vazio():
            continue
        if serie == "iqab":
            valor = resultado.iqab if resultado.iqab_status == iqab.CALCULADO else None
        else:
            valor = getattr(resultado, CAMPO_SERIE[serie])
        pontos.append({"data": resultado.coleta.data, "valor": valor})
    return pontos
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: all tests in the file PASS, including every pre-existing one.

- [ ] **Step 5: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: serie_historica — pontos de IQA-B ou parâmetro no tempo, para o gráfico

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Geometria pura do gráfico — `bebedouros/grafico.py`

**Files:**
- Create: `bebedouros/grafico.py`
- Test: Create `bebedouros/tests/test_grafico.py`

**Interfaces:**
- Produces: `montar_grafico(pontos, dominio_y=None) -> dict | None`.
  `pontos` is the list `serie_historica` returns. `dominio_y` is `(min, max)`
  to force a fixed y-axis (pass `(0, 100)` for the IQA-B so the bands line
  up); `None` auto-scales to the data (used for a parameter series).
  Returns `None` when there is no point with a value at all (nothing to
  draw). Otherwise a dict: `{"largura", "altura", "area_esq", "area_dir",
  "area_topo", "area_base", "largura_area", "segmentos", "faixas",
  "data_min", "data_max"}`
  — `segmentos` is a list of point-lists (`{"x", "y", "data", "valor"}`,
  pixel coordinates in the SVG's own units), broken at every `None` value
  in the input; `faixas` is `None` unless `dominio_y == (0, 100)`, in
  which case it's the 5 classification bands as
  `{"y", "altura", "slug"}` (slug matches the existing `gota-*`/`chip-*`
  slugs: `critica`, `ruim`, `regular`, `boa`, `excelente`).
- Consumes: nothing from Django — pure functions, `datetime`/`decimal`
  only.

- [ ] **Step 1: Write the failing tests**

Create `bebedouros/tests/test_grafico.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_grafico -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'bebedouros.grafico'`.

- [ ] **Step 3: Implement**

Create `bebedouros/grafico.py`:

```python
"""Geometria do gráfico de evolução do bebedouro.

Funções puras (sem Django, sem banco): transformam uma série de pontos
{"data": date, "valor": Decimal ou None} nas coordenadas prontas para
desenhar um SVG. Segue o mesmo espírito de bebedouros/iqab.py — uma conta
isolada, fácil de testar sozinha, chamada pela view em views.py e
desenhada pelo template bebedouro_detalhe.html.
"""

LARGURA = 760
ALTURA = 220
MARGEM_ESQ = 34
MARGEM_DIR = 10
MARGEM_TOPO = 10
MARGEM_BASE = 24

# (nota mínima, nota máxima, slug) — mesmos slugs de faixa usados pelas
# classes .gota-*/.chip-* já existentes (ver base.html).
FAIXAS_IQAB = [
    (0, 20, "critica"),
    (20, 40, "ruim"),
    (40, 60, "regular"),
    (60, 80, "boa"),
    (80, 100, "excelente"),
]


def _escala(valor, minimo, maximo, destino_min, destino_max):
    if maximo == minimo:
        return (destino_min + destino_max) / 2
    fracao = (valor - minimo) / (maximo - minimo)
    return destino_min + fracao * (destino_max - destino_min)


def montar_grafico(pontos, dominio_y=None):
    """pontos: lista de {"data": date, "valor": Decimal ou None}, em
    ordem cronológica. dominio_y: (mínimo, máximo) fixo — passe (0, 100)
    para o IQA-B, para as faixas baterem com a escala; None calcula a
    escala a partir dos valores presentes (usado para um parâmetro).

    Retorna None se não houver nenhum ponto com valor. Senão, um dict
    com as coordenadas prontas para o template desenhar — ver o
    docstring do módulo e o plano de implementação para o formato."""
    com_valor = [p for p in pontos if p["valor"] is not None]
    if not com_valor:
        return None

    area_esq, area_dir = MARGEM_ESQ, LARGURA - MARGEM_DIR
    area_topo, area_base = MARGEM_TOPO, ALTURA - MARGEM_BASE

    datas = [p["data"] for p in pontos]
    data_min, data_max = min(datas), max(datas)
    intervalo_dias = (data_max - data_min).days or 1

    if dominio_y is not None:
        y_min, y_max = dominio_y
    else:
        valores = [float(p["valor"]) for p in com_valor]
        y_min, y_max = min(valores), max(valores)
        if y_min == y_max:
            y_min, y_max = y_min - 1, y_max + 1
        else:
            folga = (y_max - y_min) * 0.1
            y_min -= folga
            y_max += folga
        y_min = min(y_min, 0)

    segmentos = []
    atual = []
    for p in pontos:
        if p["valor"] is None:
            if atual:
                segmentos.append(atual)
                atual = []
            continue
        x = _escala((p["data"] - data_min).days, 0, intervalo_dias, area_esq, area_dir)
        y = _escala(float(p["valor"]), y_min, y_max, area_base, area_topo)
        atual.append({"x": x, "y": y, "data": p["data"], "valor": p["valor"]})
    if atual:
        segmentos.append(atual)

    faixas = None
    if dominio_y == (0, 100):
        faixas = []
        for minimo, maximo, slug in FAIXAS_IQAB:
            y_topo = _escala(maximo, y_min, y_max, area_base, area_topo)
            y_base = _escala(minimo, y_min, y_max, area_base, area_topo)
            faixas.append({"y": y_topo, "altura": y_base - y_topo, "slug": slug})

    return {
        "largura": LARGURA,
        "altura": ALTURA,
        "area_esq": area_esq,
        "area_dir": area_dir,
        "area_topo": area_topo,
        "area_base": area_base,
        "largura_area": area_dir - area_esq,
        "segmentos": segmentos,
        "faixas": faixas,
        "data_min": data_min,
        "data_max": data_max,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_grafico -v 2`
Expected: all `MontarGraficoTests` PASS.

- [ ] **Step 5: Commit**

```bash
git add bebedouros/grafico.py bebedouros/tests/test_grafico.py
git commit -m "feat: grafico.montar_grafico — geometria pura do gráfico de evolução (SVG)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Seção do gráfico na página do bebedouro

**Files:**
- Modify: `bebedouros/views.py`
- Modify: `bebedouros/templates/bebedouros/bebedouro_detalhe.html`
- Modify: `bebedouros/templates/bebedouros/base.html`
- Test: Modify `bebedouros/tests/test_bebedouro_detalhe.py`

**Interfaces:**
- Consumes: `serie_historica`, `SERIES_LABELS`, `JANELAS_LABELS` (Task 1);
  `grafico.montar_grafico` (Task 2).

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_bebedouro_detalhe.py`:

```python
    def test_grafico_padrao_e_12_meses_e_iqab(self):
        coleta = Coleta.objects.create(
            data=datetime.date.today(), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<circle", count=1)
        self.assertContains(response, 'class="grafico-faixa faixa-excelente"')
        # o link já ativo não deve levar a pessoa pra ele mesmo de novo
        self.assertContains(response, ">12 meses<")

    def test_seletor_de_janela_preserva_a_serie_escolhida(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/?serie=ph")
        self.assertContains(response, 'href="?janela=6m&serie=ph"')

    def test_seletor_de_serie_preserva_a_janela_escolhida(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/?janela=6m")
        self.assertContains(response, 'href="?janela=6m&serie=ph"')

    def test_serie_de_parametro_nao_mostra_faixas_coloridas(self):
        coleta = Coleta.objects.create(
            data=datetime.date.today(), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/?serie=ph")
        # Checa o atributo class do próprio elemento, não o texto solto —
        # 'grafico-faixa' sozinho também aparece na definição de cor no
        # CSS compartilhado, presente em toda página independentemente do
        # gráfico (mesma armadilha encontrada nos testes da gota).
        self.assertNotContains(response, 'class="grafico-faixa')

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
        self.assertContains(response, "<circle", count=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_bebedouro_detalhe -v 2`
Expected: FAIL — none of the graph markup exists yet.

- [ ] **Step 3: Wire up the view**

In `bebedouros/views.py`, add the import (near the existing `from . import iqab`):

```python
from . import grafico
```

Change the services import to add the three new names:

```python
from .services import (
    JANELAS_LABELS,
    SERIES_LABELS,
    alertas_internos,
    linhas_faltantes,
    publicar_coleta,
    recalcular_coleta,
    serie_historica,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
)
```

In `bebedouro_detalhe`, replace:

```python
    return render(
        request,
        "bebedouros/bebedouro_detalhe.html",
        {"bebedouro": bebedouro, "situacao": situacao, "pesos_iqab": pesos_iqab},
    )
```

with:

```python
    janela = request.GET.get("janela", "12m")
    if janela not in ("6m", "12m", "tudo"):
        janela = "12m"
    serie = request.GET.get("serie", "iqab")
    if serie not in SERIES_LABELS:
        serie = "iqab"

    pontos = serie_historica(bebedouro, serie, janela, apenas_publicadas=apenas_publicadas)
    dominio_y = (0, 100) if serie == "iqab" else None
    grafico_dados = grafico.montar_grafico(pontos, dominio_y=dominio_y)

    return render(
        request,
        "bebedouros/bebedouro_detalhe.html",
        {
            "bebedouro": bebedouro,
            "situacao": situacao,
            "pesos_iqab": pesos_iqab,
            "grafico": grafico_dados,
            "janela": janela,
            "serie": serie,
            "janelas_labels": JANELAS_LABELS,
            "series_labels": SERIES_LABELS,
        },
    )
```

- [ ] **Step 4: Add the CSS**

In `bebedouros/templates/bebedouros/base.html`, find:

```css
    .cartao-indice-motivo { font-size: 13px; color: #8a5a00; }
```

Replace with (keeps that line, adds the graph rules after it):

```css
    .cartao-indice-motivo { font-size: 13px; color: #8a5a00; }

    /* Gráfico de evolução */
    .grafico-selecao {
      display: flex; flex-wrap: wrap; gap: 6px 18px; margin-bottom: 12px; font-size: 14px;
    }
    .grafico-selecao-grupo { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
    .grafico-selecao-rotulo { color: var(--tinta-suave); }
    .grafico-selecao a { color: var(--tinta-suave); text-decoration: none; }
    .grafico-selecao a:hover { text-decoration: underline; }
    .grafico-selecao a.ativo { color: var(--profunda); font-weight: 700; }
    .grafico-svg { width: 100%; height: auto; }
    .grafico-linha { fill: none; stroke: var(--profunda-2); stroke-width: 2; }
    .grafico-ponto { fill: var(--profunda-2); }
    .grafico-eixo-data { font-size: 11px; fill: var(--tinta-suave); }
    .grafico-faixa.faixa-excelente { fill: #dbf1e6; }
    .grafico-faixa.faixa-boa { fill: #dcecf6; }
    .grafico-faixa.faixa-regular { fill: #faefd5; }
    .grafico-faixa.faixa-ruim { fill: #f7e2d3; }
    .grafico-faixa.faixa-critica { fill: #f6dcdc; }
    .grafico-vazio { color: var(--tinta-suave); }
```

- [ ] **Step 5: Add the template section**

In `bebedouros/templates/bebedouros/bebedouro_detalhe.html`, find the end
of the file:

```html
  <section class="parametros">
    <h2>O que é monitorado:</h2>
    <div class="painel">
      <table>
        <thead><tr><th>Parâmetro</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Cloro Residual Livre</td><td>{{ situacao.resultado.cloro|default:"—" }} mg/L Cl₂</td></tr>
          <tr><td>Condutividade Elétrica</td><td>{{ situacao.resultado.condutividade|default:"—" }} µS/cm</td></tr>
          <tr><td>Nitrato</td><td>{{ situacao.resultado.nitrato|default:"—" }} mg/L N</td></tr>
          <tr><td>Turbidez</td><td>{{ situacao.resultado.turbidez_texto|default:"—" }} UNT</td></tr>
          <tr><td>pH</td><td>{{ situacao.resultado.ph|default:"—" }}</td></tr>
          <tr><td>Coliformes Totais</td><td>{{ situacao.resultado.get_coliformes_totais_display|default:"—" }}</td></tr>
          <tr><td>E. coli</td><td>{{ situacao.resultado.get_ecoli_display|default:"—" }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
{% endblock %}
```

Replace with (keeps the `parametros` section, adds the graph section
right after it, before `{% endblock %}`):

```html
  <section class="parametros">
    <h2>O que é monitorado:</h2>
    <div class="painel">
      <table>
        <thead><tr><th>Parâmetro</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Cloro Residual Livre</td><td>{{ situacao.resultado.cloro|default:"—" }} mg/L Cl₂</td></tr>
          <tr><td>Condutividade Elétrica</td><td>{{ situacao.resultado.condutividade|default:"—" }} µS/cm</td></tr>
          <tr><td>Nitrato</td><td>{{ situacao.resultado.nitrato|default:"—" }} mg/L N</td></tr>
          <tr><td>Turbidez</td><td>{{ situacao.resultado.turbidez_texto|default:"—" }} UNT</td></tr>
          <tr><td>pH</td><td>{{ situacao.resultado.ph|default:"—" }}</td></tr>
          <tr><td>Coliformes Totais</td><td>{{ situacao.resultado.get_coliformes_totais_display|default:"—" }}</td></tr>
          <tr><td>E. coli</td><td>{{ situacao.resultado.get_ecoli_display|default:"—" }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="evolucao">
    <h2>Evolução</h2>
    <div class="grafico-selecao">
      <span class="grafico-selecao-grupo">
        <span class="grafico-selecao-rotulo">Período:</span>
        {% for chave, rotulo in janelas_labels.items %}
          <a href="?janela={{ chave }}&serie={{ serie }}" class="{% if chave == janela %}ativo{% endif %}">{{ rotulo }}</a>
        {% endfor %}
      </span>
      <span class="grafico-selecao-grupo">
        <span class="grafico-selecao-rotulo">Mostrar:</span>
        {% for chave, rotulo in series_labels.items %}
          <a href="?janela={{ janela }}&serie={{ chave }}" class="{% if chave == serie %}ativo{% endif %}">{{ rotulo }}</a>
        {% endfor %}
      </span>
    </div>

    {% if grafico %}
      <svg class="grafico-svg" viewBox="0 0 {{ grafico.largura }} {{ grafico.altura }}">
        {% if grafico.faixas %}
          {% for faixa in grafico.faixas %}
            <rect class="grafico-faixa faixa-{{ faixa.slug }}" x="{{ grafico.area_esq }}" y="{{ faixa.y }}" width="{{ grafico.largura_area }}" height="{{ faixa.altura }}"></rect>
          {% endfor %}
        {% endif %}
        {% for segmento in grafico.segmentos %}
          <polyline class="grafico-linha" points="{% for p in segmento %}{{ p.x }},{{ p.y }} {% endfor %}"></polyline>
          {% for p in segmento %}
            <circle class="grafico-ponto" cx="{{ p.x }}" cy="{{ p.y }}" r="3.5"><title>{{ p.data|date:"d/m/Y" }}: {{ p.valor }}</title></circle>
          {% endfor %}
        {% endfor %}
        <text class="grafico-eixo-data" x="{{ grafico.area_esq }}" y="{{ grafico.altura|add:"-6" }}">{{ grafico.data_min|date:"d/m/Y" }}</text>
        <text class="grafico-eixo-data" x="{{ grafico.area_dir }}" y="{{ grafico.altura|add:"-6" }}" text-anchor="end">{{ grafico.data_max|date:"d/m/Y" }}</text>
      </svg>
    {% else %}
      <p class="grafico-vazio">Ainda não há dados suficientes para o gráfico.</p>
    {% endif %}
  </section>
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_bebedouro_detalhe -v 2`
Expected: all tests PASS.

- [ ] **Step 7: Run the full test suite**

Run: `python manage.py test`
Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add bebedouros/views.py bebedouros/templates/bebedouros/bebedouro_detalhe.html bebedouros/templates/bebedouros/base.html bebedouros/tests/test_bebedouro_detalhe.py
git commit -m "feat: gráfico de evolução na página do bebedouro (IQA-B ou parâmetro, com janela)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Manual check (do this after Task 3)

```bash
python manage.py runserver
```

1. Open a bebedouro with a few published coletas spread over time. Confirm
   the IQA-B line appears over the 5 colored bands, points sit roughly
   where you'd expect for their score, and hovering a point (mouse, no
   click needed) shows its date and value in a native browser tooltip.
2. Click "pH" (or another parameter). Confirm the colored bands disappear
   and the line rescales to a sensible range for that parameter.
3. Click "6 meses" with data older than that on record. Confirm older
   points drop off and the line reflows to what's left.
4. If you have a coleta with a missing parameter (an "incompleto" IQA-B
   row, or a specific field left blank), confirm the line visibly breaks
   there — two separate line segments, not one line quietly skipping the
   gap.
5. Log out and revisit a bebedouro that has only draft (unpublished) data.
   Confirm the graph shows the "sem dados suficientes" message instead of
   drawing an empty/broken chart.
