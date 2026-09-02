# Projeto: Sistema de Monitoramento e Gestão da Água nos Bebedouros do IFRN-CNAT

> Documento em construção. Estamos definindo O PROJETO em linguagem comum.
> As decisões técnicas (linguagem de programação, ferramentas, hospedagem) só
> serão tratadas depois que o projeto estiver bem definido.

---

## 1. Contexto

Produto de TCC. Hoje o acompanhamento da qualidade da água dos bebedouros do
IFRN – Campus Natal Central é feito de forma manual, com planilhas soltas numa
pasta compartilhada. O objetivo é substituir isso por um sistema que:

- organize num só lugar o cadastro dos bebedouros e os resultados das análises;
- calcule automaticamente o índice de qualidade **IQA-B** e sua classificação;
- mostre a evolução de cada bebedouro ao longo do tempo;
- tenha uma parte pública para a comunidade do campus;
- sinalize situações que exigem atenção (alertas).

Aplicação inicial: **15 bebedouros**.

---

## 2. Como funciona hoje (processo manual atual)

- Um **bolsista dedicado** faz a coleta das amostras nos bebedouros.
- As amostras vão para o **laboratório do próprio IFRN**, onde as análises são feitas.
- Os resultados são repassados à **professora orientadora** numa **planilha Excel**.
- As planilhas ficam **na nuvem**, em pasta compartilhada com os membros do projeto.
- As coletas acontecem **quinzenalmente** (a cada 15 dias).
- **Nenhum índice é calculado hoje** — só resultados brutos.
- A **situação do filtro** é observada pelo bolsista na coleta, mas **não é
  registrada em lugar nenhum**.

---

## 3. Os bebedouros

- São **15**, identificados por código **"B" + número**: B1, B2, … B15.
  Cada código corresponde a um local (ex.: B1 = próximo às mesas verdes;
  B2 = área das piscinas).
- **Lista completa B1–B15 (com o local de cada um) será fornecida pela orientanda**
  e entra como cadastro inicial do sistema.
- A única informação de estado que importa sobre o bebedouro em si é
  **ativo / desativado**.

---

## 4. As análises (conteúdo da planilha do laboratório)

Parâmetros medidos a cada coleta:

| Parâmetro | Unidade | Como aparece o resultado | Dimensão |
|---|---|---|---|
| Cloro Residual Livre | mg/L Cl₂ | número | Físico-Química (QFQ) |
| Condutividade Elétrica | (unidade a confirmar) | número | Físico-Química (QFQ) |
| Nitrato | mg/L N | número | Físico-Química (QFQ) |
| Turbidez | UNT | número **ou** limite "<0,751" | Físico-Química (QFQ) |
| pH | — | número | Físico-Química (QFQ) |
| Coliformes Totais | — | **AUSENTE** ou **PRESENTE** | Microbiológica (QM) |
| E. coli | — | **AUSENTE** ou **PRESENTE** | Microbiológica (QM) |

Organização atual da planilha: **uma aba nova por quinzena**, todos os resultados
juntos, **um bebedouro por linha**.

O sistema precisa aceitar resultados **não numéricos**:
- "AUSENTE / PRESENTE" (microbiológicos);
- valores com limite de detecção, como "<0,751" na turbidez — que **conta como o
  melhor caso possível** (nota cheia no parâmetro).

---

## 5. O filtro (dimensão CO)

- Cada filtro tem etiqueta com a data da última troca e prazo de validade de
  **6 meses**. "Vencido" = passaram-se mais de 6 meses dessa data.
- Esse registro hoje existe **apenas no setor de manutenção do campus**.
- **Decisão:** o sistema **não guarda a data da etiqueta**. Ao lançar a coleta,
  quem digita apenas marca o filtro como **"dentro da validade"** ou **"vencido"**
  (observação do bolsista na hora da coleta).
- Consequência aceita: sem a data, o sistema não avisa "vai vencer em X dias" —
  registra apenas o estado informado a cada coleta.

---

## 6. Quem usa o sistema

- **Digitam dados:** o bolsista e a orientadora.
- **Também acompanha os resultados:** a orientadora.
- **Uma única conta** para todo o time (o projeto fica num **núcleo de extensão**
  com troca de bolsistas a cada 6 meses; a conta é do núcleo, não da pessoa).
- A parte pública **não exige login**.
- **Sem etapa de aprovação / revisor:** a orientadora confia no que o bolsista lança.
- Consequência aceita: quem tem o login pode fazer tudo, inclusive ajustar os
  pesos/parâmetros da fórmula. Sem separação de permissões no MVP.

---

## 7. Fluxo de trabalho

1. Bolsista coleta as amostras (quinzenal) e anota a situação do filtro.
2. Laboratório do IFRN faz as análises.
3. Bolsista/orientadora lançam no sistema os resultados daquela quinzena
   (grade com os 15 bebedouros — ver seção 14) — fica como **rascunho**.
4. O sistema calcula o IQA-B de cada bebedouro daquela quinzena.
5. Quando a quinzena está completa e conferida, aperta-se o **botão "publicar"**;
   só então aqueles resultados aparecem na parte pública.
6. Correções: **edita direto**. O sistema não guarda histórico de "valor antigo →
   valor novo".

---

## 8. O índice IQA-B

Combina três dimensões:
1. **QFQ** – Qualidade Físico-Química (5 parâmetros)
2. **QM** – Qualidade Microbiológica (2 parâmetros)
3. **CO** – Condição Operacional — **somente a situação do filtro**
   ("dentro da validade" / "vencido"). Nenhuma outra condição operacional deve
   ser adicionada agora.

### 8.1 O que já está definido

**Fórmula do índice final:**

```
IQA-B = (QFQ × 0,3) + (QM × 0,5) + (CO × 0,2)
```

- QFQ, QM e CO são notas de **0 a 100**; o IQA-B final também é **0 a 100**.

**Classificação do IQA-B final:**

| Faixa | Classificação |
|---|---|
| 80 – 100 | Excelente |
| 60 – 79 | Boa |
| 40 – 59 | Regular |
| 20 – 39 | Ruim |
| < 20 | Crítica |

**Turbidez "<0,751":** conta como melhor caso possível (nota cheia no parâmetro).

### 8.2 Decisões metodológicas PENDENTES (em ajuste no TCC)

Estas respostas ainda estão em processo de ajuste metodológico do TCC e serão
definidas depois. O sistema deve tratá-las como **configuráveis**:

- **Pontuação por parâmetro:** como cada parâmetro vira uma nota de 0 a 100.
  Base de referência acordada: **limites da Portaria MS nº 888/2021**.
- **Cálculo do QFQ:** como combinar as 5 notas de parâmetro (média simples /
  média com pesos / puxada pela pior nota).
- **Cálculo do QM:** como AUSENTE/PRESENTE viram nota e se **E. coli PRESENTE
  zera o QM**.
- **Cálculo do CO:** que nota o filtro recebe quando "dentro da validade" e
  quando "vencido".

Implicação para o sistema: cada IQA-B calculado deve registrar **qual versão da
configuração/metodologia** foi usada, para que o histórico continue coerente
quando a metodologia mudar.

---

## 9. Telas — parte interna (com login)

1. **Tela inicial:** lista dos 15 bebedouros, cada um com o **IQA-B atual** e uma
   **cor** conforme a classificação.
2. **Tela do bebedouro:** as duas coisas juntas —
   - **gráfico** da evolução do IQA-B ao longo dos meses;
   - **tabela** com os resultados brutos de cada quinzena.
3. Foco sempre **bebedouro por bebedouro** (sem visão de "média do campus" no MVP).

---

## 10. Telas — parte pública (sem login)

Organizada em **abas**:

- **Aba Mapa (principal):** mapa do campus com os bebedouros marcados. Ao clicar
  num bebedouro, a pessoa vê:
  - IQA-B da quinzena atual e a classificação (com cor);
  - histórico / evolução ao longo dos meses;
  - data da última análise;
  - alerta de necessidade de troca do filtro (quando a última coleta publicada
    marcou o filtro como "vencido").
- **Aba Alertas:** lista apenas os bebedouros com **IQA-B ruim**.
- **Aba Parâmetros:** mostra e **explica** os parâmetros monitorados.

Ponto de partida; abas e conteúdo podem mudar depois.

**Necessidade de material:** uma **imagem/planta do campus** e a **posição de
cada bebedouro** sobre ela.

---

## 11. Alertas

**Parte interna (bolsista / orientadora):**
- **IQA-B ruim** — bebedouro na faixa "Ruim" ou "Crítica" (IQA-B < 40).
- **Filtro vencido** — a última coleta marcou o filtro como "vencido".
- **Quinzena sem dados** — passou uma quinzena sem nenhum resultado lançado para
  um bebedouro (ativo).

*(Não entram no MVP: parâmetro isolado fora do limite, E. coli PRESENTE como
alerta próprio, queda brusca de IQA-B entre quinzenas.)*

**Aba pública de Alertas:** lista os bebedouros com **IQA-B < 40** (faixas "Ruim"
e "Crítica").

---

## 12. Prazo

- Sem data de defesa marcada.
- Meta: **concluir o sistema em no máximo 8 semanas** (a partir de 31/08/2026,
  ou seja, até o fim de outubro/2026), para finalizar a escrita do TCC em
  **novembro/2026**.
- Isso reforça um MVP enxuto: cadastro + lançamento de coletas + cálculo do
  IQA-B + telas internas + parte pública + os 3 alertas acima.

---

## 13. Dados históricos

- **Decisão:** carregar no sistema os dados históricos existentes **desde 2023**
  (para os gráficos de evolução já nascerem preenchidos).
- Volume aproximado: coletas quinzenais de 2023 até hoje ≈ 50+ quinzenas × 15
  bebedouros (a confirmar a partir das planilhas reais).
- **A definir:** como esse histórico entra — digitação manual pela grade (inviável
  para tantos meses) **ou** uma carga única a partir das planilhas Excel
  existentes. A carga única a partir do Excel é o caminho realista; exige acertar
  o formato das planilhas antigas (que pode ter variado ao longo do tempo).
- **Ponto metodológico:** as quinzenas históricas **não têm registro da situação
  do filtro** (nunca foi anotada). Definir como calcular o IQA-B histórico —
  sem a dimensão CO (só QFQ + QM, com pesos renormalizados) ou deixando CO em
  branco no histórico. Fica junto das decisões metodológicas pendentes (8.2).

## 14. Tela de lançamento

- Formato **grade/tabela com os 15 bebedouros**, parecido com a planilha atual:
  colunas = parâmetros + situação do filtro; linhas = bebedouros. Preenche a
  quinzena inteira numa tela.

## 15. Ainda a definir (não metodológico)

- Planta do campus + posição dos bebedouros (material a ser fornecido).
- Lista B1–B15 com o local de cada um (material a ser fornecido).
- Unidade da Condutividade Elétrica.
- Formato das planilhas históricas (para a carga única).
- Textos da aba "Parâmetros" (a serem fornecidos).

---

## 16. Próximos passos

1. **Você valida este documento** (seções 1–15) e corrige o que estiver errado.
2. Fornece os materiais pendentes (lista B1–B15, planta do campus, textos da aba
   Parâmetros) — podem vir depois, não travam o próximo passo.
3. **Só então** montamos juntos a **arquitetura técnica** — também em linguagem
   acessível — cobrindo: como o sistema é organizado por dentro, onde os dados
   ficam guardados, como o histórico é carregado, como a parte pública é separada
   da interna, e as escolhas de ferramentas/hospedagem, sempre com alternativas
   e trade-offs antes de decidir.
4. Depois disso, o plano de implementação e a construção.

## 17. Decisões técnicas — DEPOIS

Nada de linguagem de programação / ferramentas / hospedagem até este documento de
projeto estar validado pela orientanda.
