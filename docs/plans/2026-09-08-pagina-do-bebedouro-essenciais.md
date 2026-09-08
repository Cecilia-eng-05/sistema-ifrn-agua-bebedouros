# Página do Bebedouro — Dados Essenciais Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the página do bebedouro (`DESENHO-PARTE-VISUAL.md` §5) — the
single page, shared by the public site and the internal (logged-in) view,
that shows one bebedouro's current IQA-B, its filtro-vencido warning, the
internal QFQ/QM/CO breakdown, and the last collection's raw parameter
values. This plan covers everything in §5 except the evolution graph
(item 5 of that section), which is its own, more complex follow-up plan.

**Architecture:** One new view, `bebedouro_detalhe`, NOT behind
`@login_required` (it must be reachable by anonymous visitors) — it
decides internally which data to show based on `request.user.is_authenticated`:
anonymous visitors only ever see data from **published** coletas
(`DEFINICAO-DO-PROJETO.md` §7 — "só então aqueles resultados aparecem na
parte pública"); logged-in staff see the latest data regardless of
draft/published status, matching how the tela Início already behaves for
them. A new `situacao_atual_bebedouro(bebedouro, apenas_publicadas=False)`
service function (a single-bebedouro sibling of the existing
`situacao_atual_bebedouros()`) implements this gating, by extending the
existing `_ultimo_resultado_valido()` helper with an `apenas_publicadas`
filter. The template branches on `{% if user.is_authenticated %}` to show
or hide the internal-only QFQ/QM/CO cards — this is a presentation-only
split of data that is already correctly gated at the view/query level, so
there is no risk of leaking draft data through the public branch.

The "gota grande" (big teardrop) reuses the exact same CSS shape already
shipped for the tela Início's small gotas (`.gota`, plus the existing
`.gota-{classificação}`/`.gota-vazia` color classes) — just a bigger size
modifier, `.gota-lg`, plus a number overlaid as a **sibling** element (not
a child) so it isn't affected by the shape's `rotate(-45deg)` transform.
This is a simplification of the original "gota que enche" (progressive
fill) idea from `DESENHO-PARTE-VISUAL.md` §3 — solid color by
classification, matching what already shipped for the small gotas,
deferred pending a look at the real page before investing in a fill
animation that can't be visually verified sight-unseen.

`DESENHO-PARTE-VISUAL.md` §5 lists "o que é monitorado" (item 4) and
"última quinzena em tabela" (item 6) as two separate pieces, but both
show the same seven parameter values from the same collection — this
plan renders them once, as a single two-column table (parâmetro/valor),
to avoid showing the same numbers twice on the page.

Two links mentioned in §5 are intentionally left out of this plan because
their destination pages don't exist yet: the link to the aba Parâmetros
(item 4) and "ver quinzenas anteriores" (item 6). Both are one-line
additions once those pages exist in a later plan — not built here.

**Tech Stack:** Same as the tela Início plan — Django 5.2, server-rendered
HTML, `base.html`'s existing `<style>` block, Django `TestCase` + test
client. No new dependencies. No real bebedouro photos exist yet (pending
material, `DESENHO-PARTE-VISUAL.md` §9) — the header uses a plain neutral
placeholder box instead of an `<img>`; wiring up real photo uploads is
deferred to when photos actually arrive.

**Spec:** `DESENHO-PARTE-VISUAL.md` §5 (page content), §8 decisions 2, 3,
6, 7 (same page for both audiences; gota always visible; internal-only
breakdown; neutral parameter values) and `DEFINICAO-DO-PROJETO.md` §7
(publish gates public visibility). Builds on
`docs/plans/2026-09-08-tela-inicio-interna.md` (already implemented) —
this plan also finishes that plan's deferred "link to the bebedouro page
once it exists" note.

## Global Constraints

(Same as `docs/plans/2026-09-08-tela-inicio-interna.md` — Portuguese UI
text, no external JS/CSS/dependencies, Django `TestCase` + `self.client`
test style, reuse the shared `.gota`/`.gota-*` classes rather than
redefining them.)

- Anonymous visitors must never receive data from an unpublished
  (`Coleta.RASCUNHO`) coleta in the response — this is enforced at the
  query level in `situacao_atual_bebedouro`, not just hidden by CSS/template.
- No parameter value in the public-facing table gets a color or
  right/wrong marking — plain text only (`DESENHO-PARTE-VISUAL.md` §8
  decision 7).
- The "motivo" text on the internal breakdown only ever appears for a
  vencido filtro, never for any other low sub-score (§8 decision 6 /
  the orientanda's explicit instruction in conversation).

---

### Task 1: Data layer — situação de um único bebedouro, com filtro de publicação

**Files:**
- Modify: `bebedouros/services.py`
- Test: `bebedouros/tests/test_services.py`

**Interfaces:**
- Modifies (backward-compatible): `_ultimo_resultado_valido(bebedouro, apenas_publicadas=False)`
  — adds an optional kwarg; default behavior unchanged, so
  `situacao_atual_bebedouros()` (which calls it with no kwarg) and every
  existing test keep passing untouched.
- Produces: `situacao_atual_bebedouro(bebedouro, apenas_publicadas=False) -> dict`
  — same shape as one item of `situacao_atual_bebedouros()`:
  `{"bebedouro": Bebedouro, "resultado": Resultado | None, "data": date | None}`.
  With `apenas_publicadas=True`, only considers `Resultado`s whose
  `coleta.status == Coleta.PUBLICADO`.

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_services.py` (the `RESULTADO_COMPLETO` dict
already added by the tela Início plan is reused here):

```python
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
```

Also add `situacao_atual_bebedouro` to the existing import block at the top
of the file:

```python
from bebedouros.services import (
    alertas_internos,
    linhas_faltantes,
    recalcular_coleta,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'situacao_atual_bebedouro'`.

- [ ] **Step 3: Implement**

In `bebedouros/services.py`, replace the existing `_ultimo_resultado_valido`
function:

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
```

with:

```python
def _ultimo_resultado_valido(bebedouro, apenas_publicadas=False):
    """O Resultado mais recente deste bebedouro que tem algum dado de
    verdade — pula linhas vazias e linhas marcadas 'fora de operação'.
    Com apenas_publicadas=True, considera só coletas já publicadas (usado
    pela página pública do bebedouro — DEFINICAO-DO-PROJETO.md §7)."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    for resultado in resultados:
        if not resultado.fora_de_operacao and not resultado.esta_vazio():
            return resultado
    return None
```

Then add, right after `situacao_atual_bebedouros`:

```python
def situacao_atual_bebedouro(bebedouro, apenas_publicadas=False):
    """Situação mais recente de UM bebedouro — mesmo formato de item de
    situacao_atual_bebedouros(), usado pela página do bebedouro (pública e
    interna). apenas_publicadas=True restringe às coletas já publicadas."""
    resultado = _ultimo_resultado_valido(bebedouro, apenas_publicadas=apenas_publicadas)
    return {
        "bebedouro": bebedouro,
        "resultado": resultado,
        "data": resultado.coleta.data if resultado else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_services -v 2`
Expected: all tests in the file PASS, including every pre-existing test
(`LinhasFaltantesTests`, `SituacaoAtualBebedourosTests`, `AlertasInternosTests`).

- [ ] **Step 5: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: situacao_atual_bebedouro — situação de um bebedouro, com filtro de publicação

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Página do bebedouro — rota, view, template e identidade visual

**Files:**
- Modify: `bebedouros/models.py`
- Modify: `bebedouros/views.py`
- Modify: `bebedouros/urls.py`
- Modify: `bebedouros/templates/bebedouros/base.html`
- Create: `bebedouros/templates/bebedouros/bebedouro_detalhe.html`
- Test: Create `bebedouros/tests/test_bebedouro_detalhe.py`

**Interfaces:**
- Consumes: `situacao_atual_bebedouro(bebedouro, apenas_publicadas)` (Task 1).
- Produces: URL name `bebedouro_detalhe` resolving to `/bebedouros/<pk>/`,
  used by Task 3 to link from the tela Início, and by future plans (mapa
  público, gráfico de evolução) that link into this page.
- Produces: `Resultado.turbidez_texto()` — display-only method, same
  format as the grade's `<0,751` convention.
- Produces CSS: `.gota-lg`, `.gota-grande-wrap`, `.gota-numero-grande`,
  `.cartoes-indice*`, `.cartao-indice*`, `.foto-placeholder`,
  `.cabecalho-bebedouro`, `.cabecalho-info`, `.cabecalho-status`,
  `.parametros` in `base.html`.

- [ ] **Step 1: Write the failing tests**

Create `bebedouros/tests/test_bebedouro_detalhe.py`:

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
        self.assertContains(response, "gota-vazia")

    def test_com_dados_publicados_mostra_gota_colorida(self):
        coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "gota-excelente")
        self.assertContains(response, "Excelente")
        self.assertContains(response, "01/09/2026")

    def test_visitante_nao_ve_rascunho(self):
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "gota-vazia")
        self.assertNotContains(response, "gota-excelente")

    def test_usuario_logado_ve_rascunho(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "gota-excelente")

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
        self.assertNotContains(response, "De onde vem a nota")

    def test_interno_mostra_cartoes_com_pesos_e_notas(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "De onde vem a nota")
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
        self.assertContains(response, "O que é monitorado nesta água")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_bebedouro_detalhe -v 2`
Expected: FAIL — `404` on every `/bebedouros/<pk>/` request (no such URL
yet).

- [ ] **Step 3: Add `Resultado.turbidez_texto()`**

In `bebedouros/models.py`, add this method to `Resultado`, right after
`iqab_faixa_slug`:

```python
    def turbidez_texto(self):
        """Texto de exibição da turbidez — mesmo formato aceito na grade
        ('<0,751' quando abaixo do limite de detecção; vazio sem dado)."""
        if self.turbidez_abaixo_limite and self.turbidez_valor is not None:
            return f"<{number_format(self.turbidez_valor)}"
        if self.turbidez_abaixo_limite:
            return "<"
        if self.turbidez_valor is not None:
            return number_format(self.turbidez_valor)
        return ""
```

(`number_format` is already imported at the top of `bebedouros/models.py`.)

- [ ] **Step 4: Add the URL**

In `bebedouros/urls.py`, add the new path right after `inicio/`:

```python
    path("inicio/", views.inicio, name="inicio"),
    path("bebedouros/<int:pk>/", views.bebedouro_detalhe, name="bebedouro_detalhe"),
    path("", views.coleta_list, name="coleta_list"),
```

- [ ] **Step 5: Add the view**

In `bebedouros/views.py`, add the `iqab` module import (it isn't imported
there yet):

```python
from . import iqab
```

Change the services import to add `situacao_atual_bebedouro`:

```python
from .services import (
    alertas_internos,
    linhas_faltantes,
    publicar_coleta,
    recalcular_coleta,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
)
```

Add the view (note: **no** `@login_required` — this page must be reachable
by anonymous visitors):

```python
def bebedouro_detalhe(request, pk):
    bebedouro = get_object_or_404(Bebedouro, pk=pk)
    apenas_publicadas = not request.user.is_authenticated
    situacao = situacao_atual_bebedouro(bebedouro, apenas_publicadas=apenas_publicadas)
    pesos_iqab = {
        "qfq": int(iqab.PESO_QFQ * 100),
        "qm": int(iqab.PESO_QM * 100),
        "co": int(iqab.PESO_CO * 100),
    }
    return render(
        request,
        "bebedouros/bebedouro_detalhe.html",
        {"bebedouro": bebedouro, "situacao": situacao, "pesos_iqab": pesos_iqab},
    )
```

- [ ] **Step 6: Add the CSS**

In `bebedouros/templates/bebedouros/base.html`, find the end of the gota
CSS block added by the tela Início plan:

```css
    .gota-critica { background: #a32222; }
```

Replace with (keeps that line, adds the new rules after it):

```css
    .gota-critica { background: #a32222; }
    .gota-lg { width: 64px; height: 64px; }
    .gota-grande-wrap {
      position: relative; display: inline-block; width: 64px; height: 64px; flex-shrink: 0;
    }
    .gota-grande-wrap .gota-lg { position: absolute; inset: 0; }
    .gota-numero-grande {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      font-size: 20px; font-weight: 700; color: #fff;
    }

    /* Página do bebedouro */
    .cabecalho-bebedouro {
      display: flex; align-items: center; gap: 18px; flex-wrap: wrap; margin-top: 6px;
    }
    .foto-placeholder {
      width: 96px; height: 96px; border-radius: 12px; flex-shrink: 0;
      background: var(--clara); border: 1px solid var(--borda);
    }
    .cabecalho-info { flex: 1 1 240px; }
    .cabecalho-status { color: var(--tinta-suave); margin: 2px 0 0; }
    .cartoes-indice, .parametros { margin-top: 20px; }
    .cartoes-indice h2, .parametros h2 { font-size: 16px; margin: 0 0 10px; }
    .cartoes-indice-grid { display: flex; flex-wrap: wrap; gap: 12px; }
    .cartao-indice {
      background: var(--superficie); border: 1px solid var(--borda); border-radius: 10px;
      padding: 12px 14px; flex: 1 1 180px; min-width: 180px;
      display: flex; flex-direction: column; gap: 4px;
    }
    .cartao-indice-nome { font-weight: 600; }
    .cartao-indice-peso { font-size: 12px; color: var(--tinta-suave); }
    .cartao-indice-nota { font-size: 22px; font-weight: 700; }
    .cartao-indice-motivo { font-size: 13px; color: #8a5a00; }
```

- [ ] **Step 7: Create the template**

Create `bebedouros/templates/bebedouros/bebedouro_detalhe.html`:

```html
{% extends "bebedouros/base.html" %}
{% block titulo %}{{ bebedouro.codigo }} — Monitoramento da Água — IFRN-CNAT{% endblock %}
{% block conteudo %}
  <div class="cabecalho-bebedouro">
    <div class="foto-placeholder" aria-hidden="true"></div>
    <div class="gota-grande-wrap">
      {% if situacao.resultado.iqab_status == "calculado" %}
        <span class="gota gota-lg gota-{{ situacao.resultado.iqab_faixa_slug }}"></span>
        <span class="gota-numero-grande">{{ situacao.resultado.iqab }}</span>
      {% else %}
        <span class="gota gota-lg gota-vazia"></span>
      {% endif %}
    </div>
    <div class="cabecalho-info">
      <h1>{{ bebedouro.codigo }} — {{ bebedouro.local }}</h1>
      {% if situacao.resultado.iqab_status == "calculado" %}
        <p class="cabecalho-status">{{ situacao.resultado.iqab_classificacao }} · última análise em {{ situacao.data|date:"d/m/Y" }}</p>
      {% else %}
        <p class="cabecalho-status">Ainda não há um IQA-B calculado para este bebedouro.</p>
      {% endif %}
    </div>
  </div>

  {% if situacao.resultado.filtro == "vencido" %}
    <div class="msg warning">Filtro fora da validade na última coleta.</div>
  {% endif %}

  {% if user.is_authenticated %}
    <section class="cartoes-indice">
      <h2>De onde vem a nota</h2>
      <div class="cartoes-indice-grid">
        <div class="cartao-indice">
          <span class="cartao-indice-nome">Físico-química da água</span>
          <span class="cartao-indice-peso">peso {{ pesos_iqab.qfq }}%</span>
          <span class="cartao-indice-nota">{{ situacao.resultado.iqab_qfq|default:"—" }}</span>
        </div>
        <div class="cartao-indice">
          <span class="cartao-indice-nome">Presença de bactérias</span>
          <span class="cartao-indice-peso">peso {{ pesos_iqab.qm }}%</span>
          <span class="cartao-indice-nota">{{ situacao.resultado.iqab_qm|default:"—" }}</span>
        </div>
        <div class="cartao-indice">
          <span class="cartao-indice-nome">Situação do filtro</span>
          <span class="cartao-indice-peso">peso {{ pesos_iqab.co }}%</span>
          <span class="cartao-indice-nota">{{ situacao.resultado.iqab_co|default:"—" }}</span>
          {% if situacao.resultado.filtro == "vencido" %}
            <span class="cartao-indice-motivo">Filtro fora da validade na data da coleta.</span>
          {% endif %}
        </div>
      </div>
    </section>
  {% endif %}

  <section class="parametros">
    <h2>O que é monitorado nesta água</h2>
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

- [ ] **Step 8: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_bebedouro_detalhe -v 2`
Expected: all `BebedouroDetalheTests` PASS.

- [ ] **Step 9: Run the full test suite**

Run: `python manage.py test`
Expected: all tests PASS (confirms the `base.html`, `urls.py` and
`models.py` changes didn't break any existing page).

- [ ] **Step 10: Commit**

```bash
git add bebedouros/models.py bebedouros/views.py bebedouros/urls.py bebedouros/templates/bebedouros/base.html bebedouros/templates/bebedouros/bebedouro_detalhe.html bebedouros/tests/test_bebedouro_detalhe.py
git commit -m "feat: página do bebedouro — gota grande, aviso de filtro, cartões internos e parâmetros

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Ligar a tela Início à página do bebedouro

**Files:**
- Modify: `bebedouros/templates/bebedouros/inicio.html`
- Modify: `bebedouros/templates/bebedouros/base.html`
- Test: Modify `bebedouros/tests/test_inicio.py`

**Interfaces:**
- Consumes: URL name `bebedouro_detalhe` (Task 2).

This finishes the "becomes links once the bebedouro page exists" note
left in `docs/plans/2026-09-08-tela-inicio-interna.md` Task 2. It links
the main table's código (all 15 bebedouros) and the "IQA-B baixo" /
"Filtro vencido" alert chips. The "Quinzena sem dados" chip is left as
plain text — `alertas_internos()` returns that alert as plain código
strings (not bebedouro objects, see `services.py`), and the same
bebedouro is one click away in the table below regardless.

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_inicio.py`:

```python
    def test_tabela_liga_para_pagina_do_bebedouro(self):
        b1 = Bebedouro.objects.create(numero=1)
        response = self.client.get("/inicio/")
        self.assertContains(response, f'href="/bebedouros/{b1.pk}/"')

    def test_chip_de_filtro_vencido_liga_para_pagina_do_bebedouro(self):
        b1 = Bebedouro.objects.create(numero=1)
        coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        dados = {**RESULTADO_COMPLETO, "filtro": Resultado.FILTRO_VENCIDO}
        Resultado.objects.create(coleta=coleta, bebedouro=b1, **dados)
        recalcular_coleta(coleta)
        response = self.client.get("/inicio/")
        # Uma vez na linha da tabela, outra vez no chip do alerta.
        self.assertContains(response, f'href="/bebedouros/{b1.pk}/"', count=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_inicio -v 2`
Expected: FAIL — neither test finds the `href="/bebedouros/..."` string
(the código is still plain text, not a link).

- [ ] **Step 3: Link the table's código**

In `bebedouros/templates/bebedouros/inicio.html`, find:

```html
          <td class="cod">{{ s.bebedouro.codigo }}</td>
```

Replace with:

```html
          <td class="cod"><a href="{% url 'bebedouro_detalhe' s.bebedouro.pk %}">{{ s.bebedouro.codigo }}</a></td>
```

- [ ] **Step 4: Link the "IQA-B baixo" chip**

In the same file, find:

```html
            <span class="chip chip-{{ s.resultado.iqab_faixa_slug }}">{{ s.bebedouro.codigo }}</span>
```

Replace with:

```html
            <a class="chip chip-{{ s.resultado.iqab_faixa_slug }}" href="{% url 'bebedouro_detalhe' s.bebedouro.pk %}">{{ s.bebedouro.codigo }}</a>
```

- [ ] **Step 5: Link the "Filtro vencido" chip**

Find (note: this is the chip using `s.bebedouro.codigo` — the "Quinzena
sem dados" block below it uses bare `codigo` and must NOT be touched):

```html
            <span class="chip chip-vencido">{{ s.bebedouro.codigo }}</span>
```

Replace with:

```html
            <a class="chip chip-vencido" href="{% url 'bebedouro_detalhe' s.bebedouro.pk %}">{{ s.bebedouro.codigo }}</a>
```

- [ ] **Step 6: Style the new links to match the existing look**

In `bebedouros/templates/bebedouros/base.html`, find:

```css
    .chip-vencido { background: var(--aviso-bg); color: #8a5a00; border-color: var(--aviso-bd); }
```

Replace with (adds link-reset rules right after):

```css
    .chip-vencido { background: var(--aviso-bg); color: #8a5a00; border-color: var(--aviso-bd); }
    .chip { text-decoration: none; }
    td.cod a { color: inherit; text-decoration: none; }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_inicio -v 2`
Expected: all `InicioTests` PASS, including the 2 new ones.

- [ ] **Step 8: Run the full test suite**

Run: `python manage.py test`
Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add bebedouros/templates/bebedouros/inicio.html bebedouros/templates/bebedouros/base.html bebedouros/tests/test_inicio.py
git commit -m "feat: ligar a tela Início à página do bebedouro

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Manual check (do this after Task 3, before moving to the next plan)

```bash
python manage.py runserver
```

1. From `/inicio/`, click a bebedouro's código. Confirm you land on its
   page, with the big gota, its classification and date, and the table
   of last-collection values underneath.
2. While logged in, confirm the "De onde vem a nota" cards show under the
   parameter table, with the three weights (30%/50%/20%) and scores.
3. Log out (`/sair/`) and revisit the same bebedouro's URL directly.
   Confirm the "De onde vem a nota" cards are gone, and — if that
   bebedouro's latest coleta was never published — confirm the gota shows
   empty/gray rather than the logged-in numbers.
4. Publish a coleta with that bebedouro filled in, then revisit while
   logged out: confirm the gota now shows the published number.
5. Mark a filtro as vencido and confirm the banner appears on the page
   AND (while logged in) the "motivo" line appears only on the "Situação
   do filtro" card, not on the other two.
