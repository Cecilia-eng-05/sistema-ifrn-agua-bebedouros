# Ajustes na Página do Bebedouro (pedidos da orientadora) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `DESENHO-PAGINA-DO-BEBEDOURO.md` — reorganize the
bebedouro detail page around a fixed list of the 5 most recent coletas
plus their average, add filtro-troca (filter replacement) tracking with
a public ok/vencido indicator, and fix the "Composição da nota" cards so
they're visible to anonymous visitors like the rest of the public page.

**Architecture:** One new model, `TrocaFiltro` (bebedouro + coleta +
data_troca), populated from a new optional column on the existing
lançamento grid — same pattern the grid already uses for `Resultado`
rows (`update_or_create` keyed by coleta+bebedouro, via the existing
`ResultadoRowForm`/`_salvar_grade` machinery). Two existing service
functions (`historico_bebedouro`, and the standalone "O que é
monitorado" table) are retired and replaced by one function,
`coletas_recentes()`, that returns the 5 most recent `Resultado` rows
(current one included) — the template renders all 5 as
`<details>`, the first one `open`. A new `media_coletas()` service
function reduces that same list to one dict of ready-to-display
strings (so the template has no averaging logic in it). Filtro
validity (`situacao_filtro()`) is computed from the most recent
`TrocaFiltro` row plus a fixed 182-day (~6 month) window — the same
approximation the codebase already uses for `JANELA_DIAS["6m"]`. None
of this touches `iqab.py`'s formula inputs: the manually-entered
`Resultado.filtro` (dentro/vencido) field keeps feeding the CO score
exactly as today.

**Tech Stack:** Django 5.2, sqlite (dev), no new dependencies.

**Spec:** `DESENHO-PAGINA-DO-BEBEDOURO.md` (also depends on
`DEFINICAO-DO-PROJETO.md` and `DESENHO-PARTE-VISUAL.md`, unchanged by
this plan except where DESENHO-PAGINA-DO-BEBEDOURO.md §1 explicitly
overrides the page's block order).

## Global Constraints

- Filtro validity window: **182 days** (≈ 6 months — same approximation
  as `services.JANELA_DIAS["6m"]`), same for all 15 bebedouros.
- The `Resultado.filtro` field (dentro/vencido, manually entered) keeps
  feeding the IQA-B's CO score exactly as today — `iqab.py` is not
  modified in this plan except to add one new public helper,
  `media()`, used only for display.
- Every new/changed piece of the public bebedouro page must respect the
  existing publish gate: anonymous visitors only ever see data coming
  from `Coleta.status == PUBLICADO` (`apenas_publicadas=True` threaded
  through, exactly like every existing service function already does).
- Run the full suite after every task: `./.venv/Scripts/python.exe manage.py test bebedouros`.
- Portuguese docstrings/comments, matching the rest of the codebase.

---

## Task 1: `TrocaFiltro` model + migration

**Files:**
- Modify: `bebedouros/models.py`
- Create: `bebedouros/migrations/0008_trocafiltro.py` (via `makemigrations`)
- Test: `bebedouros/tests/test_troca_filtro_model.py`

**Interfaces:**
- Produces: `TrocaFiltro` model with fields `bebedouro` (FK → Bebedouro,
  `related_name="trocas_filtro"`), `coleta` (FK → Coleta,
  `related_name="trocas_filtro"`), `data_troca` (DateField). Unique
  constraint on `(coleta, bebedouro)` named
  `uniq_troca_filtro_por_bebedouro_na_coleta`.

- [ ] **Step 1: Write the failing test**

```python
# bebedouros/tests/test_troca_filtro_model.py
import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, TrocaFiltro


class TrocaFiltroModelTests(TestCase):
    def setUp(self):
        self.b1 = Bebedouro.objects.create(numero=1)
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))

    def test_cria_troca_filtro(self):
        troca = TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        self.assertEqual(troca.bebedouro, self.b1)
        self.assertEqual(str(troca), "B1 — troca em 01/09/2026")

    def test_uma_troca_por_bebedouro_por_coleta(self):
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrocaFiltro.objects.create(
                bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 2)
            )

    def test_apagar_coleta_apaga_trocas(self):
        TrocaFiltro.objects.create(
            bebedouro=self.b1, coleta=self.coleta, data_troca=datetime.date(2026, 9, 1)
        )
        self.coleta.delete()
        self.assertEqual(TrocaFiltro.objects.count(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_troca_filtro_model -v 2`
Expected: FAIL — `ImportError: cannot import name 'TrocaFiltro'`

- [ ] **Step 3: Add the model**

Append to `bebedouros/models.py` (after the `Resultado` class):

```python
class TrocaFiltro(models.Model):
    """Uma troca de filtro registrada para um bebedouro. Lançada junto
    com uma coleta (mesma grade), mas independente do valor Resultado.filtro
    daquela coleta — ver DESENHO-PAGINA-DO-BEBEDOURO.md §7."""

    bebedouro = models.ForeignKey(
        Bebedouro, on_delete=models.CASCADE, related_name="trocas_filtro"
    )
    coleta = models.ForeignKey(
        Coleta, on_delete=models.CASCADE, related_name="trocas_filtro"
    )
    data_troca = models.DateField("Troca realizada em")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["coleta", "bebedouro"],
                name="uniq_troca_filtro_por_bebedouro_na_coleta",
            )
        ]
        ordering = ["-data_troca"]

    def __str__(self):
        return f"{self.bebedouro.codigo} — troca em {self.data_troca:%d/%m/%Y}"
```

- [ ] **Step 4: Generate and inspect the migration**

Run: `./.venv/Scripts/python.exe manage.py makemigrations bebedouros`
Expected: creates `bebedouros/migrations/0008_trocafiltro.py` declaring
the `TrocaFiltro` model with the two FKs and the unique constraint above.
Open the generated file and confirm it matches — fix the migration by
hand only if `makemigrations` produced something different (e.g. field
order) that doesn't match the model.

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_troca_filtro_model -v 2`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add bebedouros/models.py bebedouros/migrations/0008_trocafiltro.py bebedouros/tests/test_troca_filtro_model.py
git commit -m "feat: modelo TrocaFiltro para registrar troca de filtro por coleta"
```

---

## Task 2: Extract `formatar_turbidez()` in `models.py`

Pure refactor — no behavior change — so `media_coletas()` (Task 4) can
reuse the exact same turbidez display rule the single-coleta table
already uses, instead of duplicating it.

**Files:**
- Modify: `bebedouros/models.py`
- Test: `bebedouros/tests/test_resultado_model.py`

**Interfaces:**
- Produces: `formatar_turbidez(valor, abaixo_limite)` — module-level
  function in `bebedouros/models.py`. Returns `""` when `valor is None`
  and `abaixo_limite` is `False`; `f"<{number_format(valor)}"` when both
  are set; `"<"` when `abaixo_limite` is `True` and `valor is None`;
  `number_format(valor)` when only `valor` is set.

- [ ] **Step 1: Write the failing test**

Add to `bebedouros/tests/test_resultado_model.py`:

```python
from bebedouros.models import formatar_turbidez


class FormatarTurbidezTests(TestCase):
    def test_sem_valor_e_sem_marcador(self):
        self.assertEqual(formatar_turbidez(None, False), "")

    def test_valor_normal(self):
        self.assertEqual(formatar_turbidez(Decimal("0.751"), False), "0,751")

    def test_abaixo_do_limite_com_valor(self):
        self.assertEqual(formatar_turbidez(Decimal("0.751"), True), "<0,751")

    def test_abaixo_do_limite_sem_valor(self):
        self.assertEqual(formatar_turbidez(None, True), "<")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_resultado_model -v 2`
Expected: FAIL — `ImportError: cannot import name 'formatar_turbidez'`

- [ ] **Step 3: Extract the function**

In `bebedouros/models.py`, add the module-level function (near the top,
after the imports) and rewrite `Resultado.turbidez_texto` to call it:

```python
def formatar_turbidez(valor, abaixo_limite):
    """Texto de exibição da turbidez ('<0,751' quando abaixo do limite de
    detecção; vazio sem dado nenhum). Compartilhado entre a tabela de uma
    única coleta (Resultado.turbidez_texto) e a média de várias coletas
    (services.media_coletas)."""
    if abaixo_limite and valor is not None:
        return f"<{number_format(valor)}"
    if abaixo_limite:
        return "<"
    if valor is not None:
        return number_format(valor)
    return ""
```

Replace the body of `Resultado.turbidez_texto`:

```python
    def turbidez_texto(self):
        """Texto de exibição da turbidez — mesmo formato aceito na grade
        ('<0,751' quando abaixo do limite de detecção; vazio sem dado)."""
        return formatar_turbidez(self.turbidez_valor, self.turbidez_abaixo_limite)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_resultado_model bebedouros.tests.test_bebedouro_detalhe -v 2`
Expected: PASS — including the pre-existing
`test_turbidez_abaixo_do_limite_mostra_menor_que` in
`test_bebedouro_detalhe.py`, unaffected by the refactor.

- [ ] **Step 5: Commit**

```bash
git add bebedouros/models.py bebedouros/tests/test_resultado_model.py
git commit -m "refactor: extrai formatar_turbidez para reuso na média de coletas"
```

---

## Task 3: `iqab.media()`

**Files:**
- Modify: `bebedouros/iqab.py`
- Test: `bebedouros/tests/test_iqab.py`

**Interfaces:**
- Consumes: `iqab._arredondar` (existing, private, same module).
- Produces: `iqab.media(notas)` — `notas` a list of already-calculated
  `Decimal` IQA-B scores. Returns `None` for an empty list, otherwise
  the floor-rounded average (`Decimal`, same rounding rule as a single
  score).

- [ ] **Step 1: Write the failing test**

Add to `bebedouros/tests/test_iqab.py` (check the file's existing import
style first — `from decimal import Decimal` and `from bebedouros import
iqab` are already used there):

```python
class MediaTests(TestCase):
    def test_lista_vazia_retorna_none(self):
        self.assertIsNone(iqab.media([]))

    def test_media_simples(self):
        self.assertEqual(iqab.media([Decimal("80"), Decimal("60")]), Decimal("70"))

    def test_corta_pra_baixo_como_uma_nota_unica(self):
        # (79 + 80) / 2 = 79.5 -> corta pra 79, não arredonda pra 80.
        self.assertEqual(iqab.media([Decimal("79"), Decimal("80")]), Decimal("79"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_iqab -v 2`
Expected: FAIL — `AttributeError: module 'bebedouros.iqab' has no attribute 'media'`

- [ ] **Step 3: Implement**

Add to `bebedouros/iqab.py`, after `calcular()`:

```python
def media(notas):
    """Média de uma lista de notas de IQA-B já calculadas (Decimal), para
    o bloco 'Média das coletas recentes' da página do bebedouro. Arredonda
    do mesmo jeito que uma nota individual (corta pra baixo). None se a
    lista estiver vazia."""
    if not notas:
        return None
    return _arredondar(sum(notas) / len(notas))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_iqab -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bebedouros/iqab.py bebedouros/tests/test_iqab.py
git commit -m "feat: iqab.media() para a média das notas na página do bebedouro"
```

---

## Task 4: `services.coletas_recentes()` replaces `historico_bebedouro()`

**Files:**
- Modify: `bebedouros/services.py`
- Modify: `bebedouros/tests/test_services.py` (remove the
  `historico_bebedouro` tests, add `coletas_recentes` tests)

**Interfaces:**
- Produces: `coletas_recentes(bebedouro, apenas_publicadas=False,
  quantidade=5)` — list of `Resultado`, most recent first, length ≤
  `quantidade`. Includes the current/most-recent result (unlike the old
  `historico_bebedouro`, which excluded it). Skips rows where
  `esta_vazio()` is true and `fora_de_operacao` is false (same skip rule
  `historico_bebedouro` already used). No 12-month window — this
  function looks back as far as needed to fill `quantidade`.

- [ ] **Step 1: Look at the tests being replaced**

Open `bebedouros/tests/test_services.py` and find the block of tests
that import and call `historico_bebedouro` (currently the last ~7 tests
in the file, lines ~290-360 per the current layout — confirm by
searching for `historico_bebedouro` in that file). Delete that whole
block of test methods and remove `historico_bebedouro` from the
`from bebedouros.services import (...)` import at the top of the file.

- [ ] **Step 2: Write the failing tests**

Add to `bebedouros/tests/test_services.py` (add `coletas_recentes` to
the existing import line):

```python
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

    def test_fora_de_operacao_entra_na_lista(self):
        self._coleta_com_resultado(0, fora_de_operacao=True)
        recentes = coletas_recentes(self.b1)
        self.assertEqual(len(recentes), 1)
        self.assertTrue(recentes[0].fora_de_operacao)

    def test_apenas_publicadas_ignora_rascunho(self):
        coleta = Coleta.objects.create(data=datetime.date.today())  # rascunho
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, ph=Decimal("7.0"))
        self.assertEqual(coletas_recentes(self.b1, apenas_publicadas=True), [])
        self.assertEqual(len(coletas_recentes(self.b1, apenas_publicadas=False)), 1)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'coletas_recentes'`

- [ ] **Step 4: Implement, replacing `historico_bebedouro`**

In `bebedouros/services.py`, delete the whole `historico_bebedouro`
function and replace it with:

```python
def coletas_recentes(bebedouro, apenas_publicadas=False, quantidade=5):
    """As `quantidade` coletas mais recentes deste bebedouro — a atual
    incluída — para o bloco 'Coletas recentes' da página do bebedouro.
    Mais recente primeiro. Pula linhas totalmente vazias (sem nenhum
    lançamento), mas mantém as marcadas 'fora de operação'.
    apenas_publicadas=True restringe às coletas já publicadas."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)

    recentes = []
    for resultado in resultados:
        if resultado.esta_vazio() and not resultado.fora_de_operacao:
            continue
        recentes.append(resultado)
        if len(recentes) == quantidade:
            break
    return recentes
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: PASS (note: `test_bebedouro_detalhe.py` and `views.py` still
reference `historico_bebedouro` at this point in the plan and will fail
— that's expected until Task 9/12; run only `test_services` here.)

- [ ] **Step 6: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: coletas_recentes() substitui historico_bebedouro()"
```

---

## Task 5: `services.media_coletas()`

**Files:**
- Modify: `bebedouros/services.py`
- Modify: `bebedouros/tests/test_services.py`

**Interfaces:**
- Consumes: `formatar_turbidez` (Task 2, from `.models`), `iqab.media`
  (Task 3), `iqab.classificar` (existing), `Resultado.AUSENTE` /
  `Resultado.PRESENTE` (existing).
- Produces: `media_coletas(resultados)` — takes a list of `Resultado`
  (e.g. the output of `coletas_recentes()`) and returns a dict:
  `{"quantidade": int, "cloro": str, "condutividade": str, "nitrato":
  str, "ph": str, "turbidez": str, "coliformes_totais": str,
  "coliformes_totais_alerta": bool, "ecoli": str, "ecoli_alerta": bool,
  "iqab_texto": str}`. Every string value is ready to display as-is
  (already `"—"` when there's no data). `quantidade` counts only the
  rows that aren't `fora_de_operacao` (those are excluded from every
  average).

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_services.py` (add `media_coletas` to the
import line):

```python
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
        self.assertEqual(media["cloro"], "1,5")
        self.assertEqual(media["quantidade"], 2)

    def test_valor_em_branco_fica_de_fora_da_media(self):
        r1 = self._resultado(1, cloro=Decimal("2.0"))
        r2 = self._resultado(2)  # cloro em branco
        media = media_coletas([r1, r2])
        self.assertEqual(media["cloro"], "2")

    def test_fora_de_operacao_fica_de_fora_da_media(self):
        r1 = self._resultado(1, cloro=Decimal("2.0"))
        r2 = self._resultado(2, fora_de_operacao=True)
        media = media_coletas([r1, r2])
        self.assertEqual(media["cloro"], "2")
        self.assertEqual(media["quantidade"], 1)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'media_coletas'`

- [ ] **Step 3: Implement**

Add near the top of `bebedouros/services.py`:

```python
from django.utils.formats import number_format

from . import iqab
from .models import Bebedouro, Coleta, Resultado, formatar_turbidez
```

(replacing the existing `from . import iqab` / `from .models import
Bebedouro, Coleta, Resultado` lines with these two).

Then add, after `coletas_recentes()`:

```python
def media_coletas(resultados):
    """Média dos parâmetros de uma lista de Resultado (normalmente a
    saída de coletas_recentes()), para o bloco 'Média das coletas
    recentes' da página do bebedouro. Coletas marcadas fora de operação
    ficam de fora de toda a conta. Retorna um dict já pronto para
    exibir — cada valor é uma string ('—' quando não há dado nenhum)."""
    validos = [r for r in resultados if not r.fora_de_operacao]

    def texto_decimal(campo):
        valores = [getattr(r, campo) for r in validos if getattr(r, campo) is not None]
        if not valores:
            return "—"
        return number_format(sum(valores) / len(valores))

    turbidez_valores = []
    turbidez_abaixo = False
    for r in validos:
        if r.turbidez_valor is None:
            continue
        turbidez_valores.append(r.turbidez_valor)
        if r.turbidez_abaixo_limite:
            turbidez_abaixo = True
    turbidez_media = (
        sum(turbidez_valores) / len(turbidez_valores) if turbidez_valores else None
    )
    turbidez_texto = formatar_turbidez(turbidez_media, turbidez_abaixo) or "—"

    def texto_micro(campo):
        respondidos = [
            getattr(r, campo)
            for r in validos
            if getattr(r, campo) in (Resultado.AUSENTE, Resultado.PRESENTE)
        ]
        total = len(respondidos)
        if total == 0:
            return "—", False
        presentes = sum(1 for v in respondidos if v == Resultado.PRESENTE)
        if presentes > 0:
            return f"Presente em {presentes} de {total} coletas", True
        return f"Ausente em {total} de {total} coletas", False

    coliformes_texto, coliformes_alerta = texto_micro("coliformes_totais")
    ecoli_texto, ecoli_alerta = texto_micro("ecoli")

    notas = [
        r.iqab for r in validos if r.iqab_status == iqab.CALCULADO and r.iqab is not None
    ]
    media_iqab = iqab.media(notas)
    iqab_texto = (
        f"{number_format(media_iqab)} · {iqab.classificar(media_iqab)}"
        if media_iqab is not None
        else "—"
    )

    return {
        "quantidade": len(validos),
        "cloro": texto_decimal("cloro"),
        "condutividade": texto_decimal("condutividade"),
        "nitrato": texto_decimal("nitrato"),
        "ph": texto_decimal("ph"),
        "turbidez": turbidez_texto,
        "coliformes_totais": coliformes_texto,
        "coliformes_totais_alerta": coliformes_alerta,
        "ecoli": ecoli_texto,
        "ecoli_alerta": ecoli_alerta,
        "iqab_texto": iqab_texto,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: media_coletas() para o bloco de média da página do bebedouro"
```

---

## Task 6: Filtro-troca services (`ultima_troca_filtro`, `situacao_filtro`, `salvar_troca_filtro`)

**Files:**
- Modify: `bebedouros/services.py`
- Modify: `bebedouros/tests/test_services.py`

**Interfaces:**
- Consumes: `TrocaFiltro` (Task 1, from `.models`).
- Produces:
  - `VALIDADE_FILTRO_DIAS = 182` (module constant).
  - `ultima_troca_filtro(bebedouro, apenas_publicadas=False)` → the most
    recent `TrocaFiltro` for that bebedouro, or `None`.
  - `situacao_filtro(bebedouro, apenas_publicadas=False)` → dict
    `{"status": "sem_registro"|"ok"|"vencido", "data_troca": date|None,
    "data_vencimento": date|None}`.
  - `salvar_troca_filtro(coleta, bebedouro, data_troca)` → creates,
    updates, or (if `data_troca is None`) deletes the `TrocaFiltro` row
    for that `(coleta, bebedouro)` pair.

- [ ] **Step 1: Write the failing tests**

Add to `bebedouros/tests/test_services.py` (add `TrocaFiltro` to the
`from bebedouros.models import (...)` line, and `situacao_filtro`,
`ultima_troca_filtro`, `salvar_troca_filtro` to the services import):

```python
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
        rascunho = Coleta.objects.create(data=datetime.date.today())  # rascunho
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: FAIL — `ImportError: cannot import name 'situacao_filtro'`

- [ ] **Step 3: Implement**

Add `TrocaFiltro` to the `.models` import line in `bebedouros/services.py`
and add, at the end of the file:

```python
VALIDADE_FILTRO_DIAS = 182  # ~6 meses — mesma aproximação de JANELA_DIAS["6m"]


def ultima_troca_filtro(bebedouro, apenas_publicadas=False):
    """A troca de filtro mais recente registrada para este bebedouro, ou
    None se nunca houve uma (ou nenhuma visível). apenas_publicadas=True
    restringe às trocas lançadas em coletas já publicadas."""
    trocas = TrocaFiltro.objects.filter(bebedouro=bebedouro).select_related("coleta")
    if apenas_publicadas:
        trocas = trocas.filter(coleta__status=Coleta.PUBLICADO)
    return trocas.order_by("-data_troca").first()


def situacao_filtro(bebedouro, apenas_publicadas=False):
    """Situação da manutenção do filtro deste bebedouro, para o bloco
    'Manutenção do filtro' da página do bebedouro. Retorna
    {"status": "sem_registro"|"ok"|"vencido", "data_troca": date|None,
    "data_vencimento": date|None}."""
    troca = ultima_troca_filtro(bebedouro, apenas_publicadas=apenas_publicadas)
    if troca is None:
        return {"status": "sem_registro", "data_troca": None, "data_vencimento": None}
    vencimento = troca.data_troca + datetime.timedelta(days=VALIDADE_FILTRO_DIAS)
    status = "ok" if datetime.date.today() <= vencimento else "vencido"
    return {"status": status, "data_troca": troca.data_troca, "data_vencimento": vencimento}


def salvar_troca_filtro(coleta, bebedouro, data_troca):
    """Cria, atualiza ou remove o registro de troca de filtro lançado
    nesta coleta para este bebedouro. data_troca=None remove o registro,
    se houver — é o que a grade envia quando o bolsista apaga a data."""
    if data_troca is None:
        TrocaFiltro.objects.filter(coleta=coleta, bebedouro=bebedouro).delete()
        return
    TrocaFiltro.objects.update_or_create(
        coleta=coleta, bebedouro=bebedouro, defaults={"data_troca": data_troca}
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_services -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bebedouros/services.py bebedouros/tests/test_services.py
git commit -m "feat: services de situação e gravação da troca de filtro"
```

---

## Task 7: `troca_filtro` field on `ResultadoRowForm`

**Files:**
- Modify: `bebedouros/forms.py`
- Test: `bebedouros/tests/test_forms.py` (create — no such file exists
  yet; check first with `ls bebedouros/tests/test_*form*` in case one
  was added since this plan was written)

**Interfaces:**
- Produces: `ResultadoRowForm.troca_filtro` — optional `DateField` with
  an `<input type="date">` widget **forced to ISO format**
  (`format="%Y-%m-%d"`). This is NOT quite the same as `ColetaForm.data`:
  that field never renders a pre-filled value today, so it never hit
  this — but `troca_filtro` does (Task 8 pre-fills it from an existing
  `TrocaFiltro`), and Django's default `DateInput` renders initial
  values in the `pt-br` locale format (`01/09/2026`), which an
  `<input type="date">` silently ignores (it requires ISO
  `yyyy-mm-dd`) — the field would just look blank even with data behind
  it. Confirmed with a throwaway shell check during planning: the
  default widget renders `value="01/09/2026"`; adding
  `format="%Y-%m-%d"` renders `value="2026-09-01"` and still parses an
  ISO-format POST body correctly.

- [ ] **Step 1: Write the failing test**

Create `bebedouros/tests/test_forms.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_forms -v 2`
Expected: FAIL — `KeyError: 'troca_filtro'`

- [ ] **Step 3: Implement**

In `bebedouros/forms.py`, add to `ResultadoRowForm` (after `filtro`):

```python
    troca_filtro = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
```

The explicit `format="%Y-%m-%d"` is required — without it, Django
renders a pre-filled value in the `pt-br` locale format
(`01/09/2026`), which an `<input type="date">` silently fails to
display (see Step 1's trap test).

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_forms -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bebedouros/forms.py bebedouros/tests/test_forms.py
git commit -m "feat: campo troca_filtro na grade de lançamento"
```

---

## Task 8: Wire `troca_filtro` into the lançamento view + grid template

**Files:**
- Modify: `bebedouros/views.py`
- Modify: `bebedouros/templates/bebedouros/lancamento.html`
- Modify: `bebedouros/templates/bebedouros/base.html` (grade `nth-child` CSS only)
- Modify: `bebedouros/tests/test_lancamento_get.py`
- Create: `bebedouros/tests/test_lancamento_troca_filtro.py`

**Interfaces:**
- Consumes: `TrocaFiltro` (Task 1), `salvar_troca_filtro` (Task 6).
- Produces: `_initial_de()` now includes `"troca_filtro"` in its
  returned dict; `_salvar_grade()` now also calls `salvar_troca_filtro`
  per row.

- [ ] **Step 1: Write the failing tests**

Create `bebedouros/tests/test_lancamento_troca_filtro.py`:

```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, TrocaFiltro


class LancamentoTrocaFiltroTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def _post(self, **campos):
        dados = {f"b{self.b1.id}-{k}": v for k, v in campos.items()}
        return self.client.post(f"/coletas/{self.coleta.pk}/lancamento/", dados, follow=True)

    def test_preencher_data_cria_troca(self):
        self._post(troca_filtro="2026-09-01")
        troca = TrocaFiltro.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(troca.data_troca, datetime.date(2026, 9, 1))

    def test_deixar_em_branco_nao_cria_troca(self):
        self._post(ph="7,20")
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_apagar_data_remove_troca(self):
        self._post(troca_filtro="2026-09-01")
        self._post(troca_filtro="")
        self.assertEqual(TrocaFiltro.objects.count(), 0)

    def test_relancar_a_grade_sem_mudar_nao_duplica(self):
        self._post(troca_filtro="2026-09-01")
        self._post(troca_filtro="2026-09-01")
        self.assertEqual(TrocaFiltro.objects.count(), 1)

    def test_grade_mostra_troca_ja_lancada(self):
        self._post(troca_filtro="2026-09-01")
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertContains(response, "2026-09-01")
```

Add to `bebedouros/tests/test_lancamento_get.py`
(`LancamentoGetTests.test_grid_shows_editable_row_for_active_and_locked_for_inactive`
stays as-is; add a new test method to the same class):

```python
    def test_grid_has_troca_filtro_column(self):
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertContains(response, "Troca de filtro realizada em")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_lancamento_troca_filtro bebedouros.tests.test_lancamento_get -v 2`
Expected: FAIL — `troca_filtro` not saved anywhere yet, and the column
header text isn't in the template yet.

- [ ] **Step 3: Implement in `views.py`**

Add `TrocaFiltro` to the `from .models import Bebedouro, Coleta,
Resultado` line, and `salvar_troca_filtro` to the `from .services
import (...)` line. Then update `_initial_de`:

```python
def _initial_de(resultado):
    if resultado is None:
        return {}
    if resultado.turbidez_abaixo_limite and resultado.turbidez_valor is not None:
        turbidez = f"<{number_format(resultado.turbidez_valor)}"
    elif resultado.turbidez_abaixo_limite:
        turbidez = "<"
    elif resultado.turbidez_valor is not None:
        turbidez = number_format(resultado.turbidez_valor)
    else:
        turbidez = None
    troca = TrocaFiltro.objects.filter(
        coleta_id=resultado.coleta_id, bebedouro_id=resultado.bebedouro_id
    ).first()
    return {
        "cloro": resultado.cloro,
        "condutividade": resultado.condutividade,
        "nitrato": resultado.nitrato,
        "turbidez": turbidez,
        "ph": resultado.ph,
        "coliformes_totais": resultado.coliformes_totais,
        "ecoli": resultado.ecoli,
        "filtro": resultado.filtro,
        "troca_filtro": troca.data_troca if troca else None,
        "fora_de_operacao": resultado.fora_de_operacao,
        "observacao": resultado.observacao,
    }
```

And in `_salvar_grade`, right after the `Resultado.objects.update_or_create(...)`
call (still inside the `for linha in linhas:` loop):

```python
        Resultado.objects.update_or_create(
            coleta=coleta,
            bebedouro=bebedouro,
            defaults={
                **numericos,
                "turbidez_abaixo_limite": turbidez_abaixo,
                "coliformes_totais": cd.get("coliformes_totais") or "",
                "ecoli": cd.get("ecoli") or "",
                "filtro": cd.get("filtro") or "",
                "fora_de_operacao": cd.get("fora_de_operacao") or False,
                "observacao": cd.get("observacao") or "",
            },
        )
        salvar_troca_filtro(coleta, bebedouro, cd.get("troca_filtro"))
```

- [ ] **Step 4: Implement in `lancamento.html`**

In the `<thead>`, add a new column header right after `<th>Filtro</th>`:

```html
          <th>Filtro</th>
          <th>Troca de filtro realizada em</th>
```

In the row loop, add a new `<td>` right after the filtro `<td>`:

```html
            <td>{{ linha.form.filtro }}</td>
            <td>{{ linha.form.troca_filtro }}</td>
```

And bump the locked-row `colspan` from `11` to `12` (one more column now):

```html
            <td colspan="12">Fora de operação (bebedouro desativado)</td>
```

- [ ] **Step 5: Fix the grade's `nth-child` CSS — the new column shifts every column after it**

The new "Troca de filtro" column lands right after "Filtro" (10th),
pushing "Fora de operação" from 11th to 12th and "Observação" from
12th to 13th. `base.html`'s grid styling targets those columns by
position, so it now points at the wrong ones. In
`bebedouros/templates/bebedouros/base.html`, find these two lines:

```css
    .grade td:nth-child(11) { text-align: center; white-space: nowrap; }
    .grade td:nth-child(12) input { min-width: 110px; }
```

Replace them with (bumped by one, plus a width for the new date input,
matching the pattern the Condutividade column already uses):

```css
    .grade td:nth-child(11) input { min-width: 130px; }
    .grade td:nth-child(12) { text-align: center; white-space: nowrap; }
    .grade td:nth-child(13) input { min-width: 110px; }
```

- [ ] **Step 6: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_lancamento_troca_filtro bebedouros.tests.test_lancamento_get bebedouros.tests.test_lancamento_post bebedouros.tests.test_editar_publicada -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add bebedouros/views.py bebedouros/templates/bebedouros/lancamento.html bebedouros/templates/bebedouros/base.html bebedouros/tests/test_lancamento_get.py bebedouros/tests/test_lancamento_troca_filtro.py
git commit -m "feat: grade de lançamento grava e mostra a troca de filtro"
```

---

## Task 9: Rewire `bebedouro_detalhe` view

**Files:**
- Modify: `bebedouros/views.py`

**Interfaces:**
- Consumes: `coletas_recentes`, `media_coletas`, `situacao_filtro`
  (Tasks 4-6).
- Produces: template context keys `recentes`, `media`, `filtro`
  (replacing `historico`); `situacao`, `pesos_iqab`, `grafico`,
  `janela`, `janelas_labels`, `ultimo` stay unchanged.

No new tests in this task — Task 10 rewrites the template and Task 11
rewrites `test_bebedouro_detalhe.py` end-to-end against the new
context+template together. Doing the view alone first keeps each commit
buildable without a broken import.

- [ ] **Step 1: Update the imports and the view**

In `bebedouros/views.py`, change the `.services` import: remove
`historico_bebedouro`, add `coletas_recentes`, `media_coletas`,
`situacao_filtro`:

```python
from .services import (
    JANELAS_LABELS,
    alertas_internos,
    coletas_recentes,
    linhas_faltantes,
    media_coletas,
    publicar_coleta,
    recalcular_coleta,
    salvar_troca_filtro,
    serie_historica,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
    situacao_filtro,
    ultimo_resultado,
)
```

Rewrite `bebedouro_detalhe`:

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
    janela = request.GET.get("janela", "12m")
    if janela not in ("6m", "12m", "tudo"):
        janela = "12m"

    pontos = serie_historica(bebedouro, janela, apenas_publicadas=apenas_publicadas)
    grafico_dados = grafico.montar_grafico(pontos, dominio_y=(0, 100))
    recentes = coletas_recentes(bebedouro, apenas_publicadas=apenas_publicadas)
    media = media_coletas(recentes)
    filtro = situacao_filtro(bebedouro, apenas_publicadas=apenas_publicadas)
    ultimo = ultimo_resultado(bebedouro, apenas_publicadas=apenas_publicadas)

    return render(
        request,
        "bebedouros/bebedouro_detalhe.html",
        {
            "bebedouro": bebedouro,
            "situacao": situacao,
            "pesos_iqab": pesos_iqab,
            "grafico": grafico_dados,
            "janela": janela,
            "janelas_labels": JANELAS_LABELS,
            "recentes": recentes,
            "media": media,
            "filtro": filtro,
            "ultimo": ultimo,
        },
    )
```

- [ ] **Step 2: Confirm it's broken exactly where expected**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros.tests.test_bebedouro_detalhe -v 2 2>&1 | tail -40`
Expected: FAIL — `TemplateSyntaxError` or `VariableDoesNotExist`-style
failures from `bebedouro_detalhe.html` still referencing `historico`
and the old "O que é monitorado" block. This is expected; Task 10 fixes
the template. Do not attempt to make this pass yet.

- [ ] **Step 3: Commit**

```bash
git add bebedouros/views.py
git commit -m "feat: bebedouro_detalhe usa coletas_recentes/media_coletas/situacao_filtro"
```

(Committing a known-red state here is intentional and matches this
plan's task boundaries — Task 10 is the next commit and turns the suite
green again. If your workflow prefers not to commit red states, squash
Tasks 9 and 10 into one commit instead.)

---

## Task 10: Reorganize `bebedouro_detalhe.html` + new CSS

**Files:**
- Modify: `bebedouros/templates/bebedouros/bebedouro_detalhe.html`
- Modify: `bebedouros/templates/bebedouros/base.html` (CSS only)

**Interfaces:**
- Consumes: template context from Task 9 (`recentes`, `media`,
  `filtro`), plus the still-present `situacao`, `pesos_iqab`, `grafico`,
  `janela`, `janelas_labels`, `ultimo`.

Section order per `DESENHO-PAGINA-DO-BEBEDOURO.md` §4: cabeçalho (with
now-public composição da nota) → manutenção do filtro → coletas
recentes → média → evolução (chart moves to the bottom).

- [ ] **Step 1: Rewrite the template**

Replace the full contents of
`bebedouros/templates/bebedouros/bebedouro_detalhe.html`:

```html
{% extends "bebedouros/base.html" %}
{% load l10n %}
{% block titulo %}{{ bebedouro.codigo }} — Monitoramento da Água — IFRN-CNAT{% endblock %}
{% block conteudo %}
  <div class="cabecalho-bebedouro">
    <div class="foto-placeholder" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="44" height="44" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="5" width="18" height="14" rx="2"/>
        <circle cx="8.5" cy="10" r="1.5"/>
        <path d="M21 15l-5-5-4 4-3-3-6 6"/>
      </svg>
    </div>
    <div class="gota-grande-wrap">
      {% if not ultimo.fora_de_operacao and situacao.resultado.iqab_status == "calculado" %}
        <span class="gota gota-lg gota-{{ situacao.resultado.iqab_faixa_slug }}"></span>
        <span class="gota-numero-grande">{{ situacao.resultado.iqab }}</span>
      {% else %}
        <span class="gota gota-lg gota-vazia"></span>
      {% endif %}
    </div>
    <div class="cabecalho-info">
      <h1>{{ bebedouro.codigo }} — {{ bebedouro.local }}</h1>
      {% if ultimo.fora_de_operacao %}
        <p class="cabecalho-classificacao">Fora de operação</p>
        <p class="cabecalho-status">
          desde {{ ultimo.coleta.data|date:"d/m/Y" }}
          {% if ultimo.observacao %} — {{ ultimo.observacao }}{% endif %}
        </p>
      {% elif situacao.resultado.iqab_status == "calculado" %}
        <p class="cabecalho-classificacao">{{ situacao.resultado.iqab_classificacao }}</p>
        <p class="cabecalho-status">última análise em {{ situacao.data|date:"d/m/Y" }}</p>
      {% else %}
        <p class="cabecalho-status">Ainda não há um IQA-B calculado para este bebedouro.</p>
      {% endif %}
    </div>
  </div>

  <section class="cartoes-indice">
    <h2>Composição da nota:</h2>
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

  <section class="manutencao-filtro">
    <h2>Manutenção do filtro</h2>
    {% if filtro.status == "sem_registro" %}
      <p class="filtro-status filtro-sem-registro">Sem registro de troca de filtro.</p>
    {% elif filtro.status == "ok" %}
      <p class="filtro-status filtro-ok">
        <span class="filtro-icone" aria-hidden="true">✅</span>
        Filtro trocado em {{ filtro.data_troca|date:"d/m/Y" }} — dentro da validade
        <span class="filtro-detalhe">(válido até {{ filtro.data_vencimento|date:"d/m/Y" }})</span>
      </p>
    {% else %}
      <p class="filtro-status filtro-vencido">
        <span class="filtro-icone" aria-hidden="true">❌</span>
        Filtro trocado em {{ filtro.data_troca|date:"d/m/Y" }} — venceu em {{ filtro.data_vencimento|date:"d/m/Y" }}
        <span class="filtro-detalhe">Há necessidade de troca.</span>
      </p>
    {% endif %}
  </section>

  <section class="coletas-recentes">
    <h2>Coletas recentes</h2>
    {% if recentes %}
      {% for resultado in recentes %}
        <details{% if forloop.first %} open{% endif %} class="historico-item">
          <summary>{{ resultado.coleta.data|date:"d/m/Y" }}</summary>
          <div class="historico-detalhe">
            {% if resultado.fora_de_operacao %}
              <p>Fora de operação nesta data.</p>
            {% else %}
              <p>IQA-B: {{ resultado.iqab_texto }}</p>
              {% if resultado.filtro == "vencido" %}
                <p>Filtro fora da validade.</p>
              {% endif %}
              <table>
                <thead><tr><th>Parâmetro</th><th>Valor</th></tr></thead>
                <tbody>
                  <tr><td>Cloro Residual Livre</td><td>{{ resultado.cloro|default:"—" }} mg/L Cl₂</td></tr>
                  <tr><td>Condutividade Elétrica</td><td>{{ resultado.condutividade|default:"—" }} µS/cm</td></tr>
                  <tr><td>Nitrato</td><td>{{ resultado.nitrato|default:"—" }} mg/L N</td></tr>
                  <tr><td>Turbidez</td><td>{{ resultado.turbidez_texto|default:"—" }} UNT</td></tr>
                  <tr><td>pH</td><td>{{ resultado.ph|default:"—" }}</td></tr>
                  <tr><td>Coliformes Totais</td><td>{{ resultado.get_coliformes_totais_display|default:"—" }}</td></tr>
                  <tr><td>E. coli</td><td>{{ resultado.get_ecoli_display|default:"—" }}</td></tr>
                </tbody>
              </table>
            {% endif %}
          </div>
        </details>
      {% endfor %}
    {% else %}
      <p class="historico-vazio">Ainda não há coletas registradas para este bebedouro.</p>
    {% endif %}
  </section>

  <section class="media-coletas">
    <h2>Média das coletas recentes ({{ media.quantidade }})</h2>
    {% if media.quantidade %}
      <div class="painel">
        <table>
          <thead><tr><th>Parâmetro</th><th>Valor</th></tr></thead>
          <tbody>
            <tr><td>Cloro Residual Livre</td><td>{{ media.cloro }} mg/L Cl₂</td></tr>
            <tr><td>Condutividade Elétrica</td><td>{{ media.condutividade }} µS/cm</td></tr>
            <tr><td>Nitrato</td><td>{{ media.nitrato }} mg/L N</td></tr>
            <tr><td>Turbidez</td><td>{{ media.turbidez }} UNT</td></tr>
            <tr><td>pH</td><td>{{ media.ph }}</td></tr>
            <tr>
              <td>Coliformes Totais</td>
              <td{% if media.coliformes_totais_alerta %} class="media-alerta"{% endif %}>{{ media.coliformes_totais }}</td>
            </tr>
            <tr>
              <td>E. coli</td>
              <td{% if media.ecoli_alerta %} class="media-alerta"{% endif %}>{{ media.ecoli }}</td>
            </tr>
            <tr><td>Média do IQA-B</td><td>{{ media.iqab_texto }}</td></tr>
          </tbody>
        </table>
      </div>
    {% else %}
      <p class="historico-vazio">Sem coletas para calcular a média.</p>
    {% endif %}
  </section>

  <section class="evolucao">
    <h2>Evolução</h2>
    <div class="grafico-selecao">
      <span class="grafico-selecao-grupo">
        <span class="grafico-selecao-rotulo">Período:</span>
        {% for chave, rotulo in janelas_labels.items %}
          <a href="?janela={{ chave }}" class="{% if chave == janela %}ativo{% endif %}">{{ rotulo }}</a>
        {% endfor %}
      </span>
    </div>

    {% if grafico %}
      {% localize off %}
      <svg class="grafico-svg" viewBox="0 0 {{ grafico.largura }} {{ grafico.altura }}">
        {% for faixa in grafico.faixas %}
          <rect class="grafico-faixa faixa-{{ faixa.slug }}" x="{{ grafico.area_esq }}" y="{{ faixa.y }}" width="{{ grafico.largura_area }}" height="{{ faixa.altura }}"></rect>
        {% endfor %}
        {% for segmento in grafico.segmentos %}
          <polyline class="grafico-linha" points="{% for p in segmento %}{{ p.x }},{{ p.y }} {% endfor %}"></polyline>
          {% for p in segmento %}
            <circle class="grafico-ponto" cx="{{ p.x }}" cy="{{ p.y }}" r="3.5"><title>{{ p.data|date:"d/m/Y" }}: {{ p.valor }}</title></circle>
          {% endfor %}
        {% endfor %}
        <text class="grafico-eixo-data" x="{{ grafico.area_esq }}" y="{{ grafico.altura|add:"-6" }}">{{ grafico.data_min|date:"d/m/Y" }}</text>
        <text class="grafico-eixo-data" x="{{ grafico.area_dir }}" y="{{ grafico.altura|add:"-6" }}" text-anchor="end">{{ grafico.data_max|date:"d/m/Y" }}</text>
      </svg>
      {% endlocalize %}
    {% else %}
      <p class="grafico-vazio">Ainda não há dados suficientes para o gráfico.</p>
    {% endif %}
  </section>
{% endblock %}
```

- [ ] **Step 2: Add CSS**

In `bebedouros/templates/bebedouros/base.html`, add after the existing
`.historico-vazio { color: var(--tinta-suave); }` rule:

```css
    .manutencao-filtro { margin-top: 20px; }
    .manutencao-filtro h2 { font-size: 16px; margin: 0 0 10px; }
    .filtro-status {
      display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 8px;
      padding: 10px 14px; margin: 0; border-radius: 8px; border: 1px solid transparent;
    }
    .filtro-ok { background: var(--ok-bg); border-color: var(--ok-bd); }
    .filtro-vencido { background: var(--erro-bg); border-color: var(--erro-bd); }
    .filtro-sem-registro { color: var(--tinta-suave); }
    .filtro-icone { font-size: 16px; }
    .filtro-detalhe { color: var(--tinta-suave); font-size: 13px; flex-basis: 100%; }
    .media-coletas { margin-top: 20px; }
    .media-coletas h2 { font-size: 16px; margin: 0 0 10px; }
    .media-alerta { color: #922; font-weight: 600; }
```

- [ ] **Step 3: Smoke check via the Django test client (no browser available to you — use this instead)**

Run this one-off script and confirm its output:

```bash
./.venv/Scripts/python.exe manage.py shell -c "
from django.test import Client
from bebedouros.models import Bebedouro
b, _ = Bebedouro.objects.get_or_create(numero=1)
resp = Client().get(f'/bebedouros/{b.pk}/')
assert resp.status_code == 200, resp.status_code
html = resp.content.decode()
marcos = ['Composição da nota', 'Manutenção do filtro', 'Coletas recentes', 'Média das coletas recentes', 'Evolução']
posicoes = [html.index(m) for m in marcos]
assert posicoes == sorted(posicoes), f'ordem errada: {list(zip(marcos, posicoes))}'
assert 'Sem registro de troca de filtro.' in html
print('OK — ordem das seções e filtro sem registro conferem')
"
```

Expected output: `OK — ordem das seções e filtro sem registro conferem`
(status code check is implicit — `.content` would raise on a 500).

- [ ] **Step 4: Commit**

```bash
git add bebedouros/templates/bebedouros/bebedouro_detalhe.html bebedouros/templates/bebedouros/base.html
git commit -m "feat: reorganiza a página do bebedouro (filtro, coletas recentes, média)"
```

(Full test suite is still red at this commit — `test_bebedouro_detalhe.py`
tests the *old* page structure. Task 11 rewrites that file and turns
everything green.)

---

## Task 11: Rewrite `test_bebedouro_detalhe.py`

**Files:**
- Modify: `bebedouros/tests/test_bebedouro_detalhe.py` (full rewrite)

This replaces every test that asserted old-structure text ("O que é
monitorado:", "Coletas anteriores" / "quinzena", "Filtro fora da
validade na última coleta.", cards hidden from the public) with tests
against the new structure, and adds coverage for the three new blocks.

- [ ] **Step 1: Replace the file**

```python
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

    def test_coleta_fora_de_operacao_conta_como_uma_das_5(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, fora_de_operacao=True)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "<summary>", count=1)
        self.assertContains(response, "Fora de operação nesta data.")

    # --- Média das coletas recentes ---

    def test_sem_coletas_mostra_mensagem_de_media_vazia(self):
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Sem coletas para calcular a média.")

    def test_media_aparece_aberta_sem_precisar_clicar(self):
        coleta = Coleta.objects.create(data=datetime.date.today(), status=Coleta.PUBLICADO)
        Resultado.objects.create(coleta=coleta, bebedouro=self.b1, **RESULTADO_COMPLETO)
        recalcular_coleta(coleta)
        response = self.client.get(f"/bebedouros/{self.b1.pk}/")
        self.assertContains(response, "Média das coletas recentes (1)")
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
        self.assertContains(response, "1,5 mg/L Cl")

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
```

- [ ] **Step 2: Run the full suite**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros -v 2 2>&1 | tail -80`
Expected: PASS — every test in the project, including the whole
rewritten file and every task committed since Task 4.

- [ ] **Step 3: Fix anything red**

If a specific assertion fails, read the actual rendered HTML
(`print(response.content.decode())` temporarily in the failing test) —
the most likely mismatches are exact wording (e.g. "1,5 mg/L Cl" vs the
real `number_format` output) or the `<details open>` vs `<details
open="">` rendering quirk (Django's `DateInput`/HTML boolean attributes
render as `open`, not `open=""`, for a literal `open` written in the
template — confirm by inspecting the response before changing the
assertion). Fix the test to match correct real behavior — do not change
`bebedouro_detalhe.html`'s section order or wording to make a test pass
if the design doc says otherwise; re-check
`DESENHO-PAGINA-DO-BEBEDOURO.md` first.

- [ ] **Step 4: Commit**

```bash
git add bebedouros/tests/test_bebedouro_detalhe.py
git commit -m "test: reescreve os testes da página do bebedouro para a nova estrutura"
```

---

## Task 12: Final check — `manage.py check`, full suite, manual walk-through

**Files:** none (verification only)

- [ ] **Step 1: Django system check**

Run: `./.venv/Scripts/python.exe manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Migrations are in sync**

Run: `./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
Expected: no output, exit code 0 (no missing migrations).

- [ ] **Step 3: Full test suite**

Run: `./.venv/Scripts/python.exe manage.py test bebedouros`
Expected: `OK`, same or higher test count than the 171 baseline this
plan started from.

- [ ] **Step 4: End-to-end walk-through via the Django test client (no browser available to you — use this instead)**

Run this one-off script — it plays the real flow (log in as staff,
create a coleta, fill the grade including "Troca de filtro realizada
em", save as rascunho, publish, then re-fetch the page logged out) and
confirms what a visitor would actually see:

```bash
./.venv/Scripts/python.exe manage.py shell -c "
import datetime
from django.contrib.auth.models import User
from django.test import Client
from bebedouros.models import Bebedouro, Coleta

User.objects.filter(username='_smoke').delete()
User.objects.create_user('_smoke', password='segredo')
b, _ = Bebedouro.objects.get_or_create(numero=1)
staff = Client()
staff.login(username='_smoke', password='segredo')
staff.post('/coletas/nova/', {'data': '2026-09-01'})
coleta = Coleta.objects.get(data=datetime.date(2026, 9, 1))
dados = {
    f'b{b.id}-cloro': '1,0', f'b{b.id}-nitrato': '5,0', f'b{b.id}-ph': '7,0',
    f'b{b.id}-turbidez': '0,5', f'b{b.id}-coliformes_totais': 'AUSENTE',
    f'b{b.id}-ecoli': 'AUSENTE', f'b{b.id}-filtro': 'dentro',
    f'b{b.id}-troca_filtro': '2026-09-01',
}
staff.post(f'/coletas/{coleta.pk}/lancamento/', dados)
staff.post(f'/coletas/{coleta.pk}/publicar/', {'confirmar': '1'})

visitante = Client()
resp = visitante.get(f'/bebedouros/{b.pk}/')
assert resp.status_code == 200
html = resp.content.decode()
for esperado in ['Composição da nota', '✅', 'dentro da validade', '01/09/2026', 'Média das coletas recentes (1)']:
    assert esperado in html, f'faltando: {esperado!r}'
print('OK — fluxo completo (lançar, publicar, ver como visitante) confere')
User.objects.filter(username='_smoke').delete()
coleta.delete()
"
```

Expected output: `OK — fluxo completo (lançar, publicar, ver como
visitante) confere`. The script cleans up its own test user and coleta
at the end either way — if it fails partway, remove them manually
before re-running (`Coleta.objects.filter(data=datetime.date(2026,9,1)).delete()`).

Note: this runs against the real local `db.sqlite3` (not an isolated
test database) — it's the only way to exercise the actual dev database
outside the test suite. Harmless today (gitignored file, cleaned up
above), but once real 2024/2025 data has been typed in, re-run this
check against a copy of the database instead of the live one.

- [ ] **Step 5: Update the progress log**

Append a new section to `docs/plans/PROGRESSO-execucao.md` recording
this plan's completion, following the same format as the existing
entries (tasks done, commit refs, any rulings made mid-implementation).

- [ ] **Step 6: Final commit**

```bash
git add docs/plans/PROGRESSO-execucao.md
git commit -m "docs: registra execução do plano de ajustes da página do bebedouro"
```
