# Feature Specification: Identidade Visual — Anti AI-Slop

**Feature Branch**: `main` (o projeto trabalha sem branches de feature)

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Refine a identidade visual da plataforma de ingressos para cumprir o Princípio V (Interface Autoral / Anti AI-Slop), sem mudar o comportamento funcional já entregue pelas features 001–005."

> **Nenhum comportamento muda.** Esta feature não toca endpoint, migração, contrato de API, regra
> de trilha, seed nem limite do carrossel. A estrutura da home permanece: destaques na primeira
> dobra, trilhas abaixo. O que muda é **a linguagem visual** — tipografia, ritmo, microdetalhe.
>
> **Fronteira com a feature 005**: a 005 decidiu **qual conteúdo** aparece na vitrine. Esta decide
> **como ele se parece**. Nenhuma das duas invade a outra.

## User Scenarios & Testing *(mandatory)*

> A ordem das quatro histórias é **mandatória** e foi definida pelo usuário: ritmo → tipografia →
> movimento → checagem. As prioridades abaixo refletem essa sequência, não apenas valor isolado.

### User Story 1 - Ler a home com ritmo, não com uniformidade (Priority: P1)

O visitante desce a home e percebe uma hierarquia clara: o painel de destaques domina a primeira
dobra, e as trilhas abaixo se organizam em seções com respiro entre elas. Ele sabe onde uma seção
termina e outra começa sem precisar ler os títulos.

**Why this priority**: É a base sobre a qual tipografia e movimento se apoiam. Ajustar fonte numa
página sem ritmo não resolve — só troca o tipo do problema.

**Independent Test**: Abrir a home e confirmar que o espaçamento entre o carrossel e a primeira
trilha é visivelmente maior que o espaçamento entre trilhas, e que os títulos de seção têm peso
distinto do corpo de texto.

**Acceptance Scenarios**:

1. **Given** a home carregada, **When** o visitante rola da primeira dobra para as trilhas,
   **Then** há uma separação vertical deliberada entre o painel de destaques e a primeira trilha,
   maior que a separação entre trilhas consecutivas.
2. **Given** as trilhas exibidas, **When** o visitante as percorre, **Then** os títulos de seção
   se distinguem do restante por peso e escala, não por cor isolada.
3. **Given** a home em qualquer largura de 360px a 1920px, **When** exibida, **Then** o ritmo
   vertical se mantém proporcional, sem seções coladas nem buracos.
4. **Given** os cartazes das trilhas, **When** exibidos, **Then** mantêm proporção e densidade
   consistentes entre si e coerentes com a escala do painel de destaques.
5. **Given** as setas de navegação das trilhas, **When** visíveis, **Then** têm tratamento visual
   integrado à seção — a regra de **quando** aparecem não muda.
6. **Given** a primeira dobra, **When** exibida, **Then** não há cartão decorativo, chip, selo de
   promoção nem sobreposição além do véu que garante contraste.

---

### User Story 2 - Reconhecer a marca pela tipografia (Priority: P2)

O visitante encontra uma tipografia com personalidade de cinema — não a fonte do sistema
operacional que qualquer aplicação usa. O título do filme em destaque tem presença de cartaz.

**Why this priority**: É a mudança de maior impacto visual por unidade de esforço, e a que mais
afasta a interface do genérico. Depende do ritmo da US1 estar definido para calibrar as escalas.

**Independent Test**: Abrir a home e confirmar que nenhum texto é renderizado com fonte do
sistema, e que o título do destaque e o corpo de texto pertencem a famílias com relação
tipográfica deliberada.

**Acceptance Scenarios**:

1. **Given** qualquer tela do produto, **When** exibida, **Then** todo texto usa a tipografia
   definida nos tokens, e nenhum recai na fonte padrão do sistema.
2. **Given** o painel de destaques, **When** exibido, **Then** o título do filme usa o tratamento
   de display, distinto do corpo de texto em escala e em largura de caractere.
3. **Given** a página carregando, **When** as fontes ainda não chegaram, **Then** o texto
   permanece legível e o layout não salta quando elas chegam.
4. **Given** qualquer componente, **When** inspecionado, **Then** nenhuma família tipográfica é
   declarada fora dos tokens.
5. **Given** a tipografia escolhida, **When** o projeto é entregue, **Then** sua licença permite
   uso comercial e está registrada na documentação, junto com o motivo da escolha.

---

### User Story 3 - Perceber que a interface responde (Priority: P3)

Ao passar o ponteiro sobre um cartaz, ao trocar de painel no carrossel ou ao deslizar uma trilha,
o visitante percebe uma resposta suave e curta. O movimento existe para dar retorno, não para
chamar atenção.

**Why this priority**: É polimento. Entrega valor real, mas uma home com ritmo e tipografia boas
já cumpre o Princípio V sem ele.

**Independent Test**: Percorrer cartaz, carrossel e trilha confirmando resposta visível em cada
um; ativar preferência por movimento reduzido e confirmar que todos cessam.

**Acceptance Scenarios**:

1. **Given** o ponteiro sobre um cartaz, **When** entra e sai, **Then** há resposta visual suave
   na entrada e na saída, sem salto.
2. **Given** o carrossel trocando de painel, **When** a transição ocorre, **Then** ela é contínua
   e não deixa rastro de conteúdo anterior.
3. **Given** uma trilha sendo deslocada, **When** o visitante aciona a seta, **Then** o movimento
   é suave e para de forma previsível.
4. **Given** o visitante configurou preferência por movimento reduzido, **When** interage com
   qualquer um dos três, **Then** o resultado é imediato, sem animação.
5. **Given** qualquer estado de carregamento, vazio, erro ou cartaz ausente, **When** exibido,
   **Then** parece pertencer a este produto — nunca um retângulo cinza genérico.
6. **Given** o produto inteiro, **When** auditado, **Then** existem no máximo **três** gestos de
   movimento distintos.

---

### User Story 4 - Reconhecer o produto sem o logo (Priority: P4)

Alguém vê uma captura da primeira dobra com o cabeçalho recortado. Ainda assim identifica que é
**este** produto: sala escura, laranja de projeção, tipografia de cartaz. Não confunde com
qualquer catálogo de streaming.

**Why this priority**: É a checagem final, não uma etapa de construção. Só faz sentido depois que
as três anteriores existem.

**Independent Test**: Capturar a primeira dobra, recortar cabeçalho e logotipo, e submeter aos
critérios escritos de revisão — a captura precisa ser atribuível a esta marca.

**Acceptance Scenarios**:

1. **Given** uma captura da primeira dobra sem cabeçalho nem logotipo, **When** avaliada, **Then**
   a paleta de sala escura com destaque laranja está evidente.
2. **Given** a mesma captura, **When** avaliada, **Then** o tratamento tipográfico é reconhecível
   como escolha, não como padrão de framework.
3. **Given** a paleta entregue, **When** comparada à baseline, **Then** permanece escura com
   destaque laranja — sem roxo, sem creme com serifada terracota, sem brilho excessivo.
4. **Given** qualquer superfície do produto, **When** revisada, **Then** não há texto de
   preenchimento, marcador de posição nem seção "em breve".
5. **Given** decisões visuais não óbvias, **When** a feature é entregue, **Then** estão
   registradas na documentação com o motivo.

---

### Edge Cases

- **Fonte não carrega**: o texto permanece legível com a pilha de reserva e o layout não salta.
- **Título de filme muito longo**: o tratamento de display continua legível e não estoura o
  painel nem invade os botões.
- **Título muito curto**: não fica perdido num espaço dimensionado para títulos longos.
- **Tela estreita (360px)**: a escala de display reduz proporcionalmente; o ritmo vertical não
  colapsa em seções coladas.
- **Tela larga (1920px)**: o conteúdo não estica indefinidamente; a medida de leitura permanece
  confortável.
- **Movimento reduzido ativado no meio da sessão**: os gestos cessam a partir dali, sem exigir
  recarga.
- **Cartaz ausente**: o substituto é reconhecível como parte do produto, com o título legível.
- **Trilha com poucos itens**: alinha à esquerda sem esticar cartazes nem deixar buraco.
- **Contraste sobre arte muito clara**: o véu continua garantindo legibilidade do texto e dos
  botões.

## Requirements *(mandatory)*

### Ritmo e hierarquia (US1)

- **FR-001**: A separação vertical entre o painel de destaques e a primeira trilha DEVE ser maior
  que a separação entre trilhas consecutivas, e ambas DEVEM vir de tokens.
- **FR-002**: Os títulos de seção DEVEM se distinguir do corpo de texto por peso e escala, não
  apenas por cor.
- **FR-003**: Os cartazes DEVEM manter proporção e densidade consistentes entre trilhas.
- **FR-004**: As setas de navegação DEVEM ter tratamento visual coerente com a seção. A regra de
  **quando** aparecem NÃO muda.
- **FR-005**: A primeira dobra NÃO PODE conter cartão decorativo, chip, selo de promoção nem
  sobreposição além do véu de contraste.
- **FR-006**: O ritmo vertical DEVE se manter proporcional de 360px a 1920px.

### Tipografia (US2)

- **FR-007**: A tipografia DEVE ter personalidade editorial de cinema, substituindo a pilha de
  fontes do sistema.
- **FR-008**: DEVE haver distinção deliberada entre o tratamento de display e o de texto.
- **FR-009**: Toda declaração de família tipográfica DEVE vir dos tokens; nenhuma pode ser
  declarada dentro de componente.
- **FR-010**: As fontes DEVEM ser servidas pelo próprio produto, sem depender de terceiro em
  tempo de visita.
- **FR-011**: O carregamento das fontes NÃO PODE provocar salto de layout nem texto invisível.
- **FR-012**: A licença da tipografia DEVE permitir uso comercial e estar registrada na
  documentação, com o motivo da escolha e por que não a fonte do sistema.

### Movimento (US3)

- **FR-013**: DEVE haver resposta visual ao ponteiro sobre o cartaz, na entrada e na saída.
- **FR-014**: A transição do carrossel e o deslocamento das trilhas DEVEM ser suaves e previsíveis.
- **FR-015**: O produto inteiro NÃO PODE ter mais de **três** gestos de movimento distintos.
- **FR-016**: Todo movimento DEVE cessar sob preferência por movimento reduzido, e a mudança de
  preferência DEVE valer sem recarga.
- **FR-017**: O movimento NÃO PODE causar engasgo perceptível durante a rolagem.
- **FR-018**: Estados de carregamento, vazio, erro e cartaz ausente DEVEM parecer parte do
  produto, não retângulo genérico.

### Identidade (US4)

- **FR-019**: A primeira dobra sem cabeçalho e sem logotipo DEVE permanecer atribuível a esta
  marca.
- **FR-020**: A paleta DEVE permanecer escura com destaque laranja. Roxo, creme com serifada
  terracota e brilho excessivo estão vetados.
- **FR-021**: Nenhuma superfície pode conter texto de preenchimento, marcador de posição ou seção
  "em breve".
- **FR-022**: Decisões visuais não óbvias DEVEM ser registradas com o motivo (Princípio VI).

### Disciplina de tokens

- **FR-023**: Nenhum valor de cor, espaçamento, escala tipográfica, raio ou duração pode ser
  declarado fora dos tokens.
- **FR-024**: Os valores soltos que já existem DEVEM ser migrados para tokens — há hoje ao menos
  uma cor literal repetida em dois arquivos.
- **FR-025**: Os tokens DEVEM ser estendidos, não substituídos: nomes existentes permanecem
  válidos para não quebrar o que já os consome.

### O que NÃO pode mudar

- **FR-026**: Nenhum contrato de API, endpoint, migração ou regra de trilha pode ser alterado.
- **FR-027**: A estrutura da home permanece: destaques na primeira dobra, trilhas abaixo.
- **FR-028**: A acessibilidade já entregue DEVE ser preservada: operação por teclado, foco
  visível, semântica das regiões e contraste do texto sobre o véu.
- **FR-029**: Nenhuma biblioteca de interface gerada ou de efeitos prontos pode ser adotada.
- **FR-030**: Todo o comportamento coberto pelos testes existentes DEVE continuar passando sem
  alteração de asserção.

## Success Criteria *(mandatory)*

- **SC-001**: Zero valores de cor, espaçamento, escala tipográfica, raio ou duração declarados
  fora dos tokens — verificável por varredura nos arquivos de estilo dos componentes.
- **SC-002**: Zero declarações de família tipográfica fora dos tokens.
- **SC-003**: A primeira dobra sem cabeçalho e sem logotipo é atribuída a esta marca por quem
  aplica os critérios escritos de revisão.
- **SC-004**: O produto tem no máximo 3 gestos de movimento distintos, contáveis na documentação.
- **SC-005**: Com preferência por movimento reduzido ativa, nenhum dos gestos ocorre.
- **SC-006**: O deslocamento de layout ao carregar as fontes é imperceptível — o conteúdo não
  muda de posição depois da primeira exibição.
- **SC-007**: O contraste do texto e dos botões sobre o véu permanece em nível legível, igual ou
  melhor que a baseline.
- **SC-008**: Os testes de front-end existentes continuam passando sem alteração de asserção.
- **SC-009**: A licença da tipografia está registrada na documentação e permite uso comercial.
- **SC-010**: Nenhuma superfície contém texto de preenchimento, marcador de posição ou "em breve".
- **SC-011**: A página permanece sem rolagem horizontal de 360px a 1920px.

## Assumptions

- **Tipografia: Archivo Expanded (display) + Archivo (texto)** — decisão do usuário em
  2026-08-11, escolhida entre três direções apresentadas. Licença **SIL Open Font License**, que
  permite uso comercial, modificação e redistribuição embutida. Superfamília única dá coerência
  entre display e texto sem precisar casar duas vozes; o corte expandido no display evoca cartaz
  de mostra de cinema, o que afasta do genérico de streaming.

  A alternativa Fontshare (Clash Display + Satoshi) foi apresentada e descartada pelo usuário: a
  ITF Free Font License permite uso comercial e self-hosting, mas a OFL é mais inequívoca num
  repositório público avaliado por terceiros.

- **"Três gestos de movimento" são categorias, não instâncias** — hover do cartaz, transição do
  carrossel e deslocamento da trilha contam como três, ainda que cada um apareça em vários
  lugares. O teto existe para impedir acúmulo de efeitos, não para proibir reuso.

- **A checagem anti-slop é revisão humana com critérios escritos** — não existe teste automático
  para "parece autoral". O que se pode automatizar é o objetivo: ausência de valores soltos,
  paleta preservada, ausência de texto de preenchimento. O julgamento final é do revisor,
  aplicando os critérios registrados.

- **As referências citadas orientam ritmo, não estrutura** — Mobbin e Supahero servem para
  calibrar espaçamento e hierarquia; Godly e Awwwards, como critério de revisão. Nenhuma layout
  nova é copiada.

- **Há um débito de token já existente** — a cor `#150703`, usada como texto sobre o botão
  laranja, aparece literal em dois arquivos. Foi encontrada na auditoria antes desta redação e
  entra no escopo por FR-024.

### Escopo excluído

Redesenho do fluxo de compra, da página do filme, do cabeçalho ou da tela de entrada além do que
a disciplina de tokens exigir. Alteração de paleta, de seed, do limite do carrossel ou das regras
Em cartaz / Em alta / Em breve. Modo claro. Ilustração ou identidade de marca além da tipografia
e do uso da paleta existente.

### Dependências

Todas as features anteriores (`001` a `005`) entregues — esta refina o que existe. Nenhuma
dependência externa nova em tempo de visita: as fontes são servidas pelo próprio produto.
