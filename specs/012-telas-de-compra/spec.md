# Feature Specification: Telas de Compra — Filme, Assentos e Pagamento

**Feature Branch**: `main` — sem branch própria, como nas 003–011

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Recompor a página do filme, o mapa de assentos e o pagamento
inspirado no ingresso.com, sem alterar o catálogo."

> **Esta feature é a composição que a 011 registrou e não fez.** A checagem anti-slop daquela
> feature passou com uma ressalva: a identidade estava na paleta e na tipografia; o **arranjo** das
> telas de compra ainda era o de uma lista. A 011 proibiu alargar a si mesma para mexer nisso. Esta
> é a feature que mexe — e só aqui.
>
> **O catálogo não entra.** Home, carrossel, trilhas, busca, seed, sincronização e os contratos de
> destaque permanecem exatamente como a 011 os deixou. Se uma mudança nesta feature alterar o que
> aparece na primeira dobra da home, ela está fora de escopo.
>
> **Nenhuma regra de negócio é reaberta.** Reservar, pagar, emitir, compartilhar e validar
> continuam as mesmas operações, com as mesmas garantias. O que muda é **como** a pessoa vê o filme,
> escolhe o horário, confirma o lugar e paga.
>
> A exploração visual vive em `prototipo/index.html`. Esta spec extrai o que vale: a arquitetura de
> informação das três telas, não o HTML do protótipo.

## O que permanece e o que esta feature mexe

| Superfície | Nesta feature |
|---|---|
| Home, carrossel, trilhas, busca | **Intocados** |
| Cabeçalho, marca, paleta da 011 | **Intocados** — consomem o que já existe |
| Página do filme | **Recomposta** — sessões, sobre, trailers |
| Mapa de assentos | **Recomposto** — resumo ao lado da sala |
| Pagamento e ingresso emitido nessa tela | **Recompostos** — o que se compra visível ao pagar; o ingresso como objeto |
| Portaria, entrada, meus ingressos, página pública | **Intocados** na composição; recebem a paleta já aplicada |
| APIs, seed, limite do carrossel, regras de trilha | **Intocados** |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher sessão como grade de cinema (Priority: P1)

A pessoa abre um filme. Vê o cartaz, o título e a classificação. Em seguida escolhe o **dia**,
depois o **horário** agrupado por sala — alvos compactos, não uma lista de linhas. Uma sessão
esgotada se distingue sem parecer botão morto de formulário. Um toque no horário disponível leva
ao mapa.

**Why this priority**: É o primeiro passo da compra depois do catálogo, e é o que hoje mais parece
configuração em vez de programação. Sem esta história a feature não entrega o motivo de existir.

**Independent Test**: Abrir um filme com sessões em mais de um dia e mais de uma sala, escolher um
dia, acionar um horário disponível e chegar ao mapa numa interação.

**Acceptance Scenarios**:

1. **Given** um filme com sessões publicadas, **When** a página abre, **Then** a pessoa vê um seletor
   de dia e, para o dia ativo, os horários agrupados por sala.
2. **Given** dois dias com grades diferentes, **When** a pessoa troca o dia, **Then** os horários
   passam a ser os daquele dia, sem recarregar o filme.
3. **Given** uma sessão esgotada, **When** ela é exibida, **Then** o estado "Esgotada" é legível e
   o alvo **não** navega para o mapa.
4. **Given** uma sessão com lugares, **When** a pessoa aciona o horário, **Then** chega ao mapa
   daquela sessão — uma interação.
5. **Given** um filme sem sessões e com estreia futura, **When** a aba de sessões é vista, **Then**
   a ausência é explicada em português, com a data de estreia quando ela for conhecida.

---

### User Story 2 - Sobre e trailers no mesmo filme (Priority: P1)

Na mesma página, a pessoa troca para **Sobre** e lê a sinopse e os dados que o filme já tem
(classificação, duração, gênero). Troca para **Trailers** e reproduz o que já está associado ao
filme. Não sai da página, não cai na home, não pede dado que o catálogo ainda não guarda.

**Why this priority**: É o que transforma a página de "lista de horários com sinopse em cima" em
página de filme. Sem as duas abas, a US1 sozinha ainda lê como formulário.

**Independent Test**: Abrir um filme que tem sinopse e trailer, percorrer Sessões → Sobre →
Trailers, reproduzir o trailer e voltar às sessões sem perder o filme.

**Acceptance Scenarios**:

1. **Given** a página do filme, **When** ela é observada, **Then** existem três seções mutuamente
   exclusivas: Sessões, Sobre e Trailers — a ativa é evidente.
2. **Given** a seção Sobre, **When** é exibida, **Then** mostra a sinopse completa e os metadados
   já conhecidos do filme (classificação, duração, gênero). Não inventa direção, elenco nem idioma
   que o catálogo não persiste.
3. **Given** o filme tem trailer persistido, **When** a seção Trailers é aberta, **Then** a pessoa
   consegue reproduzi-lo a partir daquela seção.
4. **Given** o filme não tem trailer, **When** a seção Trailers é aberta, **Then** a ausência é
   explicada em português — a seção não some e não mostra um alvo desabilitado.
5. **Given** um filme sem sessões (estreia futura), **When** a pessoa abre Sobre ou Trailers,
   **Then** as duas seções continuam disponíveis.

---

### User Story 3 - Escolher lugares com o resumo à vista (Priority: P1)

No mapa, a sala continua sendo a peça principal: tela, fileiras, corredor, quatro estados por
forma. Ao lado — não empurrado para baixo do mapa em tela larga — a pessoa vê o filme, o horário,
os lugares escolhidos, o total e o caminho para pagar. O prazo da reserva aparece quando a reserva
existe.

**Why this priority**: Hoje o resumo compete com a rolagem do mapa. Quem escolhe o lugar precisa
ver o que está levando sem perder a sala.

**Independent Test**: Selecionar dois lugares e conferir que o resumo ao lado lista os dois, o
total e o CTA, e que os quatro estados do mapa continuam distinguíveis em escala de cinza.

**Acceptance Scenarios**:

1. **Given** o mapa em tela larga, **When** é observado, **Then** a sala e o resumo da compra
   aparecem lado a lado — o resumo não fica só abaixo do mapa.
2. **Given** lugares selecionados, **When** a seleção muda, **Then** o resumo atualiza lugares e
   total na hora.
3. **Given** nenhum lugar selecionado, **When** a pessoa tenta confirmar, **Then** o sistema informa
   que é preciso escolher ao menos um, como já fazia.
4. **Given** o mapa, **When** é visto em escala de cinza, **Then** livre, selecionado, tomado e
   acessibilidade continuam distinguíveis **sem depender só de cor**.
5. **Given** uma tela estreita, **When** o mapa é exibido, **Then** o resumo empilha abaixo da sala
   e a página **não** ganha rolagem lateral.

---

### User Story 4 - Pagar vendo o que se leva, receber ingresso que parece ingresso (Priority: P1)

Na tela de pagamento, o resumo do que está sendo comprado permanece visível ao lado do formulário
enquanto a pessoa informa o cartão. O prazo continua correndo. Depois da aprovação, os ingressos
aparecem na mesma tela, **um por lugar**, como objeto: lugar em evidência, código em QR com fundo
branco, código em texto para a portaria digitar.

**Why this priority**: Pagar sem ver o que se leva e receber um cartão genérico no lugar de um
ingresso são os dois pontos em que a compra deixa de parecer cinema.

**Independent Test**: Reservar dois lugares, pagar, e conferir que o resumo esteve visível durante
o formulário e que os dois ingressos emitidos mostram lugar, QR branco e código digitável.

**Acceptance Scenarios**:

1. **Given** uma reserva a pagar em tela larga, **When** a página abre, **Then** o resumo (filme,
   sessão, sala, lugares, total) e o formulário aparecem lado a lado.
2. **Given** o formulário, **When** o prazo está correndo, **Then** o tempo restante permanece
   visível sem esconder o resumo.
3. **Given** o pagamento aprovado, **When** os ingressos são exibidos, **Then** há um por lugar,
   o lugar está em evidência, o QR tem fundo branco e o código em texto está visível.
4. **Given** uma recusa, **When** ela é exibida, **Then** a frase continua sendo a do servidor, em
   português, com a próxima ação — a composição nova não apaga a distinção entre recusa e erro de
   preenchimento.
5. **Given** uma tela estreita, **When** pagamento ou ingressos são exibidos, **Then** empilham sem
   rolagem lateral.

---

### User Story 5 - O catálogo e as regras continuam os mesmos (Priority: P1)

A home, o carrossel, as trilhas e a busca não mudam. Comprar, pagar, emitir, compartilhar e
validar continuam as mesmas operações. Se um teste de regra de negócio quebrar, a composição está
errada — não o teste.

**Why this priority**: É o que impede esta feature de virar uma reabertura da 001, da 004, da 007
ou da 008. Sem ela, "recompor três telas" vira licença para mexer no fluxo.

**Independent Test**: Percorrer a home e conferir que carrossel e trilhas estão iguais; rodar a
suíte das features 001–011 e conferir que nenhuma asserção de regra de negócio precisou ser
alterada.

**Acceptance Scenarios**:

1. **Given** a home, **When** é comparada à da 011, **Then** carrossel, trilhas e busca permanecem
   na composição já entregue.
2. **Given** a suíte das features 001–011, **When** é executada, **Then** as asserções de regra de
   negócio passam sem alteração.
3. **Given** um teste que precise mudar, **When** a mudança é avaliada, **Then** ela é de seletor
   ou de estilo das três telas — nunca de regra, contrato de catálogo, seed ou limite de carrossel.
4. **Given** os estados de erro e vazio das três telas, **When** são exibidos, **Then** continuam
   presentes e escritos para humanos.

---

### Edge Cases

- **Filme sem sessões e sem trailer**: Sobre continua útil; Sessões e Trailers explicam a ausência.
- **Um único dia de sessão**: o seletor de dia permanece — não some por ter uma opção só.
- **Uma única sala no dia**: os horários ainda se agrupam sob o nome da sala.
- **Sessão esgotada ao lado de disponível**: distinguíveis por texto e por comportamento, não só
  por cor.
- **Assento selecionado ao lado de tomado**: distinguíveis em escala de cinza.
- **Reserva prestes a vencer na tela de pagamento**: o prazo continua visível com o resumo.
- **Ingresso impresso em preto e branco**: continua utilizável; o QR permanece com fundo claro.
- **Tela de 320px**: abas, grade de horários, mapa e pagamento sem rolagem lateral da página.
- **Movimento reduzido**: nada que a feature introduza ignora a preferência.
- **Trailer indisponível no provedor**: a seção explica a falha; não deixa um retângulo mudo.

## Requirements *(mandatory)*

### O recorte

- **FR-001**: Esta feature recomõe **apenas** a página do filme, o mapa de assentos e a tela de
  pagamento (incluindo os ingressos emitidos nessa tela).
- **FR-002**: Home, carrossel, trilhas, busca, cabeçalho e marca **NÃO PODEM** ser alterados por
  esta feature.
- **FR-003**: Nenhuma sincronização, seed, limite de carrossel, regra de trilha ou contrato de
  catálogo pode mudar.
- **FR-004**: Nenhum campo novo de catálogo pode ser exigido. Direção, elenco e idioma **não**
  entram se o registro do filme ainda não os persiste.

### Página do filme

- **FR-005**: A página do filme DEVE oferecer três seções: **Sessões**, **Sobre** e **Trailers**.
  Só uma está visível por vez, e a ativa é evidente.
- **FR-006**: A seção Sessões DEVE apresentar primeiro o dia, depois os horários agrupados por
  sala.
- **FR-007**: Cada horário disponível DEVE ser um alvo único até o mapa daquela sessão.
- **FR-008**: Horário esgotado DEVE ser legível como esgotado e NÃO DEVE navegar.
- **FR-009**: A seção Sobre DEVE exibir a sinopse completa e os metadados já persistidos
  (classificação, duração, gênero). Ausentes simplesmente não aparecem — nunca "N/A".
- **FR-010**: A seção Trailers DEVE reproduzir os trailers **já persistidos** do filme. Expor na
  página um trailer que o registro já tem NÃO conta como alteração de catálogo. Sincronizar campo
  novo, sim.
- **FR-011**: Sem trailer, a seção Trailers DEVE explicar a ausência em português. Alvo
  desabilitado é violação.
- **FR-012**: Filme sem sessões continua oferecendo Sobre e Trailers.

### Mapa de assentos

- **FR-013**: Em tela larga, o resumo da escolha (filme, horário, sala, lugares, total, ação)
  DEVE aparecer ao lado do mapa, não apenas abaixo.
- **FR-014**: O mapa DEVE continuar distinguindo livre, selecionado, tomado e acessibilidade
  **sem depender apenas de cor**.
- **FR-015**: Confirmar sem lugar, limite de seleção, conflito e sessão esgotada permanecem como
  a 007 definiu — só a composição muda.
- **FR-016**: O prazo da reserva, quando existir, permanece visível no resumo.

### Pagamento e ingresso nessa tela

- **FR-017**: Em tela larga, o resumo do que se compra e o formulário DEVEM aparecer lado a lado
  enquanto a reserva está a pagar.
- **FR-018**: O prazo restante DEVE permanecer visível durante o preenchimento.
- **FR-019**: Recusa e erro de preenchimento DEVEM continuar distinguíveis, com a frase do
  servidor na recusa.
- **FR-020**: Após a aprovação, cada ingresso DEVE parecer um objeto de ingresso: um por lugar,
  lugar em evidência, QR com fundo **branco**, código em texto visível.
- **FR-021**: O fundo do QR **não pode** ser harmonizado com a paleta. A exceção da 008 permanece.

### Preservação

- **FR-022**: Nenhuma regra de negócio das features 001–011 pode ser alterada.
- **FR-023**: Nenhuma asserção de regra de negócio pode ser removida ou enfraquecida. Ajuste de
  seletor ou de estilo nas três telas é aceitável quando inevitável.
- **FR-024**: A paleta, a tipografia da marca e a logo da 011 DEVEM ser reutilizadas — nenhum
  valor de cor novo fora dos tokens.
- **FR-025**: Nenhuma das três telas pode ganhar rolagem lateral em 320px.
- **FR-026**: Estados de erro e vazio DEVEM continuar presentes e escritos para humanos.
- **FR-027**: Nenhuma superfície pode conter texto de preenchimento, marcador de posição ou
  "em breve".
- **FR-028**: Proibições anti-slop da 011 continuam valendo nestas três telas: sem laranja
  residual, sem roxo/índigo, sem halo, sem pílula fina genérica, sem ícone de biblioteca de
  cinema.

### Key Entities

- **Seção da página do filme** *(nova, só de apresentação)*: uma das três — Sessões, Sobre,
  Trailers. Não é entidade de banco.
- **Grade do dia** *(nova, só de apresentação)*: as sessões já persistidas, agrupadas por dia
  civil e depois por sala. O agrupamento não cria sessão.
- **Resumo da compra** *(existente, reposicionado)*: filme, sessão, sala, lugares, total e prazo.
  O valor continua sendo o que o servidor enviou.
- **Ingresso emitido** *(existente, recomposto nesta tela)*: um por lugar, QR branco, código
  digitável. A composição muda; o conteúdo e a assinatura não.

## Success Criteria *(mandatory)*

- **SC-001**: Em um filme com sessões em mais de um dia, a pessoa escolhe dia e horário e chega
  ao mapa em **uma** interação a partir do horário.
- **SC-002**: 100% dos filmes com página própria oferecem as três seções; a ausência de sessão ou
  de trailer é explicada, nunca omitida em silêncio.
- **SC-003**: Sobre não exibe nenhum dado que o registro do filme não tenha.
- **SC-004**: Em viewport larga (≥ 1000px), mapa e resumo aparecem lado a lado; pagamento a pagar
  mostra resumo e formulário lado a lado.
- **SC-005**: Os quatro estados do mapa permanecem distinguíveis em escala de cinza.
- **SC-006**: Após o pagamento, cada ingresso mostra lugar em evidência, QR com fundo branco e
  código digitável.
- **SC-007**: A home — carrossel, trilhas e busca — permanece visualmente a da 011.
- **SC-008**: Nenhuma das três telas apresenta rolagem lateral em 320px.
- **SC-009**: A suíte de comportamento das features 001–011 passa sem que nenhuma asserção de
  regra de negócio tenha sido alterada.
- **SC-010**: Alguém que não conhece o projeto, na página do filme, identifica em **3 segundos**
  como escolher o horário — aponta o dia e o alvo do horário, não uma lista de configurações.

## Assumptions

- **O catálogo está fechado.** Home, carrossel, trilhas, busca, seed e sincronização não são o
  problema que esta feature resolve. A ressalva da 011 sobre a primeira dobra permanece como
  achado — não é desta feature.

- **Sobre usa o que o filme já tem.** Sinopse, classificação, duração e gênero bastam para a
  seção existir. Trazer direção e elenco exigiria estender o catálogo, e FR-004 proíbe isso.

- **Trailer na página do filme é o trailer já persistido.** A 001 já guarda trailer. A home já o
  reproduz. A página do filme passar a exibi-lo é rearranjo de dado existente.

- **Agrupar sessões por dia e sala não cria dado.** A lista que a página já recebe é só
  reapresentada.

- **O pagamento já tem duas colunas; o que falta é a leitura de checkout e o ingresso-objeto.**
  A 008 entregou resumo + formulário. Esta feature exige que isso se leia como compra de cinema e
  que o ingresso emitido nessa tela deixe de parecer um cartão genérico.

- **Portaria, meus ingressos e a página pública não são recompostos aqui.** Receberiam o mesmo
  cartão de ingresso se fossem incluídos, e isso misturaria três superfícies numa feature de três
  telas. O cartão da 008/009 permanece lá até uma feature que as unifique.

- **A paleta da 011 é premissa, não entregável.** Nenhum token de cor novo. Se a composição
  precisar de um espaço ou um raio que ainda não existe, ele nasce em token — disciplina da 006.

### Escopo excluído

Catálogo (home, carrossel, trilhas, busca) · seed e sincronização · contratos de destaque e de
home · campos novos de filme · cabeçalho e marca · portaria · entrada · meus ingressos · página
pública compartilhada · regras de reserva, pagamento, emissão e validação · fundo do QR · tema
claro · biblioteca de componentes pronta.

### Dependências

- Identidade de marca e disciplina de tokens (`011-marca-sem-laranja`, `006-visual-identity`)
- Página do filme e sessões (`001-movie-highlights-carousel`)
- Trailer já persistido (`001-movie-highlights-carousel`)
- Mapa de assentos e reserva (`007-seat-selection`)
- Pagamento e emissão (`008-payment-ticket-issuance`)
