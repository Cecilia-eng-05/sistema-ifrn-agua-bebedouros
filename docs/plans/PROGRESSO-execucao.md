# Progresso da execução — plano 2026-09-02-entrada-armazenamento-resultados

Executado inline (sem subagentes) nesta sessão. TDD por tarefa.

- [x] Task 1 — esqueleto Django, login gate, base template (commit baf737d)
- [x] Task 2 — Bebedouro model + admin + seed (commit 190d4c8)
- [x] Task 3 — Coleta model + lista (commit 2b17569)
- [x] Task 4 — criar coleta (data + aviso duplicada) (commit pendente)
  - Ruling: ColetaForm virou forms.Form simples (não ModelForm). Motivo: o ModelForm
    validava a unicidade da data antes e nunca chegava na mensagem amigável de duplicada
    que a própria tarefa pede. Custo se errado: baixo — só a forma de montar o formulário
    de data muda; comportamento e testes iguais ao plano.
- [x] Task 5 — Resultado model + esta_vazio
- [x] Task 6 — grade (GET) + forms + parse_turbidez
- [x] Task 7 — grade (POST) salvar rascunho + avisos
- [x] Task 8 — publicar + linhas_faltantes
- [x] Task 9 — editar coleta publicada
- [x] Task 10 — apagar coleta
- [x] Task 11 — config de produção portátil

## Situação: TODAS AS 11 TAREFAS CONCLUÍDAS (2026-09-02)
- 39 testes passando. `manage.py check` limpo. Migrações em dia.
- Teste ponta a ponta manual OK: login, lista, criar coleta, grade com 15 bebedouros,
  botões salvar/publicar, cadastro no /admin.
- 12 commits no branch `master`.

## Rulings feitas durante a execução
1. Task 4 — ColetaForm virou `forms.Form` simples (não ModelForm). O ModelForm validava a
   unicidade da data antes e nunca chegava na mensagem amigável de duplicada. Custo se
   errado: baixo.
2. Task 6 — teste `test_lancamento_get` passou a checar o texto real da linha travada
   ("Fora de operação (bebedouro desativado)") em vez de "fora de operação" minúsculo,
   que não aparecia com essa grafia. Custo se errado: nenhum — mesmo comportamento.
3. Task 11 — além do plano, adicionei um bloco de endurecimento de segurança só para
   produção (cookies seguros, HSTS, proxy SSL header, CSRF_TRUSTED_ORIGINS). Custo se
   errado: baixo — só afeta quando DEBUG=0.
4. Fora do plano — corrigido `STORAGES` para usar chave `BACKEND` maiúscula (o plano
   trazia `backend` minúsculo, que quebrava o `collectstatic`).

## Notas
- Python 3.14.7, Django 5.2.17, venv em `.venv/`.
- Rodar testes: `./.venv/Scripts/python.exe manage.py test`
- Rodar local: `./.venv/Scripts/python.exe manage.py migrate` + `seed_bebedouros` +
  `createsuperuser` + `runserver`.
