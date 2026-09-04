# Desenho da parte de Entrada, Armazenamento e Gerenciamento dos Resultados

> Data: 02/09/2026
> Documento em linguagem comum. Descreve **só** a parte do sistema que
> registra, guarda e administra os resultados das análises dos bebedouros.
> Continua valendo tudo que está no `DEFINICAO-DO-PROJETO.md`.
> Nenhuma decisão de linguagem de programação, ferramentas ou hospedagem
> foi tomada aqui — isso vem depois.

---

## 1. O que esta etapa cobre

Construir a base onde todos os dados das análises vão morar:

- o **cadastro dos 15 bebedouros**;
- o **lançamento de uma coleta** (a grade com os bebedouros, parecida com a
  planilha atual);
- **guardar** esses resultados;
- **gerenciar** o que já foi lançado: ver a lista, corrigir um valor,
  apagar uma coleta inteira, e marcar uma coleta como publicada.

Essa parte foi escolhida para andar primeiro porque **não depende das
decisões metodológicas pendentes** do TCC. Um resultado de laboratório
("o cloro deu 0,8"; "coliformes deu AUSENTE") é o mesmo dado
independentemente de como a nota do IQA-B for calculada mais tarde.

---

## 2. O que NÃO entra nesta etapa

Para não haver mal-entendido, fica de fora por enquanto:

- **Cálculo do IQA-B** e a classificação por faixa/cor — depende das
  decisões metodológicas pendentes (seção 8.2 da definição).
- **Parte pública** — mapa do campus e abas Mapa / Alertas / Parâmetros.
- **Alertas** — IQA-B ruim, filtro vencido, quinzena sem dados.
- **Importação das planilhas históricas** de 2023 em diante — será tratada
  num momento seguinte, como carga a partir das planilhas.

O **login** entra sim nesta etapa (ver seção 9, decisão 5).

---

## 3. O esqueleto dos dados — as três coisas que o sistema guarda

### 3.1 Ficha do bebedouro

- **Código:** "B" + número (B1 a B15).
- **Local:** texto (ex.: "próximo às mesas verdes").
- **Situação:** ativo / desativado.

São 15 fichas. A lista real com os locais será fornecida pela orientanda e
entra como cadastro inicial; isso não trava a construção.

### 3.2 A coleta

- **Data:** o dia em que a coleta foi feita. Uma coleta = uma data.
  Todos os bebedouros daquela rodada ficam presos a essa data.
- **Estado:** **rascunho** ou **publicado**.
- Cada coleta reúne os resultados dos bebedouros naquele dia.

### 3.3 Os resultados de um bebedouro dentro de uma coleta

Para cada bebedouro, dentro de uma coleta:

| Item | Como é preenchido |
|---|---|
| Cloro Residual Livre | número |
| Condutividade Elétrica | número — unidade **µS/cm** (microsiemens por centímetro) |
| Nitrato | número |
| Turbidez | número **ou** o texto "<0,751" (abaixo do limite de detecção) |
| pH | número |
| Coliformes Totais | AUSENTE ou PRESENTE |
| E. coli | AUSENTE ou PRESENTE |
| Situação do filtro | dentro da validade ou vencido |

Qualquer uma dessas casinhas pode ficar **em branco** (resultado ainda não
chegou, não foi coletado etc.).

### 3.4 Como se ligam

- Um mesmo **bebedouro** aparece em **várias coletas** ao longo do tempo.
- Uma **coleta** cobre os bebedouros daquela data.
- É essa ligação (bebedouro × datas) que vai alimentar os gráficos de
  evolução quando o cálculo do IQA-B for construído.

### 3.5 O que o sistema NÃO guarda (decisões já tomadas na definição)

- A **data da etiqueta do filtro** — só o estado "dentro da validade /
  vencido" informado na coleta.
- **Histórico de alteração** ("valor antigo → valor novo") quando algo é
  corrigido. A correção sobrescreve o valor.
- **Quem digitou** cada dado — a conta é do núcleo, não da pessoa.

---

## 4. Tela: cadastro dos bebedouros

Uma lista com os bebedouros. Nela é possível:

- **criar** um bebedouro (código e local);
- **editar** o local;
- **desativar a partir de uma data** / **reativar**.

**Desativar não apaga nada e não mexe no passado.** As coletas anteriores
à data de desativação continuam com os resultados que tinham. O bebedouro
só deixa de ser cobrado nas coletas **daquela data em diante**, até ser
reativado. Detalhes na seção 7 (caso B).

---

## 5. Tela: lançamento de uma coleta (a grade)

- Botão **"nova coleta"** → escolhe-se a **data**.
- Se já existir uma coleta naquela data, o sistema **avisa**, para não
  duplicar sem querer.
- Abre a **grade**:
  - uma **linha por bebedouro**;
  - **colunas** = os 7 parâmetros + a situação do filtro (seção 3.3);
  - bebedouros em operação na data da coleta: linha preenchível;
  - bebedouros **desativados até a data da coleta**: linha **travada**,
    marcada como "fora de operação" (coletas anteriores à desativação
    seguem preenchíveis — ver seção 7, caso B);
  - cada linha ativa tem também um marcador **"fora de operação nesta
    data"** (com espaço para uma observação curta) para o caso de o
    bebedouro estar quebrado / em manutenção só naquele dia — ver seção 7.
- **Turbidez** aceita número ou o texto "<0,751".
- **Coliformes Totais**, **E. coli** e **situação do filtro** são escolhas
  entre as opções fixas, não campo livre.
- **Aviso leve de valor estranho:** se um número foge muito do esperado
  (pH fora de 0–14; número negativo onde não faz sentido), aparece um
  aviso. **Não trava** o salvamento. Nada além disso — se essa checagem
  começar a complicar a construção, ela é cortada.
- **Salvar como rascunho** a qualquer momento, mesmo com casinhas em
  branco.

A lista de parâmetros é **fixa** (embutida no sistema). Se um dia o projeto
passar a medir algo novo, será preciso mexer no programa — assumido como
aceitável por ora, já que a medição está estável há anos.

---

## 6. Publicar e gerenciar coletas

- **Lista de todas as coletas**, por data, cada uma com a etiqueta
  **rascunho** ou **"Publicado em dd/mm/aaaa"** (a data fica registrada na
  hora de publicar; simples, sem histórico de "publicou/despublicou").
- **Abrir** qualquer coleta (rascunho ou já publicada) mostra a mesma
  grade, com os valores já lançados.
- **Corrigir** um valor: edita direto e salva; o valor antigo não é
  guardado. Vale inclusive para coletas já publicadas.
- **Publicar:** botão dentro da coleta. **Salva a grade primeiro** (o que
  estiver na tela naquele momento), do mesmo jeito que "Salvar rascunho" —
  assim uma edição feita e mandada direto pelo botão Publicar nunca é
  perdida em silêncio. Só depois de salvar é que checa: se faltarem
  bebedouros que deveriam ter resultado (ativos e sem o marcador "fora de
  operação nesta data"), o sistema mostra quais ("faltam B3 e B9 —
  publicar mesmo assim?") e pede confirmação. **Não bloqueia.**
  - Esse aviso é **por bebedouro inteiro**: só considera "faltando" quem
    ficou com **todos** os 7 campos em branco. Um bebedouro com só um
    parâmetro faltando continua contando como resultado (parcial é
    aceito, de propósito).
  - Publicar **não é uma foto congelada**: uma correção salva depois —
    mesmo sem apertar "Publicar" de novo — já é o que valeria para a
    parte pública, porque é o mesmo dado, só com a marca de visível
    ligada.
- **Apagar uma coleta inteira:** possível tanto para rascunho quanto para
  coleta já publicada, com uma confirmação avisando que isso remove os
  resultados de todos os bebedouros daquela data.

*Nesta etapa não existe "voltar de publicado para rascunho".*

### 6.1 Cálculo do IQA-B — quando acontece

**Decisão (02/09/2026):** o IQA-B é calculado **automaticamente toda vez que
a coleta é salva**, e mostrado numa coluna da própria grade, bebedouro por
bebedouro. Não há botão "calcular" separado (fácil de esquecer, e o número
ficaria desatualizado depois de uma correção). O botão **Publicar** tem um
papel só: tornar os resultados e os índices visíveis na parte pública — ele
não gera nada.

Assim você vê a classificação de cada bebedouro **enquanto ainda é
rascunho**, que é o momento de perceber um problema antes de publicar.

Estados que uma célula de IQA-B pode mostrar:

- **"—"** — linha vazia ou "fora de operação nesta data": nada a calcular.
- **"pendente"** — (fica reservado para coletas calculadas antes de existir
  fórmula, se algum dia isso ocorrer de novo) linha com dados mas sem
  fórmula.
- **"incompleto"** — falta algum parâmetro obrigatório da fórmula naquela
  linha (é o caso do histórico 2024/2025, que nunca teve a situação do
  filtro registrada).
- **número + classificação** com cor — índice calculado.

Cada IQA-B guardado registra **qual versão da metodologia** o gerou, para o
histórico não embaralhar quando a fórmula mudar.

**Fórmula definida e implementada em 04/09/2026 (versão "1.0"), com a
orientadora:**

```
IQA-B = 0,3 × QFQ + 0,5 × QM + 0,2 × CO
```

- **QFQ** (físico-química): média ponderada — Cloro 0,35, Turbidez 0,25,
  pH 0,20, Nitrato 0,20 — cada parâmetro pontuado 0 ou 100 (turbidez também
  admite 50, faixa intermediária) pelos limites da Portaria MS nº 888/2021.
  **Condutividade é só monitorada, não entra na conta.**
- **QM** (microbiológica): **E. coli PRESENTE zera o QM inteiro** (não
  entra em média — contaminação fecal não se dilui). Caso contrário,
  0,70 × nota de E. coli + 0,30 × nota de Coliformes Totais.
- **CO** (operacional): só o filtro — dentro da validade = 100, vencido = 0.
- **Linha "incompleta":** decidida **por linha**, conforme os dados que
  realmente estão presentes (não por uma regra fixa de ano) — isso resolve
  o caso do histórico, que não tem filtro registrado, sem precisar de uma
  variante de metodologia separada.
- **Arredondamento:** o IQA-B final (e as notas QFQ/QM/CO) são sempre
  **número inteiro** — como as faixas de classificação são valores
  fechados (80, 60, 40, 20), não faz sentido mostrar casas decimais.
  Arredonda-se uma vez só, no final da conta.

**Vírgula em todo lugar (04/09/2026):** alguns números na grade estavam
aparecendo com **ponto** (o IQA-B, e a turbidez quando reaparecia numa
coleta já salva) enquanto os outros campos mostravam **vírgula** — o
padrão brasileiro. Isso **não afetava nenhuma conta**: por trás dos panos
o sistema sempre guarda e calcula com o valor certo, ponto ali era só a
forma de exibir na tela. Ainda assim, corrigido para vírgula em todo
lugar, por clareza.

---

## 7. Estados de um bebedouro — resumo

São duas situações diferentes, resolvidas de formas diferentes:

**A. Ficou fora só naquele dia** (quebrado, em manutenção, interditado na
hora da coleta):
- **não** se mexe no cadastro; o bebedouro continua ativo;
- na grade daquela data, marca-se a linha como **"fora de operação nesta
  data"** (com observação curta opcional);
- a linha fica em branco de propósito e **não** entra no aviso de
  "faltando" ao publicar;
- na coleta seguinte o bebedouro volta ao normal automaticamente.

**B. Vai ficar fora por tempo indeterminado** (removido, desligado sem
previsão):
- no cadastro, o bebedouro é **desativado a partir de uma data** (por
  padrão, o dia de hoje);
- dessa data **em diante**, ele aparece **travado** ("fora de operação")
  nas coletas;
- coletas **anteriores** a essa data **não são afetadas** — continuam
  mostrando os resultados históricos que o bebedouro teve, e ainda dá para
  corrigi-los;
- **reativar** faz o bebedouro voltar a ser cobrado nas coletas. O período
  em que ficou fora deixa de ser marcado como "desativado"; para aquelas
  quinzenas, usa-se o marcador "fora de operação nesta data" (caso A). Não
  há histórico de vários ciclos liga/desliga — desativar é para saída por
  tempo indeterminado, que deve ser rara.

**Para a parte pública (etapa futura):** os dois estados já ficam
guardados (o marcador por linha, com a observação curta, e a data de
desativação). Quando a parte pública for construída, a direção acordada é
mostrar isso como transparência — "não monitorado nesta data / fora de
operação" no lugar de um IQA-B, em vez de simplesmente sumir. O texto
exato fica para aquela etapa.

---

## 8. Decisões tomadas nesta conversa

1. Esta etapa cuida só das **quinzenas recentes e novas**; a importação do
   histórico de 2023+ fica para depois.
2. Cada coleta é identificada por **uma data específica** (o dia da
   coleta), não por período tipo "1ª quinzena de setembro".
3. Gerenciamento nesta etapa = **ver a lista**, **corrigir um valor** (até
   depois de publicado) e **apagar uma coleta inteira**. Sem "voltar para
   rascunho".
4. A marca **rascunho / publicado** existe desde já; por enquanto serve
   para a equipe saber o que já foi conferido.
5. Desativação de bebedouro tem **data**: trava a linha nas coletas
   **daquela data em diante**; coletas anteriores ficam intactas e
   preenchíveis. (Ajuste feito em 02/09/2026, após a construção.)
6. Dá para **salvar rascunho com linhas em branco**; ao publicar, o
   sistema **avisa** o que falta mas **não bloqueia**.
7. O **cadastro dos bebedouros** entra nesta etapa (criar, editar local,
   desativar a partir de uma data / reativar).
8. Formato **"<valor"** só ocorre, até hoje, na **turbidez**.
9. Conferência de valores estranhos: só o **básico e leve**, sem travar, e
   descartável se complicar.
10. Lista de parâmetros: **fixa**, embutida no sistema.
11. Marcador **"fora de operação nesta data"** por linha da grade, para o
    caso pontual, separado do desativar do cadastro.

---

## 9. Decisões técnicas (fechadas em 02/09/2026)

Estas foram discutidas em linguagem comum, com alternativas e prós/contras,
antes de escolher. Não descem a nomes de ferramentas específicas — isso é
detalhe do plano de construção.

1. **Forma do sistema:** um **site na internet**, acessado pelo navegador
   de qualquer computador. (Descartadas: programa instalado num PC só;
   ferramenta "sem código".)
2. **Onde os dados ficam:** um **banco de dados de verdade**, com **cópia
   de segurança automática**. (Descartado: arquivo simples no servidor.)
3. **Com o que é feito:** um conjunto de ferramentas em torno da linguagem
   **Python**, escolhido porque **já traz uma área de administração
   pronta** que adianta justamente o cadastro e o gerenciamento das
   coletas; bastante material em português; hospedagem simples; a mesma
   base serve para a parte pública depois.
4. **Onde fica hospedado:** começar num **serviço de hospedagem pronto para
   usar**, com **foco em faixa gratuita** e backup incluído. O sistema
   nasce **portátil** (fácil de mudar de fornecedor) porque, após a
   validação do TCC, a intenção é o **IFRN adotar o sistema e levá-lo para
   a estrutura do próprio campus**.
   - Aviso registrado: a parte que roda o site costuma ter faixa gratuita
     tranquila; a parte do **banco de dados** pode ter só período gratuito
     ou custo pequeno (poucos dólares/mês). A opção gratuita exata é
     escolhida na hora de colocar no ar.
5. **Login da parte interna:** **um usuário e uma senha únicos**,
   compartilhados pela equipe do núcleo, protegendo todas as telas internas
   (cadastro, lançamento, gerenciar). Usa a **tela de login que já vem
   pronta** no conjunto de ferramentas. Sem cadastro de várias pessoas e
   sem níveis de permissão, como na definição do projeto. Quando um
   bolsista sai, a orientadora troca a senha. A parte pública (etapa
   futura) não terá login.

**Princípio de projeto:** não ficar preso a um fornecedor — manter o
sistema fácil de mover para a estrutura do IFRN mais adiante.

---

## 10. Materiais e pendências

**Já recebido (02/09/2026):** lista real B1–B15 com os locais, no arquivo
`Análise dos Bebedouros 2026.xlsx` na pasta do projeto. Os 15 estão
**ativos**. O arquivo traz também as coordenadas de GPS de cada bebedouro
— guardadas para a etapa futura do mapa público, não usadas nesta etapa.

B1 Mesas verdes · B2 Piscinas · B3 Marcenaria · B4 Quadra 3 · B5 Quadra 1 ·
B6 Biblioteca · B7 Campo · B8 Bloco C · B9 Bloco B · B10 Bloco D ·
B11 DIATINF · B12 DIACON · B13 DIAC · B14 DIAREN 1 · B15 DIAREN 2.

**Ainda pendente (não bloqueia esta etapa):**

- Qual serviço gratuito de hospedagem/banco será usado na hora de publicar.

---

## 11. Situação e ordem dos próximos passos

**Construído e testado (04/09/2026):** toda a parte interna descrita neste
documento — cadastro, grade de lançamento, rascunho/publicado, ver /
corrigir / apagar, desativação com data, identidade visual, e o IQA-B
completo (fórmula definida com a orientadora, recálculo ao salvar,
classificação, coluna na grade). Roda no computador; ainda **não** foi para
hospedagem.

**Ordem decidida pela orientanda (02/09/2026, ajustada em 04/09/2026) —
hospedar só quando tudo estiver pronto, não agora:**

1. ~~Metodologia do IQA-B~~ e ~~fórmula~~ — **prontas** (`bebedouros/iqab.py`,
   versão "1.0").
2. **Hospedar** o sistema (escolher o serviço na hora).
3. **Digitar manualmente** os dados de 2024/2025 direto no sistema já
   hospedado — o volume de análises desse período é pequeno, não compensa
   construir um importador de planilhas para usar uma única vez.
4. Já hospedado, seguir para a **parte pública** (mapa, abas, alertas).

Enquanto isso, a orientanda testa localmente. Publicar continua sendo uma
tarefa de ~30 min quando a hora chegar (ver `README-DEPLOY.md`).

**Dados de 2024/2025 com parâmetros faltando (04/09/2026):** essas análises
antigas têm pendências em alguns parâmetros, o que afeta o cálculo do
IQA-B. Decisão: não travar por ano (ex.: "só 2026 calcula IQA-B") — usar o
status **`incompleto`** que já existe em `iqab.py`, disparado linha a linha
conforme os dados realmente presentes. Uma linha de 2024/2025 (ou de
qualquer ano) sem os parâmetros obrigatórios mostra "incompleto" em vez de
nota; se completa, calcula normalmente. Isso depende de, ao definir a
fórmula (passo 1-2 acima), também definir quais parâmetros são
obrigatórios para o cálculo.
