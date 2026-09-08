# Tela Início (interna) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new internal "Início" screen — the panorama of the 15
bebedouros (three internal alerts + a table with each bebedouro's current
IQA-B) — as the first piece of the visual layer described in
`DESENHO-PARTE-VISUAL.md`, running locally so the orientanda can see it and
show the orientadora before anything is hosted.

**Architecture:** Two new pure-data functions in `bebedouros/services.py`
compute "current situation per bebedouro" and "the three internal alerts"
from existing models — no new models, no migrations. A new `inicio` view
renders them into a new template that reuses the existing `base.html`
shell and its established color palette. The "gota d'água" (teardrop) is a
small reusable CSS shape added to `base.html`'s existing `<style>` block,
so later screens (mapa, página do bebedouro) can reuse the same classes.
Publishing a coleta is rewired to redirect to Início instead of the coleta
list, per the design doc's navigation decision.

**Tech Stack:** Django 5.2 (already in the project), Django's test client
and `TestCase` (already the project's test style), server-rendered HTML +
inline `<style>` in `base.html` (no external CSS/JS — the project has no
frontend build step and none is being introduced).

**Spec:** `DESENHO-PARTE-VISUAL.md` (sections 3, 8.11, 8.12) and
`DEFINICAO-DO-PROJETO.md` (section 11, the three internal alerts). This
plan implements only the "Início (interna, nova tela)" piece — the mapa
público, a página do bebedouro, e as abas Alertas/Parâmetros are separate,
later plans (see `DESENHO-PARTE-VISUAL.md` section 10 for the order).

## Global Constraints

- All UI text is Portuguese (pt-BR); code, comments in existing files
  follow whatever language that file already uses (this codebase mixes
  English prose in some places and Portuguese domain terms throughout —
  follow the file being edited).
- No external JS/CSS libraries, no CDN links, no new dependencies in
  `requirements.txt`. Everything server-rendered, consistent with the
  existing `base.html`.
- The "gota d'água" is the shared identity element (DESENHO-PARTE-VISUAL.md
  §3): a teardrop shape, colored by IQA-B classification (Excelente/Boa/
  Regular/Ruim/Crítica), shown empty/gray when there is no calculated
  IQA-B. Build it as reusable CSS now — later plans (mapa, página do
  bebedouro) reuse the same classes, do not redefine them.
- "IQA-B baixo" and "filtro vencido" alerts only ever consider **active**
  bebedouros (`Bebedouro.ativo`); "quinzena sem dados" already inherits
  this from the existing `linhas_faltantes()` function. Do not alter that
  existing function.
- Every new/changed view stays behind `@login_required`, matching every
  existing view in `bebedouros/views.py`.
- Tests follow this project's existing style exactly: `django.test.TestCase`
  subclasses, `self.client` for view tests, plain `assertContains` /
  `assertEqual` / `assertRedirects` — no new test utilities or fixtures
  framework.

---

### Task 1: Data layer — situação atual e alertas internos

**Files:**
- Modify: `bebedouros/services.py`
- Test: `bebedouros/tests/test_services.py`

**Interfaces:**
- Produces: `situacao_atual_bebedouros() -> list[dict]`, one dict per
  `Bebedouro` (same order as `Bebedouro.objects.all()`, i.e. by número),
  each `{"bebedouro": Bebedouro, "resultado": Resultado | None, "data": date | None}`.
  `resultado` is the most recent non-empty, non-"fora de operação"
  `Resultado` for that bebedouro (by `coleta.data`), or `None` if it never
  had one. `data` is that resultado's coleta date, or `None`.
- Produces: `alertas_internos(situacoes) -> dict` — takes the list produced
  by `situacao_atual_bebedouros()` and returns
  `{"iqab_ruim": list[dict], "filtro_vencido": list[dict], "quinzena_sem_dados": list[str]}`.
  `iqab_ruim` and `filtro_vencido` are subsets of `situacoes` (same dict
  shape, restricted to active bebedouros). `quinzena_sem_dados` is exactly
  what `linhas_faltantes(Coleta.objects.first())` returns (a list of
  bebedouro código strings), or `[]` if there is no coleta at all.
- Consumes (existing): `Bebedouro`, `Coleta`, `Resultado` models; the
  `iqab` module's `CALCULADO` constant; the existing `linhas_faltantes()`
  function in the same file.

- [ ] **Step 1: Write the failing tests for `situacao_atual_bebedouros`**

Add to `bebedouros/tests/test_services.py`:

```python
from decimal import Decimal

from bebedouros.services import (
    alertas_internos,
    linhas_faltantes,
    recalcular_coleta,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'situacao_atual_bebedouros'`
(and `alertas_internos`, imported in the same statement).

- [ ] **Step 3: Implement `situacao_atual_bebedouros`**

In `bebedouros/services.py`, change the model import line and add the
function (keep `linhas_faltantes` and `recalcular_coleta` unchanged):

```python
from .models import Bebedouro, Coleta, Resultado
```

```python
def _ultimo_resultado_valido(bebedouro):
    """O Resultado mais recente deste bebedouro que tem algum dado de
    verdade — pula linhas vazias e linhas marcadas 'fora de operação'."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    for resultado in resultados:
        if not resultado.fora_de_operacao and not resultado.esta_vazio():
            return resultado
    return None


def situacao_atual_bebedouros():
    """Situação mais recente de cada bebedouro, para a tela Início.

    Retorna uma lista, na mesma ordem de Bebedouro.objects.all() (por
    número), de dicts: {"bebedouro": Bebedouro, "resultado": Resultado ou
    None, "data": date ou None}. 'resultado' é o resultado não vazio mais
    recente daquele bebedouro; None se o bebedouro nunca teve um
    lançamento com dado."""
    situacoes = []
    for bebedouro in Bebedouro.objects.all():
        resultado = _ultimo_resultado_valido(bebedouro)
        situacoes.append(
            {
                "bebedouro": bebedouro,
                "resultado": resultado,
                "data": resultado.coleta.data if resultado else None,
            }
        )
    return situacoes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: the 3 new `SituacaoAtualBebedourosTests` PASS. (`alertas_internos`
import still fails — next step fixes that.)

- [ ] **Step 5: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: situacao_atual_bebedouros — última análise válida de cada bebedouro

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Write the failing tests for `alertas_internos`**

Add to `bebedouros/tests/test_services.py`:

```python
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
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'alertas_internos'`.

- [ ] **Step 8: Implement `alertas_internos`**

Add to `bebedouros/services.py` (below `situacao_atual_bebedouros`):

```python
def alertas_internos(situacoes):
    """A partir da lista devolvida por situacao_atual_bebedouros(), monta
    os três alertas internos da tela Início: bebedouros ativos com IQA-B
    abaixo de 40, com filtro vencido, e os que faltam na coleta mais
    recente."""
    ativos = [s for s in situacoes if s["bebedouro"].ativo]
    iqab_ruim = [
        s
        for s in ativos
        if s["resultado"]
        and s["resultado"].iqab_status == iqab.CALCULADO
        and s["resultado"].iqab_classificacao in ("Ruim", "Crítica")
    ]
    filtro_vencido = [
        s
        for s in ativos
        if s["resultado"] and s["resultado"].filtro == Resultado.FILTRO_VENCIDO
    ]
    ultima_coleta = Coleta.objects.first()
    quinzena_sem_dados = linhas_faltantes(ultima_coleta) if ultima_coleta else []
    return {
        "iqab_ruim": iqab_ruim,
        "filtro_vencido": filtro_vencido,
        "quinzena_sem_dados": quinzena_sem_dados,
    }
```

(`iqab` is already imported at the top of `bebedouros/services.py` via
`from . import iqab` — no new import needed for it.)

- [ ] **Step 9: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: all `AlertasInternosTests` PASS, and all pre-existing tests in
this file (`LinhasFaltantesTests`) still PASS.

- [ ] **Step 10: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: alertas_internos — IQA-B baixo, filtro vencido, quinzena sem dados

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Tela Início — view, rota, template, identidade visual

**Files:**
- Modify: `bebedouros/views.py`
- Modify: `bebedouros/urls.py`
- Modify: `bebedouros/templates/bebedouros/base.html`
- Create: `bebedouros/templates/bebedouros/inicio.html`
- Test: Create `bebedouros/tests/test_inicio.py`

**Interfaces:**
- Consumes: `situacao_atual_bebedouros()` and `alertas_internos(situacoes)`
  from Task 1.
- Produces: URL name `"inicio"` resolving to `/inicio/`, used by Task 3
  (redirect after publishing) and by future plans (mapa público, página do
  bebedouro) that will link into/out of this screen.
- Produces: CSS classes `.gota`, `.gota-sm`, `.gota-vazia`,
  `.gota-excelente`, `.gota-boa`, `.gota-regular`, `.gota-ruim`,
  `.gota-critica` in `base.html` — the shared "gota d'água" component that
  later plans (mapa, página do bebedouro) reuse verbatim, at other sizes
  (a `.gota-lg` modifier can be added by a later plan without touching
  these).

- [ ] **Step 1: Write the failing tests**

Create `bebedouros/tests/test_inicio.py`:

```python
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
        self.assertContains(response, "gota-vazia")

    def test_bebedouro_com_iqab_mostra_gota_colorida_e_data(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get("/inicio/")
        self.assertContains(response, "gota-excelente")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_inicio -v 2`
Expected: FAIL — `404` on `/inicio/` (no such URL yet), so every test fails
either on the status-code/redirect assertion or on missing content.

- [ ] **Step 3: Add the URL**

In `bebedouros/urls.py`, add the new path (placed after `sair/`, before the
root path):

```python
urlpatterns = [
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="bebedouros/login.html"),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("inicio/", views.inicio, name="inicio"),
    path("", views.coleta_list, name="coleta_list"),
    path("coletas/nova/", views.coleta_nova, name="coleta_nova"),
    path("coletas/<int:pk>/lancamento/", views.lancamento, name="lancamento"),
    path("coletas/<int:pk>/publicar/", views.publicar, name="publicar"),
    path("coletas/<int:pk>/apagar/", views.apagar, name="apagar"),
]
```

- [ ] **Step 4: Add the view**

In `bebedouros/views.py`, change the services import line and add the view
function (near `coleta_list`, since it is also a plain read-only page):

```python
from .services import (
    alertas_internos,
    linhas_faltantes,
    publicar_coleta,
    recalcular_coleta,
    situacao_atual_bebedouros,
)
```

```python
@login_required
def inicio(request):
    situacoes = situacao_atual_bebedouros()
    alertas = alertas_internos(situacoes)
    return render(
        request,
        "bebedouros/inicio.html",
        {"situacoes": situacoes, "alertas": alertas},
    )
```

- [ ] **Step 5: Add the nav link in `base.html`**

In `bebedouros/templates/bebedouros/base.html`, find this block:

```html
      <nav>
        <a href="{% url 'coleta_list' %}">Coletas</a>
```

Replace with:

```html
      <nav>
        <a href="{% url 'inicio' %}">Início</a>
        <a href="{% url 'coleta_list' %}">Coletas</a>
```

- [ ] **Step 6: Add the gota and alert CSS to `base.html`**

In `bebedouros/templates/bebedouros/base.html`, find this line (end of the
existing rule block):

```css
    .lista-vazia { color: var(--tinta-suave); }
```

Replace with (adds the new rules right after it, keeps the existing rule):

```css
    .lista-vazia { color: var(--tinta-suave); }

    /* Alertas (tela Início) */
    .alertas h2 { font-size: 16px; margin: 22px 0 10px; }
    .alerta-bloco {
      display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 10px;
      padding: 10px 0; border-bottom: 1px solid var(--borda);
    }
    .alerta-bloco:last-child { border-bottom: 0; }
    .alerta-titulo { font-weight: 600; min-width: 160px; }
    .alerta-ok { color: var(--tinta-suave); font-size: 14px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip {
      padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 600;
      border: 1px solid transparent;
    }
    .chip-ruim { background: #f7e2d3; color: #9a4a1a; border-color: #eccbab; }
    .chip-critica { background: var(--erro-bg); color: #922; border-color: var(--erro-bd); }
    .chip-vencido { background: var(--aviso-bg); color: #8a5a00; border-color: var(--aviso-bd); }

    /* Gota d'água — identidade visual do IQA-B (DESENHO-PARTE-VISUAL.md §3).
       Reaproveitada, nos mesmos nomes de classe, pelo mapa público e pela
       página do bebedouro em planos futuros. */
    .gota {
      display: inline-block; border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
    }
    .gota-sm { width: 14px; height: 14px; }
    .gota-vazia { background: #e4ecf0; border: 1px solid var(--borda); }
    .gota-excelente { background: #1c6b4e; }
    .gota-boa { background: #185a86; }
    .gota-regular { background: #c99a2e; }
    .gota-ruim { background: #b9601f; }
    .gota-critica { background: #a32222; }
```

- [ ] **Step 7: Create the template**

Create `bebedouros/templates/bebedouros/inicio.html`:

```html
{% extends "bebedouros/base.html" %}
{% block titulo %}Início — Monitoramento da Água — IFRN-CNAT{% endblock %}
{% block conteudo %}
  <h1>Início</h1>

  <section class="alertas">
    <h2>Alertas</h2>

    <div class="alerta-bloco">
      <span class="alerta-titulo">IQA-B baixo</span>
      {% if alertas.iqab_ruim %}
        <span class="chips">
          {% for s in alertas.iqab_ruim %}
            <span class="chip chip-{{ s.resultado.iqab_faixa_slug }}">{{ s.bebedouro.codigo }}</span>
          {% endfor %}
        </span>
      {% else %}
        <span class="alerta-ok">Nenhum bebedouro abaixo de 40.</span>
      {% endif %}
    </div>

    <div class="alerta-bloco">
      <span class="alerta-titulo">Filtro vencido</span>
      {% if alertas.filtro_vencido %}
        <span class="chips">
          {% for s in alertas.filtro_vencido %}
            <span class="chip chip-vencido">{{ s.bebedouro.codigo }}</span>
          {% endfor %}
        </span>
      {% else %}
        <span class="alerta-ok">Nenhum filtro vencido.</span>
      {% endif %}
    </div>

    <div class="alerta-bloco">
      <span class="alerta-titulo">Quinzena sem dados</span>
      {% if alertas.quinzena_sem_dados %}
        <span class="chips">
          {% for codigo in alertas.quinzena_sem_dados %}
            <span class="chip chip-vencido">{{ codigo }}</span>
          {% endfor %}
        </span>
      {% else %}
        <span class="alerta-ok">Todos os bebedouros ativos têm dado na última coleta.</span>
      {% endif %}
    </div>
  </section>

  <div class="painel" style="margin-top:20px;">
    <table>
      <thead>
        <tr><th></th><th>Código</th><th>Local</th><th>IQA-B</th><th>Última análise</th></tr>
      </thead>
      <tbody>
      {% for s in situacoes %}
        <tr>
          <td>
            {% if s.resultado.iqab_status == "calculado" %}
              <span class="gota gota-sm gota-{{ s.resultado.iqab_faixa_slug }}" title="{{ s.resultado.iqab_classificacao }}"></span>
            {% else %}
              <span class="gota gota-sm gota-vazia"></span>
            {% endif %}
          </td>
          <td class="cod">{{ s.bebedouro.codigo }}</td>
          <td>{{ s.bebedouro.local }}</td>
          <td>{{ s.resultado.iqab_texto|default:"—" }}</td>
          <td>{{ s.data|date:"d/m/Y"|default:"—" }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
{% endblock %}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_inicio -v 2`
Expected: all `InicioTests` PASS.

- [ ] **Step 9: Run the full test suite**

Run: `python manage.py test`
Expected: all tests PASS (this confirms the `base.html` and `urls.py`
changes did not break any existing page).

- [ ] **Step 10: Commit**

```bash
git add bebedouros/views.py bebedouros/urls.py bebedouros/templates/bebedouros/base.html bebedouros/templates/bebedouros/inicio.html bebedouros/tests/test_inicio.py
git commit -m "feat: tela Início — panorama dos 15 bebedouros com os 3 alertas internos

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Publicar leva para Início

**Files:**
- Modify: `bebedouros/views.py:publicar`
- Modify: `bebedouros/tests/test_publicar.py`

**Interfaces:**
- Consumes: URL name `"inicio"` (Task 2).

- [ ] **Step 1: Update the existing test to the new expected redirect**

In `bebedouros/tests/test_publicar.py`, in `test_publish_with_confirmation`,
change:

```python
        self.assertRedirects(response, "/")
```

to:

```python
        self.assertRedirects(response, "/inicio/")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_publicar.PublicarTests.test_publish_with_confirmation -v 2`
Expected: FAIL — redirected to `/` instead of `/inicio/`.

- [ ] **Step 3: Change the redirect target**

In `bebedouros/views.py`, inside `publicar`, change:

```python
    publicar_coleta(coleta)
    messages.success(request, f"{coleta} publicada.")
    return redirect("coleta_list")
```

to:

```python
    publicar_coleta(coleta)
    messages.success(request, f"{coleta} publicada.")
    return redirect("inicio")
```

- [ ] **Step 4: Run the full test suite**

Run: `python manage.py test`
Expected: all tests PASS, including every other `PublicarTests` test (none
of them assert on the final redirect target except the one just updated).

- [ ] **Step 5: Commit**

```bash
git add bebedouros/views.py bebedouros/tests/test_publicar.py
git commit -m "feat: publicar uma coleta leva de volta ao Início, não à lista de coletas

DESENHO-PARTE-VISUAL.md secao 8, decisao 12.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Manual check (do this after Task 3, before moving to the next plan)

Run the dev server and look at it as the orientanda would:

```bash
python manage.py runserver
```

1. Log in, go to `/inicio/`. With no coletas yet: all three alert lines
   should read the calm "Nenhum / Todos..." text, and every row in the
   table should show the gray empty gota with "—" for IQA-B and date.
2. Create a coleta, fill in a couple of bebedouros with values that pass
   every limit, publish it. Confirm: you land back on `/inicio/`, the
   published bebedouros now show a colored gota and today's date, and the
   ones left blank still show empty and (if active) show up under
   "Quinzena sem dados".
3. Fill one bebedouro with a value that fails a limit badly enough to drop
   it under 40 (e.g. `pH` outside 6–9 and `E. coli` presente) and confirm
   it appears under "IQA-B baixo" with a warm-colored chip.
4. Mark a filtro as vencido on an otherwise-clean bebedouro and confirm it
   shows up only under "Filtro vencido", not under "IQA-B baixo".
