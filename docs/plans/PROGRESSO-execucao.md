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
- [ ] Task 9 — editar coleta publicada
- [ ] Task 10 — apagar coleta
- [ ] Task 11 — config de produção portátil

## Notas
- Python 3.14.7, Django 5.2.17, venv em `.venv/`.
- Rodar testes: `./.venv/Scripts/python.exe manage.py test`
