# Entrada, Armazenamento e Gerenciamento dos Resultados — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the internal web screens and storage that let the project team register drinking-fountain lab results per collection date, save them as draft, publish them, and manage them (list / correct a value / delete a whole collection).

**Architecture:** A single Django project. The built-in Django admin covers the fountain registry ("cadastro dos bebedouros"). Custom views cover the per-date entry grid, the collection list, publish, and delete. Data lives in three models — `Bebedouro`, `Coleta`, `Resultado` — in one app. Access to every internal page requires login; the project uses one shared account (Django's default `User`), and Django's own admin login page is the login screen. Nothing here computes the IQA-B index, renders the public site, or imports historical spreadsheets — those are later stages.

**Tech Stack:** Python 3.12+, Django 5.1+ (uses features available in 5.1), SQLite in development, PostgreSQL in production via `dj-database-url`, `whitenoise` for static files, `gunicorn` as the production server. Django's built-in test framework (`manage.py test`) for tests. All dependencies pinned in `requirements.txt`. No frontend build step, no JS framework.

**Spec:** `../../DESENHO-ENTRADA-E-RESULTADOS.md` (plain-language design, approved 02/09/2026). The companion project definition is `../../DEFINICAO-DO-PROJETO.md`.

## Global Constraints

- **Python** >= 3.12; **Django** >= 5.1, < 6.0.
- **One shared account only.** No per-person users, no permission levels, no custom user model. The login screen is Django admin's login (`LOGIN_URL = "/admin/login/"`).
- **Every internal view requires login** (`@login_required` on each view function).
- **All user-facing text in Brazilian Portuguese.** Code identifiers in Portuguese where they name domain concepts (`Bebedouro`, `Coleta`, `Resultado`, `lancamento`), matching the spec and the definition document.
- **Fixed parameter list.** The 7 parameters plus filter status are model fields, not configurable rows. Grid column headers show units: Cloro (mg/L Cl₂), Condutividade (µS/cm), Nitrato (mg/L N), Turbidez (UNT), pH (sem unidade).
- **No change history.** Corrections overwrite values; do not store previous values. There is no audit model.
- **Blank is always allowed** in a `Resultado`. No measurement field is required at any point.
- **Validation warnings never block a save.** "Strange value" checks (pH outside 0–14, negative numbers) produce messages only; the save still completes.
- **`Coleta.data` is unique** (one collection per calendar date).
- **Deleting a `Coleta` deletes its `Resultado` rows** (cascade) and is allowed for both `rascunho` and `publicado`.
- **Keep it portable:** settings read host specifics (secret key, database URL, allowed hosts, debug) from environment variables with safe local defaults, so moving hosting providers (and, later, to IFRN infrastructure) needs only env-var changes.
- Currency of "free tier" hosting provider is out of scope for this plan; the plan must not hard-code any provider.

---

### Task 1: Project skeleton, settings, auth gate, base template

**Files:**
- Create: `manage.py`, `sistema_agua/__init__.py`, `sistema_agua/settings.py`, `sistema_agua/urls.py`, `sistema_agua/wsgi.py`, `sistema_agua/asgi.py`
- Create: `bebedouros/__init__.py`, `bebedouros/apps.py`, `bebedouros/models.py` (empty for now), `bebedouros/views.py`, `bebedouros/urls.py`
- Create: `bebedouros/templates/bebedouros/base.html`, `bebedouros/templates/bebedouros/coleta_list.html`
- Create: `.gitignore`
- Test: `bebedouros/tests/__init__.py`, `bebedouros/tests/test_auth.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - URL name `coleta_list` at path `/`, view `bebedouros.views.coleta_list(request)`, `@login_required`, renders `bebedouros/coleta_list.html` with context `{"coletas": <iterable>}`.
  - `LOGIN_URL = "/admin/login/"` in settings.
  - Installed app label `bebedouros`.
  - Template `bebedouros/base.html` with blocks `{% block conteudo %}` and a rendered `messages` loop.

- [ ] **Step 1: Scaffold the project**

Run:
```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on POSIX
pip install "Django>=5.1,<6.0"
django-admin startproject sistema_agua .
python manage.py startapp bebedouros
git init
```

- [ ] **Step 2: Write the failing test**

`bebedouros/tests/test_auth.py`:
```python
from django.test import TestCase
from django.contrib.auth.models import User


class AuthGateTests(TestCase):
    def test_home_redirects_anonymous_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_home_ok_when_logged_in(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_auth -v 2`
Expected: FAIL — no URL configured at `/` (404, not 302), or `TemplateDoesNotExist`.

- [ ] **Step 4: Implement settings, app config, urls, view, templates**

`bebedouros/apps.py`:
```python
from django.apps import AppConfig


class BebedourosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bebedouros"
```

In `sistema_agua/settings.py` — replace the relevant blocks:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inseguro-troque-em-producao")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bebedouros",
]

# MIDDLEWARE: keep the default list startproject generated.

ROOT_URLCONF = "sistema_agua.urls"

# TEMPLATES: keep default; APP_DIRS is True so bebedouros/templates/ is found.

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
```

`sistema_agua/urls.py`:
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("bebedouros.urls")),
]
```

`bebedouros/urls.py`:
```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.coleta_list, name="coleta_list"),
]
```

`bebedouros/views.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": []})
```

`bebedouros/templates/bebedouros/base.html`:
```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block titulo %}Monitoramento da Água — IFRN-CNAT{% endblock %}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; color: #1b1b1b; }
    header { background: #005a9c; color: #fff; padding: 12px 20px; }
    header a { color: #fff; margin-right: 16px; text-decoration: none; }
    main { padding: 20px; max-width: 1100px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; }
    .msg { padding: 8px 12px; margin: 6px 0; border-radius: 4px; }
    .msg.warning { background: #fff3cd; }
    .msg.error { background: #f8d7da; }
    .msg.success { background: #d1e7dd; }
    .etiqueta { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .etiqueta.rascunho { background: #e2e3e5; }
    .etiqueta.publicado { background: #d1e7dd; }
    .bloqueada { background: #f2f2f2; color: #888; }
  </style>
</head>
<body>
  <header>
    <a href="{% url 'coleta_list' %}">Coletas</a>
    <a href="/admin/bebedouros/bebedouro/">Cadastro de bebedouros</a>
    <a href="/admin/logout/">Sair</a>
  </header>
  <main>
    {% for message in messages %}
      <div class="msg {{ message.tags }}">{{ message }}</div>
    {% endfor %}
    {% block conteudo %}{% endblock %}
  </main>
</body>
</html>
```

`bebedouros/templates/bebedouros/coleta_list.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Coletas</h1>
  <p>Nenhuma coleta lançada ainda.</p>
{% endblock %}
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
db.sqlite3
staticfiles/
.env
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test bebedouros.tests.test_auth -v 2`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: Django skeleton, login gate, base template"
```

---

### Task 2: `Bebedouro` model + admin (cadastro) + seed command

**Files:**
- Modify: `bebedouros/models.py`
- Create: `bebedouros/admin.py`
- Create: `bebedouros/management/__init__.py`, `bebedouros/management/commands/__init__.py`, `bebedouros/management/commands/seed_bebedouros.py`
- Create: `bebedouros/migrations/0001_initial.py` (via `makemigrations`)
- Test: `bebedouros/tests/test_bebedouro.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `bebedouros.models.Bebedouro` with fields `numero` (PositiveSmallIntegerField, unique), `local` (CharField, blank), `ativo` (BooleanField, default True); property `codigo` -> `str` returning `f"B{self.numero}"`; `Meta.ordering = ["numero"]`; `__str__` returns `codigo`.
  - Admin registration so `/admin/bebedouros/bebedouro/` lists code, local, ativo.
  - Management command `seed_bebedouros` creating `numero` 1..15 if absent.

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_bebedouro.py`:
```python
from django.test import TestCase
from django.core.management import call_command

from bebedouros.models import Bebedouro


class BebedouroTests(TestCase):
    def test_codigo_property(self):
        b = Bebedouro.objects.create(numero=7, local="Piscinas")
        self.assertEqual(b.codigo, "B7")
        self.assertEqual(str(b), "B7")

    def test_ordering_is_numeric_not_lexical(self):
        Bebedouro.objects.create(numero=10)
        Bebedouro.objects.create(numero=2)
        codigos = [b.codigo for b in Bebedouro.objects.all()]
        self.assertEqual(codigos, ["B2", "B10"])

    def test_seed_creates_15_and_is_idempotent(self):
        call_command("seed_bebedouros")
        self.assertEqual(Bebedouro.objects.count(), 15)
        call_command("seed_bebedouros")
        self.assertEqual(Bebedouro.objects.count(), 15)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_bebedouro -v 2`
Expected: FAIL — `ImportError` / `Bebedouro` has no such fields / unknown command `seed_bebedouros`.

- [ ] **Step 3: Implement**

`bebedouros/models.py`:
```python
from django.db import models


class Bebedouro(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    local = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]

    @property
    def codigo(self):
        return f"B{self.numero}"

    def __str__(self):
        return self.codigo
```

`bebedouros/admin.py`:
```python
from django.contrib import admin

from .models import Bebedouro


@admin.register(Bebedouro)
class BebedouroAdmin(admin.ModelAdmin):
    list_display = ["codigo", "local", "ativo"]
    list_display_links = ["codigo"]
    list_editable = ["local", "ativo"]
    ordering = ["numero"]
    fields = ["numero", "local", "ativo"]

    @admin.display(description="Código", ordering="numero")
    def codigo(self, obj):
        return obj.codigo
```

`bebedouros/management/commands/seed_bebedouros.py` (real list confirmed 02/09/2026; all active; GPS coordinates from `Análise dos Bebedouros 2026.xlsx` are kept for the future public-map stage and intentionally not stored here):
```python
from django.core.management.base import BaseCommand

from bebedouros.models import Bebedouro

LOCAIS = {
    1: "Mesas verdes",
    2: "Piscinas",
    3: "Marcenaria",
    4: "Quadra 3",
    5: "Quadra 1",
    6: "Biblioteca",
    7: "Campo",
    8: "Bloco C",
    9: "Bloco B",
    10: "Bloco D",
    11: "DIATINF",
    12: "DIACON",
    13: "DIAC",
    14: "DIAREN 1",
    15: "DIAREN 2",
}


class Command(BaseCommand):
    help = "Cria B1..B15 com os locais reais se ainda não existirem."

    def handle(self, *args, **options):
        criados = 0
        for numero, local in LOCAIS.items():
            _, novo = Bebedouro.objects.get_or_create(
                numero=numero, defaults={"local": local}
            )
            criados += int(novo)
        self.stdout.write(self.style.SUCCESS(f"{criados} bebedouro(s) criado(s)."))
```

Run: `python manage.py makemigrations bebedouros`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_bebedouro -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Bebedouro model, admin cadastro, seed command"
```

---

### Task 3: `Coleta` model + collection list view

**Files:**
- Modify: `bebedouros/models.py`, `bebedouros/views.py`, `bebedouros/urls.py`
- Modify: `bebedouros/templates/bebedouros/coleta_list.html`
- Create: `bebedouros/migrations/0002_coleta.py` (via `makemigrations`)
- Test: `bebedouros/tests/test_coleta_model.py`, `bebedouros/tests/test_coleta_list.py`

**Interfaces:**
- Consumes: `coleta_list` URL name and view from Task 1 (replaces its body).
- Produces:
  - `bebedouros.models.Coleta` with `data` (DateField, unique), `status` (CharField, `choices=STATUS_CHOICES`, default `Coleta.RASCUNHO`), `criada_em`/`atualizada_em` timestamps. Class constants `RASCUNHO = "rascunho"`, `PUBLICADO = "publicado"`, `STATUS_CHOICES`. `Meta.ordering = ["-data"]`. `__str__` -> `f"Coleta de {self.data:%d/%m/%Y}"`. Property `publicada` -> `bool`.
  - `coleta_list` view renders `coleta_list.html` with `{"coletas": Coleta.objects.all()}`.

- [ ] **Step 1: Write the failing tests**

`bebedouros/tests/test_coleta_model.py`:
```python
import datetime

from django.db import IntegrityError
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaModelTests(TestCase):
    def test_defaults_to_rascunho(self):
        c = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.assertEqual(c.status, Coleta.RASCUNHO)
        self.assertFalse(c.publicada)

    def test_data_is_unique(self):
        Coleta.objects.create(data=datetime.date(2026, 9, 1))
        with self.assertRaises(IntegrityError):
            Coleta.objects.create(data=datetime.date(2026, 9, 1))
```

`bebedouros/tests/test_coleta_list.py`:
```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaListTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")

    def test_lists_collections_newest_first(self):
        Coleta.objects.create(data=datetime.date(2026, 8, 1))
        Coleta.objects.create(data=datetime.date(2026, 9, 1))
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        corpo = response.content.decode()
        self.assertLess(corpo.index("01/09/2026"), corpo.index("01/08/2026"))
        self.assertIn("Rascunho", corpo)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_coleta_model bebedouros.tests.test_coleta_list -v 2`
Expected: FAIL — `Coleta` does not exist.

- [ ] **Step 3: Implement**

Append to `bebedouros/models.py`:
```python
class Coleta(models.Model):
    RASCUNHO = "rascunho"
    PUBLICADO = "publicado"
    STATUS_CHOICES = [(RASCUNHO, "Rascunho"), (PUBLICADO, "Publicado")]

    data = models.DateField(unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=RASCUNHO)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"Coleta de {self.data:%d/%m/%Y}"

    @property
    def publicada(self):
        return self.status == self.PUBLICADO
```

`bebedouros/views.py` — replace `coleta_list`:
```python
from .models import Coleta


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": Coleta.objects.all()})
```

`bebedouros/templates/bebedouros/coleta_list.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Coletas</h1>
  <p><a href="{% url 'coleta_nova' %}">+ Nova coleta</a></p>
  {% if coletas %}
    <table>
      <thead><tr><th>Data</th><th>Situação</th><th></th></tr></thead>
      <tbody>
      {% for coleta in coletas %}
        <tr>
          <td>{{ coleta.data|date:"d/m/Y" }}</td>
          <td><span class="etiqueta {{ coleta.status }}">{{ coleta.get_status_display }}</span></td>
          <td>
            <a href="{% url 'lancamento' coleta.pk %}">Abrir</a>
            &nbsp;|&nbsp;
            <a href="{% url 'apagar' coleta.pk %}">Apagar</a>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>Nenhuma coleta lançada ainda.</p>
  {% endif %}
{% endblock %}
```

> The template references `coleta_nova`, `lancamento`, and `apagar` URL names, added in Tasks 4, 6, and 10. Add placeholder `path()` entries now pointing at a stub `views.em_breve` OR implement Tasks 4/6/10 before running the full server. For this task's tests (which only assert on rendered dates and "Rascunho"), add the three URL names as stubs:

`bebedouros/urls.py`:
```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.coleta_list, name="coleta_list"),
    path("coletas/nova/", views.coleta_nova, name="coleta_nova"),
    path("coletas/<int:pk>/lancamento/", views.lancamento, name="lancamento"),
    path("coletas/<int:pk>/publicar/", views.publicar, name="publicar"),
    path("coletas/<int:pk>/apagar/", views.apagar, name="apagar"),
]
```

Add temporary stubs to `bebedouros/views.py` (each replaced in its own task):
```python
from django.http import HttpResponse


@login_required
def coleta_nova(request):
    return HttpResponse("stub")


@login_required
def lancamento(request, pk):
    return HttpResponse("stub")


@login_required
def publicar(request, pk):
    return HttpResponse("stub")


@login_required
def apagar(request, pk):
    return HttpResponse("stub")
```

Run: `python manage.py makemigrations bebedouros`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_coleta_model bebedouros.tests.test_coleta_list -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Coleta model and collection list view"
```

---

### Task 4: Create a collection (pick date, duplicate-date warning)

**Files:**
- Modify: `bebedouros/views.py` (replace `coleta_nova` stub)
- Create: `bebedouros/forms.py`
- Create: `bebedouros/templates/bebedouros/coleta_nova.html`
- Test: `bebedouros/tests/test_coleta_nova.py`

**Interfaces:**
- Consumes: `Coleta` model (Task 3); `lancamento` URL name (stub until Task 6).
- Produces:
  - `bebedouros.forms.ColetaForm` — a `ModelForm` on `Coleta` with `fields = ["data"]`, `data` widget `DateInput(attrs={"type": "date"})`.
  - `coleta_nova` view: `GET` renders the form; `POST` with a new date creates the `Coleta` and redirects to `lancamento` for its pk; `POST` with an already-used date re-renders the form with a `messages.error` and context `existente` (the conflicting `Coleta`).

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_coleta_nova.py`:
```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Coleta


class ColetaNovaTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")

    def test_creates_collection_and_redirects_to_grid(self):
        response = self.client.post("/coletas/nova/", {"data": "2026-09-15"})
        coleta = Coleta.objects.get()
        self.assertEqual(coleta.data, datetime.date(2026, 9, 15))
        self.assertRedirects(response, f"/coletas/{coleta.pk}/lancamento/")

    def test_duplicate_date_is_rejected_with_message(self):
        Coleta.objects.create(data=datetime.date(2026, 9, 15))
        response = self.client.post("/coletas/nova/", {"data": "2026-09-15"}, follow=True)
        self.assertEqual(Coleta.objects.count(), 1)
        self.assertContains(response, "Já existe uma coleta")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_coleta_nova -v 2`
Expected: FAIL — stub returns "stub", no redirect.

- [ ] **Step 3: Implement**

`bebedouros/forms.py`:
```python
from django import forms

from .models import Coleta


class ColetaForm(forms.ModelForm):
    class Meta:
        model = Coleta
        fields = ["data"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}
```

`bebedouros/views.py` — replace `coleta_nova`:
```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from .forms import ColetaForm


@login_required
def coleta_nova(request):
    if request.method == "POST":
        form = ColetaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data["data"]
            existente = Coleta.objects.filter(data=data).first()
            if existente:
                messages.error(
                    request,
                    f"Já existe uma coleta em {data:%d/%m/%Y}. Abra-a para editar.",
                )
                return render(
                    request,
                    "bebedouros/coleta_nova.html",
                    {"form": form, "existente": existente},
                )
            coleta = form.save()
            return redirect("lancamento", pk=coleta.pk)
    else:
        form = ColetaForm()
    return render(request, "bebedouros/coleta_nova.html", {"form": form})
```

`bebedouros/templates/bebedouros/coleta_nova.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Nova coleta</h1>
  <form method="post">
    {% csrf_token %}
    <p>Data da coleta: {{ form.data }}</p>
    {{ form.data.errors }}
    <button type="submit">Criar</button>
  </form>
  {% if existente %}
    <p><a href="{% url 'lancamento' existente.pk %}">Abrir a coleta existente</a></p>
  {% endif %}
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test bebedouros.tests.test_coleta_nova -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: create collection with duplicate-date guard"
```

---

### Task 5: `Resultado` model + `esta_vazio()`

**Files:**
- Modify: `bebedouros/models.py`
- Create: `bebedouros/migrations/0003_resultado.py` (via `makemigrations`)
- Test: `bebedouros/tests/test_resultado_model.py`

**Interfaces:**
- Consumes: `Bebedouro` (Task 2), `Coleta` (Task 3).
- Produces `bebedouros.models.Resultado`:
  - FKs: `coleta` (`on_delete=CASCADE`, `related_name="resultados"`), `bebedouro` (`on_delete=PROTECT`, `related_name="resultados"`).
  - `fora_de_operacao` (BooleanField, default False); `observacao` (CharField 200, blank).
  - Numeric, all `null=True, blank=True`: `cloro`, `condutividade`, `nitrato`, `turbidez_valor` — `DecimalField(max_digits=10, decimal_places=3)`; `ph` — `DecimalField(max_digits=5, decimal_places=2)`.
  - `turbidez_abaixo_limite` (BooleanField, default False).
  - Choice fields (blank allowed, default `""`): `coliformes_totais`, `ecoli` use `Resultado.MICRO_CHOICES`; `filtro` uses `Resultado.FILTRO_CHOICES`.
  - Class constants: `AUSENTE = "AUSENTE"`, `PRESENTE = "PRESENTE"`, `MICRO_CHOICES = [("", "—"), (AUSENTE, "Ausente"), (PRESENTE, "Presente")]`, `FILTRO_DENTRO = "dentro"`, `FILTRO_VENCIDO = "vencido"`, `FILTRO_CHOICES = [("", "—"), (FILTRO_DENTRO, "Dentro da validade"), (FILTRO_VENCIDO, "Vencido")]`.
  - `Meta.constraints`: `UniqueConstraint(fields=["coleta", "bebedouro"], name="uniq_resultado_por_bebedouro_na_coleta")`.
  - `esta_vazio()` -> `bool`: `True` only when every numeric field is `None`, `turbidez_abaixo_limite` is `False`, all three choice fields are `""`, and `observacao` is `""`. Ignores `fora_de_operacao`.
  - `__str__` -> `f"{self.bebedouro.codigo} @ {self.coleta.data:%d/%m/%Y}"`.

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_resultado_model.py`:
```python
import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class ResultadoModelTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def test_blank_result_is_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        self.assertTrue(r.esta_vazio())

    def test_any_value_makes_it_not_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.20"))
        self.assertFalse(r.esta_vazio())

    def test_fora_de_operacao_alone_still_counts_as_empty(self):
        r = Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, fora_de_operacao=True)
        self.assertTrue(r.esta_vazio())

    def test_one_result_per_bebedouro_per_coleta(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)

    def test_deleting_coleta_deletes_results(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1)
        self.coleta.delete()
        self.assertEqual(Resultado.objects.count(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_resultado_model -v 2`
Expected: FAIL — `Resultado` does not exist.

- [ ] **Step 3: Implement**

Append to `bebedouros/models.py`:
```python
class Resultado(models.Model):
    AUSENTE = "AUSENTE"
    PRESENTE = "PRESENTE"
    MICRO_CHOICES = [("", "—"), (AUSENTE, "Ausente"), (PRESENTE, "Presente")]

    FILTRO_DENTRO = "dentro"
    FILTRO_VENCIDO = "vencido"
    FILTRO_CHOICES = [
        ("", "—"),
        (FILTRO_DENTRO, "Dentro da validade"),
        (FILTRO_VENCIDO, "Vencido"),
    ]

    coleta = models.ForeignKey(Coleta, on_delete=models.CASCADE, related_name="resultados")
    bebedouro = models.ForeignKey(Bebedouro, on_delete=models.PROTECT, related_name="resultados")

    fora_de_operacao = models.BooleanField(default=False)
    observacao = models.CharField(max_length=200, blank=True)

    cloro = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    condutividade = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    nitrato = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    turbidez_valor = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    turbidez_abaixo_limite = models.BooleanField(default=False)
    ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    coliformes_totais = models.CharField(max_length=10, choices=MICRO_CHOICES, blank=True, default="")
    ecoli = models.CharField(max_length=10, choices=MICRO_CHOICES, blank=True, default="")
    filtro = models.CharField(max_length=10, choices=FILTRO_CHOICES, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["coleta", "bebedouro"],
                name="uniq_resultado_por_bebedouro_na_coleta",
            )
        ]

    def __str__(self):
        return f"{self.bebedouro.codigo} @ {self.coleta.data:%d/%m/%Y}"

    def esta_vazio(self):
        numericos = [self.cloro, self.condutividade, self.nitrato, self.turbidez_valor, self.ph]
        if any(v is not None for v in numericos):
            return False
        if self.turbidez_abaixo_limite:
            return False
        if self.coliformes_totais or self.ecoli or self.filtro:
            return False
        if self.observacao:
            return False
        return True
```

Run: `python manage.py makemigrations bebedouros`

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test bebedouros.tests.test_resultado_model -v 2`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Resultado model with esta_vazio and per-collection uniqueness"
```

---

### Task 6: The entry grid — display (GET)

**Files:**
- Modify: `bebedouros/forms.py` (add `ResultadoRowForm`, `parse_turbidez`)
- Modify: `bebedouros/views.py` (replace `lancamento` stub with GET behavior; add `_linhas`, `_initial_de` helpers)
- Create: `bebedouros/templates/bebedouros/lancamento.html`
- Test: `bebedouros/tests/test_lancamento_get.py`, `bebedouros/tests/test_parse_turbidez.py`

**Interfaces:**
- Consumes: `Coleta`, `Bebedouro`, `Resultado` models.
- Produces:
  - `bebedouros.forms.parse_turbidez(texto: str | None) -> tuple[Decimal | None, bool]`. Accepts `""`, `"0,751"`, `"0.751"`, `"<0,751"`, `"< 0.751"`. Comma is treated as decimal separator. Leading `<` (after stripping spaces) sets the bool to `True`. Raises `ValueError` for anything else.
  - `bebedouros.forms.ResultadoRowForm` — a plain `forms.Form`, every field `required=False`: `cloro`, `condutividade`, `nitrato`, `ph` = `DecimalField(localize=True)`; `turbidez` = `CharField`; `coliformes_totais`, `ecoli` = `ChoiceField(choices=Resultado.MICRO_CHOICES)`; `filtro` = `ChoiceField(choices=Resultado.FILTRO_CHOICES)`; `fora_de_operacao` = `BooleanField`; `observacao` = `CharField(max_length=200)`.
  - `lancamento(request, pk)` GET: renders `lancamento.html` with `{"coleta": coleta, "linhas": [...]}` where each linha is `{"bebedouro": Bebedouro, "bloqueada": bool, "resultado": Resultado | None, "form": ResultadoRowForm | None}`. `bloqueada` is `True` exactly when `not bebedouro.ativo`; blocked rows carry `form=None`. Form prefix per row is `f"b{bebedouro.id}"`.
  - Helper `_initial_de(resultado) -> dict` producing the row form's `initial`; turbidez initial is `f"<{valor}"` when `turbidez_abaixo_limite` else the numeric value.

- [ ] **Step 1: Write the failing tests**

`bebedouros/tests/test_parse_turbidez.py`:
```python
from decimal import Decimal

from django.test import SimpleTestCase

from bebedouros.forms import parse_turbidez


class ParseTurbidezTests(SimpleTestCase):
    def test_blank(self):
        self.assertEqual(parse_turbidez(""), (None, False))

    def test_plain_number_with_comma(self):
        self.assertEqual(parse_turbidez("0,751"), (Decimal("0.751"), False))

    def test_below_detection_limit(self):
        self.assertEqual(parse_turbidez("<0,751"), (Decimal("0.751"), True))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_turbidez("abc")
```

`bebedouros/tests/test_lancamento_get.py`:
```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta


class LancamentoGetTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.ativo = Bebedouro.objects.create(numero=1, local="Mesas verdes")
        self.inativo = Bebedouro.objects.create(numero=2, local="Piscinas", ativo=False)

    def test_grid_shows_editable_row_for_active_and_locked_for_inactive(self):
        response = self.client.get(f"/coletas/{self.coleta.pk}/lancamento/")
        self.assertEqual(response.status_code, 200)
        linhas = response.context["linhas"]
        por_codigo = {l["bebedouro"].codigo: l for l in linhas}
        self.assertIsNotNone(por_codigo["B1"]["form"])
        self.assertFalse(por_codigo["B1"]["bloqueada"])
        self.assertIsNone(por_codigo["B2"]["form"])
        self.assertTrue(por_codigo["B2"]["bloqueada"])
        self.assertContains(response, "fora de operação")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_parse_turbidez bebedouros.tests.test_lancamento_get -v 2`
Expected: FAIL — `parse_turbidez` / `ResultadoRowForm` missing; `lancamento` returns "stub".

- [ ] **Step 3: Implement**

Append to `bebedouros/forms.py`:
```python
from decimal import Decimal, InvalidOperation

from .models import Resultado


def parse_turbidez(texto):
    if texto is None:
        return None, False
    t = texto.strip().replace(" ", "").replace(",", ".")
    if t == "":
        return None, False
    abaixo = False
    if t.startswith("<"):
        abaixo = True
        t = t[1:]
    try:
        return Decimal(t), abaixo
    except InvalidOperation:
        raise ValueError(f"Valor de turbidez não reconhecido: {texto!r}")


class ResultadoRowForm(forms.Form):
    cloro = forms.DecimalField(required=False, localize=True)
    condutividade = forms.DecimalField(required=False, localize=True)
    nitrato = forms.DecimalField(required=False, localize=True)
    turbidez = forms.CharField(required=False)
    ph = forms.DecimalField(required=False, localize=True)
    coliformes_totais = forms.ChoiceField(required=False, choices=Resultado.MICRO_CHOICES)
    ecoli = forms.ChoiceField(required=False, choices=Resultado.MICRO_CHOICES)
    filtro = forms.ChoiceField(required=False, choices=Resultado.FILTRO_CHOICES)
    fora_de_operacao = forms.BooleanField(required=False)
    observacao = forms.CharField(required=False, max_length=200)
```

`bebedouros/views.py` — add helpers and replace `lancamento`:
```python
from .forms import ColetaForm, ResultadoRowForm, parse_turbidez
from .models import Bebedouro, Coleta, Resultado


def _initial_de(resultado):
    if resultado is None:
        return {}
    if resultado.turbidez_abaixo_limite and resultado.turbidez_valor is not None:
        turbidez = f"<{resultado.turbidez_valor}"
    elif resultado.turbidez_abaixo_limite:
        turbidez = "<"
    else:
        turbidez = resultado.turbidez_valor
    return {
        "cloro": resultado.cloro,
        "condutividade": resultado.condutividade,
        "nitrato": resultado.nitrato,
        "turbidez": turbidez,
        "ph": resultado.ph,
        "coliformes_totais": resultado.coliformes_totais,
        "ecoli": resultado.ecoli,
        "filtro": resultado.filtro,
        "fora_de_operacao": resultado.fora_de_operacao,
        "observacao": resultado.observacao,
    }


def _linhas(coleta, dados_post=None):
    resultados = {r.bebedouro_id: r for r in coleta.resultados.select_related("bebedouro")}
    linhas = []
    for bebedouro in Bebedouro.objects.all():
        resultado = resultados.get(bebedouro.id)
        prefix = f"b{bebedouro.id}"
        if not bebedouro.ativo:
            linhas.append(
                {"bebedouro": bebedouro, "bloqueada": True, "resultado": resultado, "form": None}
            )
            continue
        if dados_post is not None:
            form = ResultadoRowForm(dados_post, prefix=prefix)
        else:
            form = ResultadoRowForm(prefix=prefix, initial=_initial_de(resultado))
        linhas.append(
            {"bebedouro": bebedouro, "bloqueada": False, "resultado": resultado, "form": form}
        )
    return linhas


@login_required
def lancamento(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    return render(
        request,
        "bebedouros/lancamento.html",
        {"coleta": coleta, "linhas": _linhas(coleta)},
    )
```

`bebedouros/templates/bebedouros/lancamento.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Coleta de {{ coleta.data|date:"d/m/Y" }}
    <span class="etiqueta {{ coleta.status }}">{{ coleta.get_status_display }}</span>
  </h1>
  <form method="post">
    {% csrf_token %}
    <table>
      <thead>
        <tr>
          <th>Bebedouro</th><th>Cloro</th><th>Condutividade</th><th>Nitrato</th>
          <th>Turbidez</th><th>pH</th><th>Coliformes totais</th><th>E. coli</th>
          <th>Filtro</th><th>Fora de operação nesta data</th><th>Observação</th>
        </tr>
      </thead>
      <tbody>
      {% for linha in linhas %}
        {% if linha.bloqueada %}
          <tr class="bloqueada">
            <td>{{ linha.bebedouro.codigo }}</td>
            <td colspan="10">Fora de operação (bebedouro desativado)</td>
          </tr>
        {% else %}
          <tr>
            <td>{{ linha.bebedouro.codigo }}</td>
            <td>{{ linha.form.cloro }}</td>
            <td>{{ linha.form.condutividade }}</td>
            <td>{{ linha.form.nitrato }}</td>
            <td>{{ linha.form.turbidez }}</td>
            <td>{{ linha.form.ph }}</td>
            <td>{{ linha.form.coliformes_totais }}</td>
            <td>{{ linha.form.ecoli }}</td>
            <td>{{ linha.form.filtro }}</td>
            <td>{{ linha.form.fora_de_operacao }}</td>
            <td>{{ linha.form.observacao }}</td>
          </tr>
        {% endif %}
      {% endfor %}
      </tbody>
    </table>
    <p>
      <button type="submit" name="acao" value="salvar">Salvar rascunho</button>
      <button type="submit" name="acao" value="publicar" formaction="{% url 'publicar' coleta.pk %}">Publicar</button>
    </p>
  </form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_parse_turbidez bebedouros.tests.test_lancamento_get -v 2`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: entry grid display with locked rows for inactive fountains"
```

---

### Task 7: The entry grid — save as draft (POST) + non-blocking warnings

**Files:**
- Create: `bebedouros/validation.py`
- Modify: `bebedouros/views.py` (add POST branch to `lancamento`)
- Test: `bebedouros/tests/test_validation.py`, `bebedouros/tests/test_lancamento_post.py`

**Interfaces:**
- Consumes: `_linhas` (Task 6), `parse_turbidez` (Task 6), `Resultado` (Task 5).
- Produces:
  - `bebedouros.validation.avisos_para_resultado(dados: dict) -> list[str]`. `dados` has keys `cloro`, `condutividade`, `nitrato`, `turbidez_valor`, `ph` mapping to `Decimal | None`. Returns messages for: `ph` outside `0`–`14`; any of the other four negative. Never raises.
  - `lancamento` POST: for each non-blocked row, `update_or_create` a `Resultado` keyed on `(coleta, bebedouro)`. Blank inputs stay `None`/`""`. `turbidez` text is parsed; on `ValueError` the value is left blank and a warning is added. All warnings are emitted via `messages.warning`, one per line, prefixed with the fountain code. On success `messages.success` ("Resultados salvos como rascunho." when `coleta.status == RASCUNHO`), then redirect to `lancamento` for the same pk. The collection's `status` is not changed here.

- [ ] **Step 1: Write the failing tests**

`bebedouros/tests/test_validation.py`:
```python
from decimal import Decimal

from django.test import SimpleTestCase

from bebedouros.validation import avisos_para_resultado


class AvisosTests(SimpleTestCase):
    def test_ph_out_of_range_warns(self):
        avisos = avisos_para_resultado({"ph": Decimal("20")})
        self.assertTrue(any("pH" in a for a in avisos))

    def test_negative_value_warns(self):
        avisos = avisos_para_resultado({"cloro": Decimal("-1")})
        self.assertTrue(any("negativo" in a for a in avisos))

    def test_normal_values_no_warnings(self):
        self.assertEqual(
            avisos_para_resultado({"ph": Decimal("7.2"), "cloro": Decimal("0.8")}),
            [],
        )
```

`bebedouros/tests/test_lancamento_post.py`:
```python
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class LancamentoPostTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)

    def _post(self, **campos):
        dados = {f"b{self.b1.id}-{k}": v for k, v in campos.items()}
        return self.client.post(f"/coletas/{self.coleta.pk}/lancamento/", dados, follow=True)

    def test_saves_values_and_keeps_draft(self):
        self._post(ph="7,20", coliformes_totais="AUSENTE")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("7.20"))
        self.assertEqual(r.coliformes_totais, "AUSENTE")
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)

    def test_blank_row_creates_empty_result(self):
        self._post()
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertTrue(r.esta_vazio())

    def test_turbidez_below_limit_is_parsed(self):
        self._post(turbidez="<0,751")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.turbidez_valor, Decimal("0.751"))
        self.assertTrue(r.turbidez_abaixo_limite)

    def test_strange_ph_saves_with_warning(self):
        response = self._post(ph="20")
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("20.00"))
        mensagens = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("pH" in m for m in mensagens))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_validation bebedouros.tests.test_lancamento_post -v 2`
Expected: FAIL — `validation` module missing; POST does not persist.

- [ ] **Step 3: Implement**

`bebedouros/validation.py`:
```python
from decimal import Decimal

_ZERO = Decimal("0")
_QUATORZE = Decimal("14")


def avisos_para_resultado(dados):
    avisos = []
    ph = dados.get("ph")
    if ph is not None and (ph < _ZERO or ph > _QUATORZE):
        avisos.append(f"pH {ph} está fora da faixa 0–14.")
    for chave, rotulo in [
        ("cloro", "Cloro"),
        ("condutividade", "Condutividade"),
        ("nitrato", "Nitrato"),
        ("turbidez_valor", "Turbidez"),
    ]:
        valor = dados.get(chave)
        if valor is not None and valor < _ZERO:
            avisos.append(f"{rotulo} {valor} é negativo.")
    return avisos
```

`bebedouros/views.py` — replace `lancamento` with GET+POST:
```python
from .validation import avisos_para_resultado


@login_required
def lancamento(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method == "POST":
        linhas = _linhas(coleta, request.POST)
        avisos = []
        for linha in linhas:
            if linha["bloqueada"]:
                continue
            bebedouro = linha["bebedouro"]
            form = linha["form"]
            form.is_valid()
            cd = form.cleaned_data
            try:
                turbidez_valor, turbidez_abaixo = parse_turbidez(cd.get("turbidez", ""))
            except ValueError as exc:
                turbidez_valor, turbidez_abaixo = None, False
                avisos.append(f"{bebedouro.codigo}: {exc}")
            numericos = {
                "cloro": cd.get("cloro"),
                "condutividade": cd.get("condutividade"),
                "nitrato": cd.get("nitrato"),
                "turbidez_valor": turbidez_valor,
                "ph": cd.get("ph"),
            }
            for msg in avisos_para_resultado(numericos):
                avisos.append(f"{bebedouro.codigo}: {msg}")
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
        for aviso in avisos:
            messages.warning(request, aviso)
        if coleta.status == Coleta.RASCUNHO:
            messages.success(request, "Resultados salvos como rascunho.")
        else:
            messages.success(request, "Resultados atualizados.")
        return redirect("lancamento", pk=coleta.pk)
    return render(
        request,
        "bebedouros/lancamento.html",
        {"coleta": coleta, "linhas": _linhas(coleta)},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_validation bebedouros.tests.test_lancamento_post -v 2`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: save grid as draft with non-blocking value warnings"
```

---

### Task 8: Publish a collection (missing-fountain warning + confirm)

**Files:**
- Create: `bebedouros/services.py`
- Modify: `bebedouros/views.py` (replace `publicar` stub)
- Create: `bebedouros/templates/bebedouros/publicar_confirma.html`
- Test: `bebedouros/tests/test_services.py`, `bebedouros/tests/test_publicar.py`

**Interfaces:**
- Consumes: `Coleta`, `Bebedouro`, `Resultado`, `Resultado.esta_vazio()`.
- Produces:
  - `bebedouros.services.linhas_faltantes(coleta) -> list[str]`: codes of `ativo` fountains that have no `Resultado` in this collection, or whose `Resultado.esta_vazio()` is `True` and `fora_de_operacao` is `False`. Ordered by fountain `numero`.
  - `bebedouros.services.publicar_coleta(coleta) -> None`: sets `status = Coleta.PUBLICADO` and saves.
  - `publicar(request, pk)`: non-`POST` redirects to `lancamento`. `POST`: if `linhas_faltantes` is non-empty and `request.POST.get("confirmar") != "1"`, render `publicar_confirma.html` with `{"coleta", "faltantes"}` and a `messages.warning` listing the codes; the confirm page re-POSTs with `confirmar=1`. Otherwise call `publicar_coleta`, `messages.success`, redirect to `coleta_list`.

- [ ] **Step 1: Write the failing tests**

`bebedouros/tests/test_services.py`:
```python
import datetime

from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado
from bebedouros.services import linhas_faltantes


class LinhasFaltantesTests(TestCase):
    def setUp(self):
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)
        self.b3 = Bebedouro.objects.create(numero=3, ativo=False)

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
```

`bebedouros/tests/test_publicar.py`:
```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class PublicarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.b1 = Bebedouro.objects.create(numero=1)
        self.b2 = Bebedouro.objects.create(numero=2)

    def test_publish_blocked_and_lists_missing(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        response = self.client.post(f"/coletas/{self.coleta.pk}/publicar/", follow=True)
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.RASCUNHO)
        self.assertContains(response, "B2")

    def test_publish_with_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        response = self.client.post(
            f"/coletas/{self.coleta.pk}/publicar/", {"confirmar": "1"}, follow=True
        )
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
        self.assertRedirects(response, "/")

    def test_publish_complete_without_confirmation(self):
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph="7.2")
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b2, ph="7.0")
        self.client.post(f"/coletas/{self.coleta.pk}/publicar/")
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test bebedouros.tests.test_services bebedouros.tests.test_publicar -v 2`
Expected: FAIL — `services` module missing; `publicar` returns "stub".

- [ ] **Step 3: Implement**

`bebedouros/services.py`:
```python
from .models import Bebedouro, Coleta


def linhas_faltantes(coleta):
    resultados = {r.bebedouro_id: r for r in coleta.resultados.all()}
    faltantes = []
    for bebedouro in Bebedouro.objects.filter(ativo=True):
        resultado = resultados.get(bebedouro.id)
        if resultado is None:
            faltantes.append(bebedouro.codigo)
        elif resultado.esta_vazio() and not resultado.fora_de_operacao:
            faltantes.append(bebedouro.codigo)
    return faltantes


def publicar_coleta(coleta):
    coleta.status = Coleta.PUBLICADO
    coleta.save(update_fields=["status", "atualizada_em"])
```

`bebedouros/views.py` — replace `publicar`:
```python
from .services import linhas_faltantes, publicar_coleta


@login_required
def publicar(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method != "POST":
        return redirect("lancamento", pk=pk)
    faltantes = linhas_faltantes(coleta)
    if faltantes and request.POST.get("confirmar") != "1":
        messages.warning(
            request, "Faltam resultados de: " + ", ".join(faltantes) + "."
        )
        return render(
            request,
            "bebedouros/publicar_confirma.html",
            {"coleta": coleta, "faltantes": faltantes},
        )
    publicar_coleta(coleta)
    messages.success(request, f"{coleta} publicada.")
    return redirect("coleta_list")
```

`bebedouros/templates/bebedouros/publicar_confirma.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Publicar coleta de {{ coleta.data|date:"d/m/Y" }}?</h1>
  <p>Faltam resultados destes bebedouros:</p>
  <ul>
    {% for codigo in faltantes %}<li>{{ codigo }}</li>{% endfor %}
  </ul>
  <form method="post" action="{% url 'publicar' coleta.pk %}">
    {% csrf_token %}
    <input type="hidden" name="confirmar" value="1">
    <button type="submit">Publicar mesmo assim</button>
    <a href="{% url 'lancamento' coleta.pk %}">Voltar</a>
  </form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_services bebedouros.tests.test_publicar -v 2`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: publish collection with missing-fountain confirmation"
```

---

### Task 9: Correct values on an already-published collection

**Files:**
- Test only: `bebedouros/tests/test_editar_publicada.py`
- Modify `bebedouros/views.py` only if a guard is found that blocks POST on published collections (there should be none — this task confirms and locks the behavior with a test).

**Interfaces:**
- Consumes: `lancamento` POST (Task 7).
- Produces: guaranteed behavior — editing a `publicado` collection persists new values, leaves `status == PUBLICADO`, and stores no previous value (there is no history model).

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_editar_publicada.py`:
```python
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class EditarPublicadaTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.coleta = Coleta.objects.create(
            data=datetime.date(2026, 9, 1), status=Coleta.PUBLICADO
        )
        self.b1 = Bebedouro.objects.create(numero=1)
        Resultado.objects.create(coleta=self.coleta, bebedouro=self.b1, ph=Decimal("7.20"))

    def test_correcting_published_value_persists_and_keeps_status(self):
        self.client.post(
            f"/coletas/{self.coleta.pk}/lancamento/",
            {f"b{self.b1.id}-ph": "6,90"},
            follow=True,
        )
        r = Resultado.objects.get(coleta=self.coleta, bebedouro=self.b1)
        self.assertEqual(r.ph, Decimal("6.90"))
        self.coleta.refresh_from_db()
        self.assertEqual(self.coleta.status, Coleta.PUBLICADO)
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `python manage.py test bebedouros.tests.test_editar_publicada -v 2`
Expected: PASS if Task 7 has no status guard (the common case) — then this task is a regression lock, proceed to commit. If it FAILS because a guard blocks the POST, do Step 3.

- [ ] **Step 3: Remove the guard (only if Step 2 failed)**

In `bebedouros/views.py` `lancamento`, delete any branch that returns early / refuses the POST when `coleta.status == Coleta.PUBLICADO`. The POST body must run identically for both statuses; only the success message differs (already handled in Task 7).

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test bebedouros.tests.test_editar_publicada -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: lock in editing of published collections"
```

---

### Task 10: Delete a whole collection

**Files:**
- Modify: `bebedouros/views.py` (replace `apagar` stub)
- Create: `bebedouros/templates/bebedouros/apagar_confirma.html`
- Test: `bebedouros/tests/test_apagar.py`

**Interfaces:**
- Consumes: `Coleta`, cascade delete of `Resultado` (Task 5).
- Produces: `apagar(request, pk)` — `GET` renders `apagar_confirma.html` with `{"coleta": coleta}`; `POST` deletes the `Coleta` (its `Resultado` rows cascade), adds `messages.success`, redirects to `coleta_list`. Allowed for `rascunho` and `publicado`.

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_apagar.py`:
```python
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from bebedouros.models import Bebedouro, Coleta, Resultado


class ApagarTests(TestCase):
    def setUp(self):
        User.objects.create_user("nucleo", password="segredo")
        self.client.login(username="nucleo", password="segredo")
        self.b1 = Bebedouro.objects.create(numero=1)
        self.alvo = Coleta.objects.create(data=datetime.date(2026, 9, 1))
        self.outra = Coleta.objects.create(data=datetime.date(2026, 8, 1))
        Resultado.objects.create(coleta=self.alvo, bebedouro=self.b1, ph="7.2")

    def test_get_shows_confirmation(self):
        response = self.client.get(f"/coletas/{self.alvo.pk}/apagar/")
        self.assertContains(response, "todos os bebedouros")

    def test_post_deletes_collection_and_its_results_only(self):
        response = self.client.post(f"/coletas/{self.alvo.pk}/apagar/", follow=True)
        self.assertRedirects(response, "/")
        self.assertFalse(Coleta.objects.filter(pk=self.alvo.pk).exists())
        self.assertEqual(Resultado.objects.count(), 0)
        self.assertTrue(Coleta.objects.filter(pk=self.outra.pk).exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test bebedouros.tests.test_apagar -v 2`
Expected: FAIL — stub returns "stub".

- [ ] **Step 3: Implement**

`bebedouros/views.py` — replace `apagar`:
```python
@login_required
def apagar(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method == "POST":
        coleta.delete()
        messages.success(request, "Coleta apagada.")
        return redirect("coleta_list")
    return render(request, "bebedouros/apagar_confirma.html", {"coleta": coleta})
```

`bebedouros/templates/bebedouros/apagar_confirma.html`:
```html
{% extends "bebedouros/base.html" %}
{% block conteudo %}
  <h1>Apagar a coleta de {{ coleta.data|date:"d/m/Y" }}?</h1>
  <p>Isso remove os resultados de todos os bebedouros dessa data. Não dá para desfazer.</p>
  <form method="post">
    {% csrf_token %}
    <button type="submit">Apagar</button>
    <a href="{% url 'coleta_list' %}">Cancelar</a>
  </form>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test bebedouros.tests.test_apagar -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Full test run + commit**

```bash
python manage.py test
git add -A
git commit -m "feat: delete a whole collection with confirmation"
```

---

### Task 11: Production-portable configuration

**Files:**
- Create: `requirements.txt`, `Procfile`, `.python-version`, `README-DEPLOY.md`
- Modify: `sistema_agua/settings.py` (env-driven database + whitenoise static)
- Test: `bebedouros/tests/test_config.py`

**Interfaces:**
- Consumes: settings from Task 1.
- Produces:
  - `settings.DATABASES["default"]` comes from `dj_database_url.config(default="sqlite:///" + str(BASE_DIR / "db.sqlite3"), conn_max_age=600)`; a `DATABASE_URL` env var of the form `postgres://...` yields a PostgreSQL engine.
  - `whitenoise.middleware.WhiteNoiseMiddleware` immediately after `SecurityMiddleware`; `STORAGES["staticfiles"]` set to WhiteNoise's compressed manifest storage.
  - `requirements.txt` pins `Django`, `gunicorn`, `dj-database-url`, `whitenoise`, `psycopg[binary]`.
  - `Procfile`: `web: gunicorn sistema_agua.wsgi` (plus a `release: python manage.py migrate` line).
  - `README-DEPLOY.md` documenting the four env vars (`SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `DATABASE_URL`), `python manage.py migrate`, `python manage.py collectstatic --noinput`, `python manage.py createsuperuser` for the single shared account, `python manage.py seed_bebedouros`, and that switching hosting providers means changing only those env vars.

- [ ] **Step 1: Write the failing test**

`bebedouros/tests/test_config.py`:
```python
from django.test import SimpleTestCase

import dj_database_url


class ConfigTests(SimpleTestCase):
    def test_database_url_parses_to_postgres(self):
        cfg = dj_database_url.parse("postgres://u:p@host:5432/dbname")
        self.assertIn("postgresql", cfg["ENGINE"])

    def test_whitenoise_is_installed(self):
        from django.conf import settings

        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE
        )
```

- [ ] **Step 2: Install deps and run test to verify it fails**

Run:
```bash
pip install gunicorn dj-database-url whitenoise "psycopg[binary]"
python manage.py test bebedouros.tests.test_config -v 2
```
Expected: FAIL — `test_whitenoise_is_installed` fails (middleware not added yet). `test_database_url_parses_to_postgres` may already pass once `dj-database-url` is installed.

- [ ] **Step 3: Implement**

In `sistema_agua/settings.py`:
```python
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
    )
}
```
Add WhiteNoise to `MIDDLEWARE` right after `django.middleware.security.SecurityMiddleware`:
```python
    "whitenoise.middleware.WhiteNoiseMiddleware",
```
Add:
```python
STORAGES = {
    "default": {"backend": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "backend": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
```

`requirements.txt` (pin to the versions installed — example values):
```
Django>=5.1,<6.0
gunicorn>=22,<24
dj-database-url>=2.2,<3
whitenoise>=6.7,<7
psycopg[binary]>=3.2,<4
```

`Procfile`:
```
release: python manage.py migrate
web: gunicorn sistema_agua.wsgi
```

`.python-version`:
```
3.12
```

`README-DEPLOY.md`:
```markdown
# Como colocar no ar

Este sistema roda em qualquer serviço que execute um app Python/Django.
Trocar de fornecedor mexe só nas variáveis de ambiente abaixo — nada no código.

## Variáveis de ambiente
- `SECRET_KEY` — uma frase longa e aleatória.
- `DEBUG` — `0` em produção.
- `ALLOWED_HOSTS` — o domínio do site, separado por vírgula.
- `DATABASE_URL` — endereço do banco PostgreSQL (o serviço fornece).
  Sem essa variável, o sistema usa um arquivo SQLite local (só para testes).

## Passos
1. `pip install -r requirements.txt`
2. `python manage.py migrate`
3. `python manage.py collectstatic --noinput`
4. `python manage.py createsuperuser` — cria a conta única do núcleo.
5. `python manage.py seed_bebedouros` — cria B1..B15 (edite os locais depois no /admin).

## Backup
O serviço de banco deve ter cópia de segurança automática ligada.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test bebedouros.tests.test_config -v 2 && python manage.py check --deploy`
Expected: config tests PASS; `check --deploy` prints security warnings (expected with `DEBUG=1` locally) but exits without error.

- [ ] **Step 5: Full suite + commit**

```bash
python manage.py test
git add -A
git commit -m "chore: portable production configuration (env-driven DB, whitenoise, deploy docs)"
```

---

## Self-Review

**1. Spec coverage** (against `DESENHO-ENTRADA-E-RESULTADOS.md`):

| Spec section | Task |
|---|---|
| 3.1 Ficha do bebedouro (código, local, ativo) | Task 2 |
| 3.2 Coleta (data única, rascunho/publicado) | Task 3 |
| 3.3 Resultados por bebedouro (5 números, 2 AUSENTE/PRESENTE, filtro, branco permitido) | Task 5, 6, 7 |
| 3.3 Turbidez "<0,751" | Task 6 (`parse_turbidez`), Task 7 (persist) |
| 3.5 Não guarda data da etiqueta / histórico / autor | Tasks 5 & 9 (no such fields/models) |
| 4 Tela de cadastro (criar, editar local, ativar/desativar) | Task 2 (Django admin) |
| 5 Grade: nova coleta + data + aviso de duplicada | Task 4 |
| 5 Grade: linhas ativas editáveis, desativadas travadas "fora de operação" | Task 6 |
| 5 Aviso leve de valor estranho, sem travar | Task 7 (`avisos_para_resultado`) |
| 5 Salvar rascunho com brancos | Task 7 |
| 6 Lista de coletas por data com etiqueta | Task 3 |
| 6 Abrir e corrigir valor (inclusive publicada), sem guardar valor antigo | Task 7, Task 9 |
| 6 Publicar com aviso de faltantes + confirmação, sem bloquear | Task 8 |
| 6 Apagar coleta inteira (rascunho ou publicada) com confirmação | Task 10 |
| 7 "Fora de operação nesta data" por linha vs. desativar no cadastro | Task 6/7 (`fora_de_operacao` field), Task 8 (excluded from faltantes), Task 2 (`ativo`) |
| 9.1 Site na internet | Task 1 (Django web app) |
| 9.2 Banco de verdade + backup | Task 11 (PostgreSQL via `DATABASE_URL`), backup = provider setting, documented |
| 9.3 Ferramentas Python com admin pronto | Task 1 + Task 2 |
| 9.4 Hospedagem portátil, sem lock-in | Task 11 (env-driven, `README-DEPLOY.md`) |
| 9.5 Login único usuário+senha em todas as telas internas | Task 1 (`@login_required` + admin login), Global Constraints |
| 10 Pendências (lista real B1–B15, unidade condutividade, provider) | Out of scope by design; `seed_bebedouros` leaves `local` blank for later fill |

No gaps found.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code and test step has literal content. `requirements.txt` version ranges are marked "example values" with instruction to pin to what was installed — acceptable (exact latest patch versions are environment-dependent).

**3. Type consistency:**
- `Coleta.RASCUNHO` / `Coleta.PUBLICADO` / `Coleta.STATUS_CHOICES` — defined Task 3, used Tasks 7, 8, 9.
- `Resultado.MICRO_CHOICES` / `FILTRO_CHOICES` — defined Task 5, used Task 6 form.
- `Resultado.esta_vazio()` — defined Task 5, used Task 8 `linhas_faltantes`.
- `parse_turbidez` returns `(Decimal|None, bool)` — Task 6, consumed Task 7.
- `avisos_para_resultado(dados: dict)` keys `cloro/condutividade/nitrato/turbidez_valor/ph` — Task 7 builds exactly those keys before calling it.
- `linhas_faltantes` / `publicar_coleta` — Task 8, used same task's view.
- `_linhas(coleta, dados_post=None)` row dict keys `bebedouro/bloqueada/resultado/form` — Task 6, consumed Task 7 POST loop and both templates.
- URL names `coleta_list`, `coleta_nova`, `lancamento`, `publicar`, `apagar` — all registered in Task 3's `urls.py`, referenced consistently.

No inconsistencies found.

---

## Execution Handoff

Choose an execution approach when starting implementation:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks. REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.
2. **Inline Execution** — tasks run in one session with checkpoints. REQUIRED SUB-SKILL: `superpowers:executing-plans`.
