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
5. `python manage.py seed_bebedouros` — cria B1..B15 com os locais reais
   (edite depois no /admin, se algum local mudar).

## Backup
O serviço de banco deve ter cópia de segurança automática ligada.

## Rodar localmente para testar
1. `python -m venv .venv` e ative o ambiente.
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py createsuperuser`
5. `python manage.py seed_bebedouros`
6. `python manage.py runserver` e abra `http://127.0.0.1:8000/`.
