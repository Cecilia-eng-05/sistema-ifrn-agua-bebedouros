# Desenho — Reorganização da Página do Bebedouro e Manutenção do Filtro

> Data: 09/09/2026
> Documento em linguagem comum. Descreve os ajustes pedidos pela
> **orientadora** na página de cada bebedouro, mais um conserto de
> visibilidade encontrado durante a conversa.
> Continua valendo tudo que está no `DEFINICAO-DO-PROJETO.md`,
> no `DESENHO-ENTRADA-E-RESULTADOS.md` e no `DESENHO-PARTE-VISUAL.md`.
> Onde este documento discordar do `DESENHO-PARTE-VISUAL.md` quanto à
> ordem dos blocos da página do bebedouro, **vale este aqui**.

---

## 1. O que a orientadora pediu

1. Em vez de "coletas anteriores dos últimos 12 meses", mostrar **sempre
   as 5 coletas mais recentes** — a cada nova coleta entra a mais nova e
   sai a mais antiga.
2. Abaixo dessas 5, mostrar **a média dos resultados dessas 5 coletas**,
   já aberta, sem precisar clicar.
3. Registrar a **data de troca do filtro** ("troca realizada em tal
   dia") e mostrar na página do bebedouro essa data com um **✅ verde**
   quando está em dia, ou um **❌ vermelho** com a frase de que **há
   necessidade de troca** quando venceu.

## 2. O que foi descoberto durante a conversa

A caixa **"Composição da nota"** (Físico-química / Bactérias / Filtro,
com os pesos) hoje só aparece para quem está logado. Isso é um **erro**:
tudo que está nas páginas públicas — Mapa, página do bebedouro e Entenda
o IQA-B — deve ser visível para quem acessa pelo link, sem login.

Entra neste trabalho como conserto.

## 3. O que NÃO muda

- A fórmula do IQA-B e a versão da metodologia.
- **A coluna "Filtro: dentro da validade / vencido"** da grade de
  lançamento. Ela continua sendo digitada à mão e continua sendo a única
  coisa que alimenta o pedaço "Situação do filtro" (peso 20%) do IQA-B.
  A data de troca **não** altera nenhum cálculo de nota.
- O gráfico de evolução do IQA-B e os botões de período (3m / 6m / 12m).
- A aba Alertas, o mapa, a tela Início e o fluxo de rascunho/publicação.
- A regra de visibilidade: visitante vê só coletas **publicadas**;
  quem está logado vê também os rascunhos.

---

## 4. A nova organização da página do bebedouro

Ordem dos blocos, de cima para baixo:

```
┌─ 1. TOPO (como já é hoje) ─────────────────────┐
│  Foto · gota grande com a nota                 │
│  B7 — Bloco tal                                │
│  "Boa" · última análise em 05/09/2026          │
│  Composição da nota (QFQ / QM / Filtro)        │
│  ↑ agora visível também para o visitante       │
└────────────────────────────────────────────────┘

┌─ 2. MANUTENÇÃO DO FILTRO (novo) ───────────────┐
│  ✅ Filtro trocado em 10/03/2026 —             │
│     dentro da validade (válido até 10/09/2026) │
└────────────────────────────────────────────────┘

┌─ 3. COLETAS RECENTES (as 5 últimas) ───────────┐
│  ▸ 05/09/2026        ← clica e abre o detalhe  │
│  ▸ 22/08/2026                                  │
│  ▸ 08/08/2026                                  │
│  ▸ 25/07/2026                                  │
│  ▸ 11/07/2026                                  │
└────────────────────────────────────────────────┘

┌─ 4. MÉDIA DESSAS 5 COLETAS (novo) ─────────────┐
│  Sempre aberta, sem clique                     │
└────────────────────────────────────────────────┘

┌─ 5. EVOLUÇÃO (gráfico, como já é hoje) ────────┐
└────────────────────────────────────────────────┘
```

**Duas seções deixam de existir como estão hoje:**

- A tabela **"O que é monitorado"**, que hoje fica solta no meio da
  página mostrando os valores da coleta mais recente. Esses valores
  passam a aparecer dentro do primeiro item do bloco 3.
- A seção **"Coletas anteriores"** do fim da página. Ela vira o bloco 3,
  que sobe de posição e passa a incluir a coleta mais recente.

---

## 5. Bloco 3 — as 5 coletas mais recentes

- São as **5 coletas mais recentes deste bebedouro**, incluindo a que
  gerou a nota do topo. Da 6ª para trás, não aparece mais nada na
  página.
- Cada linha mostra a **data**. Clicando, abre o detalhe daquela coleta:
  a nota IQA-B do dia e a tabela dos 7 parâmetros (Cloro, Condutividade,
  Nitrato, Turbidez, pH, Coliformes Totais, E. coli) — exatamente o
  conteúdo que hoje aparece em "Coletas anteriores".
- **A mais recente começa aberta**; as outras 4 começam fechadas. O
  visitante pode fechar a mais recente e abrir qualquer outra, à
  vontade.
- Coletas em que o bebedouro estava **fora de operação** aparecem na
  lista, marcadas como tal, e ocupam uma das 5 vagas.
- Se o bebedouro tiver **menos de 5 coletas**, mostra as que existirem.
- Se não tiver nenhuma, o bloco mostra a frase de lista vazia.

---

## 6. Bloco 4 — a média das 5 coletas

A média é sempre das **mesmas 5 coletas listadas no bloco 3** — se o
bloco 3 mostra 3 coletas, a média é dessas 3, e o título diz isso.

### 6.1 Como cada linha é calculada

| Linha | Como calcula |
|---|---|
| Cloro Residual Livre | Média simples das coletas que têm valor |
| Condutividade Elétrica | Média simples das coletas que têm valor |
| Nitrato | Média simples das coletas que têm valor |
| pH | Média simples das coletas que têm valor |
| Turbidez | Ver 6.2 |
| Coliformes Totais | Contagem — ver 6.3 |
| E. coli | Contagem — ver 6.3 |
| **Média do IQA-B** | Média das notas calculadas, com a classificação correspondente |

### 6.2 Turbidez

O laboratório às vezes entrega `<0,751` em vez de um número. Nesses
casos a conta usa o próprio **0,751**, e a média é apresentada com o
sinal de menor — por exemplo **`<0,68 UNT`** — deixando claro que é um
teto, não um valor exato. Se nenhuma das 5 estiver abaixo do limite, a
média sai como número normal.

### 6.3 Coliformes Totais e E. coli

Não são número, são "Ausente / Presente". Aparecem como contagem:

- **"Ausente em 5 de 5 coletas"** quando está tudo limpo.
- **"Presente em 1 de 5 coletas"**, com destaque visual, quando houve
  alguma presença.

Coletas sem essa informação não entram na contagem, e o "de N" reflete
só as que tinham resposta.

### 6.4 Casos vazios

- Coletas com o bebedouro **fora de operação** ficam de fora da média.
- Um parâmetro sem valor em nenhuma das 5 coletas mostra **`—`**.
- A **média do IQA-B** usa só as coletas cuja nota foi calculada;
  "pendente" e "incompleto" ficam de fora. Se nenhuma tiver nota, a
  linha mostra `—`.

---

## 7. Bloco 2 — manutenção do filtro

### 7.1 A regra

- A validade do filtro é de **6 meses**, igual para os 15 bebedouros.
- O sistema pega a **troca mais recente registrada** daquele bebedouro,
  soma 6 meses e compara com **a data de hoje**.

### 7.2 O que o visitante vê

**Em dia:**

```
Manutenção do filtro
✅  Filtro trocado em 10/03/2026 — dentro da validade
    (válido até 10/09/2026)
```

**Vencido:**

```
Manutenção do filtro
❌  Filtro trocado em 02/01/2026 — venceu em 02/07/2026
    Há necessidade de troca.
```

**Sem registro** (caso de todas as coletas de 2024/2025):

```
Manutenção do filtro
—   Sem registro de troca de filtro.
```

Este bloco **substitui** o aviso avulso "Filtro fora da validade na
última coleta" que hoje aparece logo abaixo do topo da página.

### 7.3 Onde a data é digitada

Na **grade de lançamento**, ao lado da coluna "Filtro" que já existe,
entra uma coluna nova: **"Troca realizada em"**.

| Bebedouro | Filtro | Troca realizada em |
|---|---|---|
| B7 | Dentro da validade ▾ | *(em branco)* |
| B8 | Dentro da validade ▾ | 10/03/2026 |

- **Em branco é o normal.** Significa "nada mudou desde a última
  coleta"; continua valendo a última troca já registrada.
- O bolsista só preenche **quando trocou o filtro** naquela quinzena.
  Como as coletas são quinzenais e o filtro dura 6 meses, o campo fica
  vazio na maioria das vezes — de propósito, para não obrigar a repetir
  a mesma data 12 vezes seguidas.

### 7.4 Como a troca fica guardada

Cada data preenchida vira **uma linha num histórico de trocas**:
qual bebedouro, em que dia o filtro foi trocado, e em qual coleta essa
informação foi lançada. O sistema passa a saber o histórico de
manutenção de cada bebedouro, não só a última troca.

Regras:

- A mesma troca lançada duas vezes (mesmo bebedouro, mesma data) **não
  duplica**.
- Apagar a data na grade **remove** aquela linha do histórico.
- A troca só fica **visível ao visitante depois que a coleta em que ela
  foi lançada for publicada** — mesma regra do resto do sistema.
  Enquanto a coleta estiver em rascunho, só quem está logado vê.
- Os dados de 2024/2025 serão digitados **sem** data de troca (essa
  informação não foi registrada na época) e **com** a coluna Filtro
  preenchida como "dentro da validade" para todos os bebedouros. Para
  aquelas coletas, o bloco 2 mostrará "Sem registro de troca de filtro"
  — o que é correto, porque não há o que mostrar.

---

## 8. O que muda no banco de dados

Uma coisa nova só: o **histórico de trocas de filtro** (bebedouro +
data da troca + coleta em que foi lançada).

Nenhum campo existente é apagado ou alterado. Os dados que já estão no
sistema continuam válidos como estão.

---

## 9. Como saber que ficou certo

- A página do bebedouro mostra no máximo 5 coletas, na ordem certa, e a
  6ª some quando entra uma nova.
- A média confere com a conta feita à mão para um bebedouro de teste,
  inclusive nos casos de valor em branco e de turbidez `<`.
- A caixa do filtro mostra ✅ antes dos 6 meses e ❌ depois, e mostra
  "sem registro" quando não há troca lançada.
- Preencher a data na grade cria a troca; apagar a data remove.
- Um visitante **sem login** vê: a composição da nota, as 5 coletas, a
  média e a caixa do filtro — tudo, só que apenas com coletas
  publicadas.

---

## 10. Pendências

- **Fotos dos bebedouros** — continua pendente, como no documento
  anterior.
- **Digitação dos dados de 2024/2025** — segue como próximo passo
  separado, depois da hospedagem.
