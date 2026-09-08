# Desenho da Parte Visual — Mapa Público e Páginas de Resultado

> Data: 08/09/2026
> Documento em linguagem comum. Descreve **só** a parte visual do sistema:
> o mapa público do campus, a página de cada bebedouro, as abas Alertas e
> Parâmetros, e a nova tela interna "Início".
> Continua valendo tudo que está no `DEFINICAO-DO-PROJETO.md` e no
> `DESENHO-ENTRADA-E-RESULTADOS.md`. Nenhuma decisão de linguagem de
> programação, ferramentas ou hospedagem foi tomada aqui — isso já está
> fechado no documento anterior.

---

## 1. O que este documento cobre

- A **aba Mapa**, principal da parte pública.
- A **página de um bebedouro**, na versão pública e na versão interna
  (é a mesma página, com blocos a mais para quem está logado).
- A **aba Alertas** (pública).
- A **aba Parâmetros** (pública).
- A tela **Início**, nova, na parte interna — panorama dos 15 bebedouros.
- A **navegação** entre as telas que já existem e as novas.

## 2. O que NÃO entra neste documento

- **Cores exatas, fontes, medidas em pixel** — isso é detalhe de
  construção, resolvido durante a implementação seguindo a identidade
  visual que já existe no sistema (ver seção 3).
- **Os textos finais** das abas Parâmetros e Alertas, e as legendas do
  mapa — ficam como pendência (seção 9).
- **A imagem definitiva do campus** e as **fotos dos bebedouros** —
  pendência (seção 9); o sistema é construído para aceitar uma imagem
  provisória e trocar depois sem problema (seção 4.4).
- **Importação/digitação dos dados de 2024–2025** — já tratado no
  documento anterior, segue como próximo passo separado.

---

## 3. Identidade visual: a gota d'água

O elemento central de toda a parte visual é uma **gota d'água que se
enche** conforme a nota do IQA-B (0 a 100), colorida pela classificação
(as mesmas cinco cores que já existem no sistema hoje: Excelente, Boa,
Regular, Ruim, Crítica). Ela aparece em três tamanhos:

- **Grande**, com o número dentro, no topo da página de cada bebedouro.
- **Pequena**, como marcador colorido no mapa do campus.
- **Pequena**, na tabela de bebedouros da tela Início (parte interna).

Onde a nota não existe (dado "incompleto"), a gota aparece vazia/cinza em
vez de colorida — para não passar a impressão errada de nota zero.

---

## 4. Aba Mapa (pública, principal)

### 4.1 A imagem

Uma **imagem parada** do campus, vista de cima, com os 15 pontos marcados
sobre ela. Não é um mapa interativo de arrastar/zoom ao vivo (avaliamos
usar o mapa embutido do Google e descartamos: tem custo de manutenção
passada uma certa cota de acesso, depende do serviço deles estar no ar, e
descaracteriza a identidade visual do sistema — a imagem parada resolve
com menos peças podendo dar errado).

### 4.2 Os marcadores

Cada bebedouro é uma **gotinha colorida** (ver seção 3) na posição
correspondente sobre a imagem.

- **Passar o mouse** (computador) ou **tocar** (celular) mostra o nome:
  "B3 — Marcenaria", por exemplo.
- **Clicar/tocar** abre um **cartãozinho** por cima do mapa, sem sair da
  tela, com: foto do bebedouro, código e local, gota do IQA-B atual com a
  classificação, data da última análise, e o aviso de filtro vencido
  quando for o caso. O cartãozinho é montado com dados que já vêm
  carregados junto com a página (são só 15 bebedouros) — não faz uma nova
  busca ao servidor a cada clique, então não tem tela de carregando nem
  risco de erro de conexão nesse passo.
- O cartãozinho tem um botão **"Ver detalhes"**, que leva para a página
  completa daquele bebedouro (seção 5).

### 4.3 Aviso de direitos de imagem

Se a imagem do campus vier do Google Earth, os créditos que aparecem nela
("Google", "Imagery © ... [empresa]") **não podem ser cortados** — isso
vale certamente para o uso no texto do TCC. Para uso na página pública do
site, o ideal é substituir por planta ou imagem aérea oficial do IFRN,
assim que disponível (ver seção 9).

### 4.4 Trocar a imagem depois

A posição de cada gotinha é guardada como **porcentagem da largura e da
altura da imagem** (não como pixel fixo). Trocar a imagem do campus depois
é: trocar o arquivo e reconferir se as 15 posições continuam caindo em
cima do bebedouro certo — não exige mudar código nem refazer a tela.

---

## 5. Página do bebedouro (pública e interna)

Mesma página para os dois públicos; a versão interna mostra blocos a mais
(marcados abaixo como "só interna").

De cima para baixo:

1. **Cabeçalho:** foto do bebedouro, código e local, e a **gota grande do
   IQA-B atual** com a classificação e a data da última análise.
2. **Aviso de filtro vencido**, em destaque, quando a última coleta
   publicada marcou o filtro como vencido.
3. *(Só interna)* **De onde vem a nota:** três cartões — Físico-química da
   água (peso 30%), Presença de bactérias (peso 50%), Situação do filtro
   (peso 20%) — cada um com sua nota e cor. Quando a nota do filtro está
   baixa, o cartão mostra o motivo por escrito (ex.: "filtro fora da
   validade na data da coleta"). Não entra em versão pública — ver
   decisão na seção 8.
4. **O que é monitorado nesta água:** lista neutra dos parâmetros com o
   valor da última coleta (cloro, condutividade, nitrato, turbidez, pH,
   coliformes totais, E. coli), sem marcação de certo/errado ao lado —
   decisão da seção 8. Um link leva para a aba Parâmetros, que explica
   cada um.
5. **Gráfico de evolução:**
   - Mostra por padrão os **últimos 12 meses**, com opções para trocar
     para 6 meses ou o histórico completo.
   - O fundo do gráfico tem **cinco faixas coloridas horizontais**, uma
     por classificação, para dar leitura visual mesmo com muitos pontos
     ao longo dos anos.
   - Cada quinzena é um ponto — **não é feita nenhuma média** que junte
     coletas.
   - Um **seletor** troca o que o gráfico mostra: IQA-B ou um parâmetro
     específico (cloro, turbidez, pH, etc.). Isso dá utilidade ao
     histórico de 2024/2025, que tem parâmetros mas não tem IQA-B
     calculado (falta a situação do filtro nesses anos — ver documento
     anterior, seção 13).
   - Onde o IQA-B não existe (linhas "incompletas"), o gráfico mostra um
     intervalo em branco em vez de zero ou de emendar a linha — para não
     parecer perda de dado.
6. **Última quinzena em tabela** — só a coleta mais recente, parâmetro por
   parâmetro. Um link discreto ("ver quinzenas anteriores") dá acesso ao
   histórico completo, para quem quiser.

---

## 6. Aba Alertas (pública)

Lista os bebedouros com **IQA-B abaixo de 40** (faixas Ruim e Crítica),
como já previsto no documento de definição do projeto. O nome da aba e o
texto de abertura ficam como pendência de redação (seção 9) — a ideia é
que o texto deixe claro que a lista existe para acompanhamento, não como
reprovação.

---

## 7. Aba Parâmetros (pública)

Um **cartão por parâmetro monitorado** (Cloro Residual Livre,
Condutividade Elétrica, Nitrato, Turbidez, pH, Coliformes Totais, E.
coli), cada um com:

- nome;
- explicação curta, em linguagem comum, do que é;
- unidade de medida;
- **limite de referência** da Portaria MS nº 888/2021 usado no cálculo do
  IQA-B (ex.: "pH deve ficar entre 6 e 9").

A Condutividade Elétrica entra com uma observação a mais: é acompanhada
como dado de referência, mas **não entra no cálculo** do índice.

Os textos de cada cartão ficam como pendência de redação (seção 9).

---

## 8. Decisões desta etapa (fechadas em 08/09/2026)

1. **Painel do mapa em cartãozinho na própria tela**, não em página
   separada e não com busca ao servidor a cada clique — os dados dos 15
   bebedouros já vêm carregados com a página do mapa.
2. **Página do bebedouro é a mesma para público e interno**, com blocos a
   mais para quem está logado, em vez de duas páginas distintas.
3. **A gota grande do IQA-B aparece na página do bebedouro**, não só no
   cartãozinho do mapa — é a informação principal e precisa estar onde a
   pessoa parar para ler.
4. **A tabela de resultados na página do bebedouro mostra só a última
   quinzena**, com link para o histórico completo à parte.
5. **O gráfico de evolução abre numa janela de 12 meses**, com opção de
   ver mais, e tem seletor para trocar entre IQA-B e parâmetros
   individuais — pensando no volume de coletas que vai se acumular ao
   longo dos anos.
6. **Pesos e notas parciais (QFQ/QM/CO) e o motivo da nota baixa não
   aparecem na versão pública** da página do bebedouro — só na interna.
   Decisão: explicar detalhadamente a metodologia do cálculo não é
   objetivo da parte pública; o foco é deixar claro **o que é monitorado**,
   não como a conta é feita.
7. **Os valores de "o que é monitorado" aparecem neutros**, sem marcação
   de certo/atenção ao lado de cada parâmetro — para não gerar
   interpretação errada de um parâmetro isolado fora da faixa quando a
   água está, no geral, boa.
8. **A aba Alertas pública é mantida** como estava definida no documento
   de definição do projeto (lista de IQA-B abaixo de 40), mesmo sendo uma
   informação mais direta — decisão da orientanda, ciente do trade-off
   frente à decisão 7.
9. **A aba Parâmetros mostra o limite de referência oficial** de cada
   parâmetro (Portaria 888/2021) — decisão da orientanda, ciente de que
   isso permite à pessoa comparar sozinha com o valor visto na página do
   bebedouro.
10. **Imagem do mapa: parada, não interativa ao vivo.** Descartado o mapa
    embutido do Google pelo custo de manutenção e dependência de serviço
    externo, a favor de uma imagem fixa com posições em porcentagem
    (fácil de trocar depois — seção 4.4).
11. **Tela Início (interna, nova):** os três alertas internos já definidos
    no documento de definição (IQA-B ruim, filtro vencido, quinzena sem
    dados) em destaque no topo, e abaixo uma tabela com os 15 bebedouros
    (gota pequena, nota, classificação, data da última análise). Layout
    em tabela, não em cartões, porque o uso interno é comparar os 15 de
    uma vez.
12. **Navegação:** login continua caindo direto em **Coletas** (não em
    Início) — é o ponto de entrada de quem vai digitar dados, que é o uso
    mais frequente. O menu ganha o item "Início". Depois de publicar uma
    coleta, o sistema leva de volta para a tela Início, já com as notas
    novas.

---

## 9. Materiais e pendências

**Ainda pendente:**

- **Imagem do campus para o mapa** — a orientanda já está marcando as
  posições dos 15 bebedouros sobre uma imagem do Google Earth, para uso
  provisório e para o texto do TCC (créditos da imagem preservados).
  Verificar com a coordenação do campus se existe planta ou imagem aérea
  **oficial do IFRN** para uso na página pública do site futuramente —
  não bloqueia a construção, a troca depois é simples (seção 4.4).
- **Fotos dos 15 bebedouros.**
- **Textos da aba Parâmetros** (explicação de cada parâmetro).
- **Texto/nome de abertura da aba Alertas.**

Nenhum desses itens trava o próximo passo (seção 10) — a construção usa
conteúdo provisório onde ainda faltar material.

---

## 10. Próximos passos

Conforme a ordem já registrada no `DESENHO-ENTRADA-E-RESULTADOS.md`
(seção 11): este desenho da parte visual entra depois que o sistema for
hospedado e os dados de 2024/2025 forem digitados. Quando chegar a vez,
o passo seguinte é montar o **plano de implementação** desta parte visual
(telas, nessa ordem: Início interna → página do bebedouro → mapa público
→ Alertas → Parâmetros), com as decisões de ferramenta específicas
(biblioteca de gráfico, por exemplo) tratadas nesse momento.
