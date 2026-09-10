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

# Progresso da execução — plano 2026-09-09-ajustes-pagina-do-bebedouro-orientadora

Executado por subagentes (subagent-driven-development), com revisão de código a cada
tarefa. 12 tarefas ao todo (11 de implementação + esta, de checagem final).

**Objetivo do plano:** reorganizar a página do bebedouro em torno das 5 coletas mais
recentes + média, acrescentar o rastreio de troca de filtro (modelo `TrocaFiltro`,
indicador público de validade dentro/vencido) e corrigir os cards de "Composição da
nota" para aparecerem também para visitante anônimo (antes só apareciam pra quem
estava logado).

- [x] Task 1 — modelo `TrocaFiltro` (commit 4b0a103)
- [x] Task 2 — `formatar_turbidez` extraído para reuso (commit 3032d60)
- [x] Task 3 — `iqab.media()` para a média das notas (commit 98a7df1)
- [x] Task 4 — `coletas_recentes()` substitui `historico_bebedouro()` (commit 194c237)
- [x] Task 5 — `media_coletas()` para o bloco de média da página (commits 194c237..d62f862,
      1 rodada de correção — ver ruling abaixo)
- [x] Task 6 — `situacao_filtro()` e gravação da troca de filtro (commit 42827ad,
      mais correção de teste em d86afc1)
- [x] Task 7 — campo `troca_filtro` na grade de lançamento (commit faa4501; 1 trecho
      fora de escopo revertido pelo controlador — ver ruling abaixo)
- [x] Task 8 — grade de lançamento grava e mostra a troca de filtro (commit 6eaeca0)
- [x] Task 9 — `bebedouro_detalhe` passa a usar `coletas_recentes`/`media_coletas`/
      `situacao_filtro` (commit 5f45b0c; estado intencionalmente vermelho até a Task 10/11)
- [x] Task 10 — reorganiza o HTML da página do bebedouro (filtro, coletas recentes,
      média) (commit e882543)
- [x] Task 11 — reescreve os testes da página para a nova estrutura (commit 875f7b1;
      212/212 testes verdes — reorganização funcionalmente completa)
- [x] Task 12 — checagem final: `manage.py check`, migrações, suíte completa, teste
      ponta a ponta (esta tarefa)

## Situação: TODAS AS 12 TAREFAS CONCLUÍDAS (2026-09-09)
- 212 testes passando (`manage.py test bebedouros`), partindo de uma base de 171 no
  início deste plano.
- `manage.py check` limpo: "System check identified no issues (0 silenced)".
- Migrações em dia (`makemigrations --check --dry-run` sem saída, exit 0).
- Teste ponta a ponta via Django test client confere: bolsista loga, cria coleta,
  preenche a grade (incluindo "Troca de filtro realizada em"), publica; visitante
  anônimo vê "Composição da nota", o ✅ de filtro dentro da validade, a data da coleta
  e o bloco de média das coletas recentes.
- Commits do plano: eac59be (doc do plano) → 875f7b1 (fim da Task 11), mais o commit
  desta Task 12.

## Rulings feitas durante a execução
1. Task 5 — as médias em `media_coletas()` precisam de `Decimal.quantize()` por campo
   (3 casas para cloro/condutividade/nitrato/turbidez, 2 para ph) antes de formatar,
   senão uma divisão sem arredondar podia virar um número com 20+ dígitos. A correção
   do próprio implementador (remover zeros à direita) foi rejeitada por deixar a média
   visualmente diferente da tabela de coleta única, que já mostra zeros à direita.
   Custo se errado: baixo, confinado a uma função interna.
2. Task 6/7 — o widget de data do Django, com `LANGUAGE_CODE='pt-br'`, mostrava o valor
   inicial em formato brasileiro ("01/09/2026"), que o `<input type="date">` ignora
   silenciosamente. Sem correção, uma troca de filtro já lançada apareceria em branco
   ao reabrir a grade — bug real de usabilidade. Corrigido com `format="%Y-%m-%d"` no
   widget, com teste específico documentando o porquê.
3. Task 7 — o revisor encontrou um trecho fora de escopo (renomeação solta de
   `historico_bebedouro` para `coletas_recentes` dentro de `views.py`) que quebrava 3
   testes ao misturar dados novos com o template antigo. Revertido pelo controlador
   (só esse trecho, sem tocar no restante do commit) — a Task 9 continuou sendo a única
   dona da reescrita de `views.py`, como o plano previa.
4. Task 10/11 — o texto da média usava concordância errada em português quando só
   havia 1 coleta ("últimas 1 coletas"). Trocado por "Média das coletas recentes (N)",
   que não depende de concordância de número.
5. Task 10/11 — o atributo `open` do `<details>` foi movido para antes de `class="..."`
   no template, porque o teste esperava a substring exata `"<details open"` (que não
   batia com `class` no meio).
6. Task 10/12 — as duas checagens manuais "abrir o navegador e olhar a página" foram
   substituídas por scripts via Django test client (`manage.py shell`), já que
   subagentes não têm navegador.

## Pendências / itens observados, não corrigidos (fora de escopo deste plano)
- Um flake pré-existente e não relacionado a este plano foi observado uma única vez em
  `bebedouros.tests.test_inicio.InicioTests.test_alerta_filtro_vencido_aparece`
  (Task 11), nunca reproduzido de novo (4 reruns isolados limpos, e limpo em toda
  execução do comando de teste obrigatório desde então, incluindo o desta Task 12).
  Registrado para referência futura; não é defeito deste plano.
- O script de teste ponta a ponta da Task 12 assume um bebedouro sem histórico prévio
  (espera "Média das coletas recentes (1)"). O banco de desenvolvimento real
  (`db.sqlite3`, não isolado) já acumula coletas de testes manuais de tarefas
  anteriores do plano, então o bebedouro nº 1 tinha 4 coletas com nota calculada antes
  mesmo da nova. O bloco de média apareceu corretamente com a contagem real
  ("Média das coletas recentes (4)") — os outros 4 marcadores esperados bateram
  exatamente. Não é um defeito: é só o número da contagem, que depende do estado do
  banco local, não do código. Nenhuma correção de código foi necessária. Quando os
  dados reais de 2024/2025 forem digitados, essa checagem deve ser refeita contra uma
  cópia do banco, como o próprio texto da tarefa já recomendava.
