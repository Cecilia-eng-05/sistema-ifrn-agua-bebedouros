# Como colocar no ar

Este sistema roda em qualquer serviço que execute um app Python/Django.
Trocar de fornecedor mexe só nas variáveis de ambiente abaixo — nada no código.

## Variáveis de ambiente
- `SECRET_KEY` — uma frase longa e aleatória.
- `DEBUG` — `0` em produção.
- `ALLOWED_HOSTS` — o domínio do site, separado por vírgula.
- `DATABASE_URL` — endereço do banco PostgreSQL (o serviço fornece).
  Sem essa variável, o sistema usa um arquivo SQLite local — é o que
  usamos no PythonAnywhere (ver abaixo), por não exigir banco separado.

## Hospedagem escolhida: PythonAnywhere (plano gratuito)

Guia rápido — o painel do PythonAnywhere muda com o tempo, então os nomes
exatos dos botões podem variar um pouco.

1. **Colocar o código no GitHub** (o PythonAnywhere busca o código de lá).
2. Criar a conta gratuita em pythonanywhere.com.
3. Abrir um **Bash console** no PythonAnywhere e rodar:
   ```
   git clone <endereço do repositório no GitHub>
   cd Sistema_IFRN_Agua
   python3.10 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Na aba **Web**, criar um novo web app → "Manual configuration" → Django →
   apontando para essa pasta e esse virtualenv.
5. Abrir o arquivo WSGI que o PythonAnywhere gera (link na própria aba Web)
   e, ANTES da linha que importa `sistema_agua.wsgi`, definir as variáveis
   de ambiente de produção:
   ```python
   import os
   os.environ["SECRET_KEY"] = "<gerar uma nova — não usar a de desenvolvimento>"
   os.environ["DEBUG"] = "0"
   os.environ["ALLOWED_HOSTS"] = "<seu-usuario>.pythonanywhere.com"
   ```
6. Na mesma aba Web, em **"Static files"**, mapear:
   - URL `/static/` → pasta `.../staticfiles`
   - URL `/media/` → pasta `.../media`
   **Esse segundo mapeamento é obrigatório** — sem ele, as fotos dos
   bebedouros enviadas pelo admin não aparecem no site (em produção,
   com `DEBUG=0`, o Django para de servir a pasta `media/` sozinho).
7. De volta ao Bash console, com o virtualenv ativado:
   ```
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   python manage.py seed_bebedouros
   ```
8. Clicar em **"Reload"** na aba Web. O site fica em
   `https://<seu-usuario>.pythonanywhere.com`.

### Atualizando o site depois (nova versão do código)
No Bash console do PythonAnywhere:
```
cd Sistema_IFRN_Agua
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```
Depois clicar em "Reload" na aba Web de novo.

## Backup
Fazer backup do arquivo `db.sqlite3` de vez em quando (ele guarda todos os
dados de coleta) — pelo Bash console ou pela aba Files do PythonAnywhere.

## Rodar localmente para testar
1. `python -m venv .venv` e ative o ambiente.
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py createsuperuser`
5. `python manage.py seed_bebedouros`
6. `python manage.py runserver` e abra `http://127.0.0.1:8000/`.
