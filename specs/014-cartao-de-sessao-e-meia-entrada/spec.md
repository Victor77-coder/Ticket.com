# Feature Specification: Cartão de Sessão e Meia-Entrada

**Feature Branch**: `main` — sem branch própria, como nas 003–013

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "use este visual de cards de sessões com o botão de assentos (modal que
mostra os assentos disponíveis e ocupados) e botão de preços (que mostra os valores (inteira e
meia))" — acompanhado de captura de tela do ingresso.com.

> **Esta feature tem duas metades de custo muito diferente, e vale dizer isso na primeira linha.**
>
> A primeira é **apresentação**: o cartão de sessão ganha cabeçalho, duas ações no topo e dois
> modais de leitura. Não toca em regra de negócio nenhuma e consome dados que a API já entrega.
>
> A segunda é **meia-entrada comprável**, decidida pelo autor em 2026-08-13 depois de ver o custo
> das duas opções. Ela **abre o cálculo do total**, que hoje é do servidor e está protegido por
> teste de concorrência (`test_payment_concurrency.py`). É a primeira feature desde a 008 a mexer
> no que se cobra.
>
> **A ordem de entrega não é sugestão.** A primeira metade é entregável sozinha e é o que o autor
> pediu olhando a imagem. A segunda depende dela apenas para ter onde exibir a tabela de preços —
> mas não o contrário. Se o prazo apertar, a P1 e a P2 sozinhas fecham o pedido visual.
>
> **Nada do fluxo fechado é reaberto.** Reservar continua sendo `UNIQUE(sessão, assento)`; pagar
> continua sendo o bloqueio seguido de revalidação; a portaria continua com **exatamente quatro
> desfechos**. A meia-entrada muda o **valor** de um assento, nunca o **direito** a ele.

## O que permanece e o que esta feature mexe

| Superfície | Nesta feature |
|---|---|
| Home, carrossel, trilhas, busca | **Intocadas** |
| Página do filme — grade de horários | **Recomposta** em cartão por sala, com duas ações |
| Mapa de assentos (seleção real, 007/012) | **Ganha o tipo de ingresso por lugar**; a seleção em si não muda |
| Pagamento | **Total passa a somar tipos diferentes**; garantias e desfechos inalterados |
| Ingresso emitido, "Meus ingressos", link público | **Passam a exibir o tipo**; nenhuma outra mudança |
| Portaria — os quatro desfechos | **Intocada.** Ver FR-024 |
| Painel do organizador (013) | **Intocado.** O organizador continua definindo um preço por sessão |
| Catálogo, seed, TMDb, autenticação | **Intocados** |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ler a sessão num cartão, não numa lista (Priority: P1)

A pessoa abre um filme e vê as sessões agrupadas em **cartões por sala**. Cada cartão tem um
cabeçalho que diz de qual sala se trata, uma régua que o separa dos horários, e os horários como
alvos compactos abaixo. No topo do cartão, à direita, duas ações: **Assentos** e **Preços**.

**Why this priority**: É o que o autor pediu ao mandar a imagem. Entrega sozinha, sem depender de
nenhuma outra história, e é a única metade da feature que não toca em dinheiro.

**Independent Test**: Abrir um filme com sessões em duas salas e confirmar que cada sala é um
cartão com cabeçalho próprio, horários agrupados dentro dele e as duas ações no topo.

**Acceptance Scenarios**:

1. **Given** um filme com sessões em duas salas no mesmo dia, **When** a página abre, **Then** a
   pessoa vê dois cartões, cada um identificado pela sala, com os horários daquela sala dentro.
2. **Given** um cartão de sessão, **When** a pessoa olha o topo dele, **Then** vê as ações
   **Assentos** e **Preços**, cada uma com rótulo em texto além do ícone.
3. **Given** um horário esgotado, **When** ele é exibido no cartão, **Then** continua distinguível
   de um horário disponível sem depender só de cor, como já era antes desta feature.
4. **Given** um horário disponível, **When** a pessoa o aciona, **Then** chega ao mapa de assentos
   daquela sessão — o mesmo destino de antes.

---

### User Story 2 - Espiar a lotação antes de escolher o horário (Priority: P2)

A pessoa está decidindo entre dois horários e quer saber qual está mais vazio. Aciona **Assentos**
e vê, em um painel sobreposto, o desenho da sala com os lugares **livres** e **ocupados**, quantos
lugares ainda restam, e um caminho direto para escolher de verdade.

**Why this priority**: É metade do pedido explícito da imagem, e é a informação que faz a pessoa
trocar de horário — o valor está em decidir **antes** de entrar no mapa.

**Independent Test**: Abrir o painel a partir de um horário com lugares vendidos e conferir que os
lugares ocupados aparecem como ocupados e a contagem de livres bate com o mapa real.

**Acceptance Scenarios**:

1. **Given** uma sessão com lugares vendidos, **When** a pessoa aciona **Assentos** naquele
   horário, **Then** vê o desenho da sala com livres e ocupados distinguíveis sem depender só de
   cor, e a quantidade de lugares livres.
2. **Given** o painel aberto, **When** a pessoa aciona "Escolher lugares", **Then** vai ao mapa de
   assentos daquela sessão, onde a seleção acontece.
3. **Given** o painel aberto, **When** a pessoa pressiona `Esc` ou aciona fechar, **Then** o painel
   fecha e o foco volta para a ação que o abriu.
4. **Given** uma sessão esgotada, **When** o painel é aberto, **Then** ele diz que não há lugares e
   **não** oferece o caminho para escolher.
5. **Given** falha ao buscar a ocupação, **When** o painel é aberto, **Then** ele exibe mensagem em
   português dizendo o que houve e como seguir, nunca um painel vazio sem explicação.

---

### User Story 3 - Saber quanto custa antes de entrar no mapa (Priority: P2)

A pessoa aciona **Preços** e vê a tabela daquela sessão: **inteira** e **meia**, com os valores, e
uma frase curta dizendo que a meia é conferida na entrada mediante documento.

**Why this priority**: É a outra metade do pedido da imagem, e sozinha já resolve a exigência do
desafio de preço visível na navegação. Não depende da história 4 para existir.

**Independent Test**: Abrir o painel de preços numa sessão e conferir que os dois valores exibidos
correspondem ao preço daquela sessão e à sua metade.

**Acceptance Scenarios**:

1. **Given** uma sessão de R$ 32,00, **When** a pessoa aciona **Preços**, **Then** vê "Inteira
   R$ 32,00" e "Meia R$ 16,00".
2. **Given** duas sessões do mesmo filme com preços diferentes, **When** a pessoa abre a tabela de
   cada uma, **Then** cada tabela mostra o preço da **sua** sessão.
3. **Given** o painel de preços aberto, **When** a pessoa o fecha, **Then** o foco volta para a
   ação que o abriu.

---

### User Story 4 - Comprar meia-entrada (Priority: P3)

Ao escolher os lugares, a pessoa define, **para cada lugar**, se é inteira ou meia. O total é
recalculado e exibido. Ela paga esse total, e cada ingresso emitido carrega o seu tipo.

**Why this priority**: É a história mais cara e a única que toca o que se cobra. Fica por último de
propósito: as três anteriores entregam o pedido visual completo sem ela, e um corte de escopo aqui
não deixa tela pela metade — deixa a plataforma como está hoje, vendendo tudo como inteira.

**Independent Test**: Reservar dois lugares, marcar um como meia, e conferir que o total cobrado é
inteira + metade, e que os dois ingressos emitidos declaram tipos diferentes.

**Acceptance Scenarios**:

1. **Given** dois lugares selecionados numa sessão de R$ 32,00, **When** a pessoa marca um deles
   como meia, **Then** o total exibido passa a ser R$ 48,00.
2. **Given** uma seleção com tipos definidos, **When** a reserva é criada, **Then** o total que o
   servidor calcula é o que a pessoa vê na tela de pagamento — a tela nunca decide o valor.
3. **Given** o pagamento aprovado de uma reserva com tipos mistos, **When** os ingressos são
   emitidos, **Then** cada ingresso declara o seu tipo, e o tipo aparece em "Meus ingressos".
4. **Given** uma pessoa que não mexe em nada, **When** ela conclui a compra, **Then** todos os
   lugares são inteira — o padrão nunca cobra menos por omissão.
5. **Given** um ingresso de meia, **When** ele é validado na portaria, **Then** o desfecho é um dos
   **quatro já existentes**; o tipo aparece como informação para o operador conferir o documento,
   e **não** cria um quinto desfecho.

---

### Edge Cases

- **A sessão esgota enquanto o painel de assentos está aberto.** O painel mostra o retrato do
  momento em que abriu. Ele não se atualiza sozinho, e a verdade continua sendo a reserva: quem
  seguir para o mapa e tentar um lugar já vendido recebe a recusa que a 007 já dá.
- **A pessoa abre o painel de assentos de uma sessão que acabou de ser cancelada pelo organizador.**
  A sessão cancelada some da grade na próxima carga; o painel aberto sobre um horário que não vende
  mais leva ao mapa, que já trata sessão não vendável.
- **Preço com centavos ímpares.** Metade de R$ 25,01 não é exata em centavos. O arredondamento
  precisa de regra definida e visível — ver FR-018.
- **Tudo meia.** Nada impede uma reserva inteira de meias. É assim no cinema de verdade: o sistema
  vende, a porta confere o documento. Ver FR-024 e a seção de Assumptions.
- **O organizador muda o preço depois da reserva.** Não acontece: a 013 não deixa editar sessão
  publicada — o caminho é cancelar e programar outra.
- **Sala sem lugares.** O painel de assentos precisa dizer isso em vez de desenhar uma sala vazia
  sem explicação.
- **Sessão cujo cartão não tem nenhum horário disponível.** O cartão continua legível, com todos os
  horários esgotados, em vez de sumir e deixar a sala parecer inexistente.

## Requirements *(mandatory)*

### Functional Requirements

#### O cartão de sessão

- **FR-001**: A grade de horários da página do filme DEVE ser apresentada como **um cartão por
  sala**, dentro do dia ativo, com o nome da sala como cabeçalho do cartão.
- **FR-002**: Cada cartão DEVE oferecer, no topo, as ações **Assentos** e **Preços**, ambas com
  rótulo em texto — ícone sozinho não identifica ação.
- **FR-003**: O cartão DEVE manter o preço já exibido por horário e a distinção de horário esgotado
  sem depender só de cor.
- **FR-004**: Acionar um horário disponível DEVE continuar levando ao mapa de assentos da sessão,
  pelo mesmo nome acessível que o teste ponta a ponta da 007 já exige.
- **FR-005**: O cartão NÃO DEVE exibir nome de cinema, endereço, selo de áudio ("DUBLADO",
  "LEGENDADO") nem ação de favoritar. Ver Assumptions — a plataforma não tem esses dados, e inventá-los
  seria texto de placeholder, proibido pelo Princípio V.

#### O painel de assentos

- **FR-006**: A ação **Assentos** DEVE abrir um painel sobreposto exibindo a ocupação da sessão:
  lugares livres e ocupados, distinguíveis **sem depender só de cor**, e a quantidade de lugares
  livres.
- **FR-007**: O painel DEVE ser **somente leitura**. Selecionar lugar acontece no mapa da 007, e
  esta feature NÃO DEVE criar um segundo caminho de reserva.
- **FR-008**: O painel DEVE consumir a **mesma fonte de ocupação** que o mapa de assentos já
  consome. Uma segunda leitura de "quem está ocupando" é proibida — a regra tem dono, e ele já
  existe.
- **FR-009**: O painel DEVE oferecer caminho direto para o mapa da sessão, exceto quando a sessão
  estiver esgotada, caso em que DEVE dizer isso.
- **FR-010**: O painel DEVE ser fechável por `Esc` e por controle visível, DEVE prender o foco
  enquanto aberto e DEVE devolver o foco à ação que o abriu.
- **FR-011**: Enquanto a ocupação carrega, o painel DEVE comunicar espera; se a busca falhar, DEVE
  exibir mensagem em português dizendo o que houve e qual a próxima ação.

#### O painel de preços

- **FR-012**: A ação **Preços** DEVE abrir um painel exibindo, para aquela sessão, os valores de
  **inteira** e **meia**.
- **FR-013**: O painel DEVE declarar que a meia-entrada é conferida na entrada mediante documento.
- **FR-014**: O painel de preços DEVE obedecer às mesmas regras de fechamento e foco do FR-010.

#### Meia-entrada

- **FR-015**: Ao escolher lugares, a pessoa DEVE poder definir o **tipo de ingresso por lugar**,
  entre **inteira** e **meia**.
- **FR-016**: O tipo padrão de todo lugar DEVE ser **inteira**. Nenhum caminho pode resultar em
  cobrança menor por omissão.
- **FR-017**: O valor da meia DEVE ser **metade do preço da sessão**.
- **FR-018**: Quando a metade não for exata em centavos, o arredondamento DEVE ser **para baixo**, em
  favor de quem compra, e o valor exibido DEVE ser exatamente o valor cobrado.
- **FR-019**: O total DEVE ser calculado **no servidor**, a partir dos tipos gravados na reserva. O
  navegador exibe; nunca decide. Um total enviado pelo cliente DEVE ser ignorado.
- **FR-020**: O preço unitário e o tipo de cada lugar DEVEM ser gravados **na reserva**, no momento
  em que ela é criada, e o pagamento DEVE cobrar o que está gravado.
- **FR-021**: Cada ingresso emitido DEVE declarar o seu tipo, e o tipo DEVE aparecer em "Meus
  ingressos".
- **FR-022**: A escolha de tipo NÃO PODE alterar a garantia de assento único: as regras de reserva,
  expiração e pagamento permanecem exatamente as da 007 e da 008.
- **FR-023**: A página pública de ingresso compartilhado PODE exibir o tipo, por ser informação do
  ingresso e não do comprador — mas NÃO PODE ganhar nenhum outro campo. O teste de vazamento
  continua sendo o árbitro.

#### A fronteira da portaria

- **FR-024**: A validação na portaria DEVE continuar produzindo **exatamente quatro desfechos**. O
  tipo do ingresso DEVE ser exibido ao operador como informação de conferência, e NUNCA como um
  quinto desfecho nem como condição de entrada. A plataforma **vende** meia; quem **confere** o
  documento é a pessoa na porta.

### Key Entities

- **Sessão**: já existe. Mantém **um** preço, definido pelo organizador. A meia é derivada dele,
  não um segundo campo que o organizador precise preencher.
- **Lugar reservado**: passa a carregar **tipo de ingresso** (inteira ou meia) e o **valor cobrado
  por aquele lugar**. É a única extensão de modelo desta feature.
- **Ingresso**: passa a expor o tipo herdado do lugar reservado. Não ganha campo próprio de preço —
  o que foi cobrado pertence ao pagamento e à reserva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pessoa descobre quantos lugares restam em um horário **sem sair da página do
  filme** e em uma única interação.
- **SC-002**: A pessoa descobre o valor de inteira e de meia **sem sair da página do filme** e em
  uma única interação.
- **SC-003**: Livre e ocupado permanecem distinguíveis com a tela em escala de cinza — a mesma
  verificação que a 007 já aplica ao mapa.
- **SC-004**: Os dois painéis são abertos, percorridos e fechados **apenas pelo teclado**, com o
  foco voltando à ação de origem.
- **SC-005**: Em uma reserva de dois lugares com tipos diferentes, o total cobrado é igual à soma
  dos valores exibidos, verificada contra o valor que o servidor calculou.
- **SC-006**: Nenhuma compra resulta em valor menor que o de inteira sem que um tipo tenha sido
  escolhido explicitamente.
- **SC-007**: A corrida de duas compras simultâneas do mesmo assento continua tendo exatamente uma
  vencedora, com tipos de ingresso envolvidos.
- **SC-008**: A portaria continua entregando quatro desfechos, e um ingresso de meia entra pelo
  mesmo caminho de um de inteira.

## Assumptions

- **O cabeçalho do cartão é a sala, não um cinema.** A imagem de referência traz nome e endereço de
  uma unidade. Esta plataforma modela **um cinema**, e a sala é a menor unidade que distingue uma
  sessão de outra — é como a grade já agrupa desde a 012. Um campo de local só existe junto com o
  conceito de praça, registrado como pendência desde a 002.
- **Não há selo de áudio.** "DUBLADO"/"LEGENDADO" na imagem vem de dado que o TMDb não fornece por
  sessão e que a plataforma não persiste. Exibir um selo fixo seria placeholder.
- **Não há favoritar.** O ícone de coração da imagem pertence a um recurso de conta que não existe
  aqui e que o desafio não pede.
- **A meia é 50% do preço**, conforme a prática consolidada no Brasil, e vale para qualquer pessoa
  que a selecione — o sistema não pergunta o motivo da meia (estudante, idoso, professor). Perguntar
  exigiria coletar e guardar categoria de documento, que é dado pessoal sem contrapartida nesta
  entrega.
- **A conferência do documento é humana e acontece na porta.** É assim no cinema real. A alternativa
  — impedir a venda de meia sem comprovação — exigiria upload e verificação de documento, muito além
  do escopo do desafio.
- **Não há cota de meia-entrada.** A lei brasileira limita a meia a 40% dos lugares. Implementar a
  cota exigiria uma regra de disponibilidade por tipo dentro da mesma sessão, com sua própria
  corrida e sua própria constraint — uma feature do tamanho da 007. Fica registrado como fora de
  escopo, e não como esquecimento.
- **O painel de assentos é um retrato, não uma transmissão.** Ocupação em tempo real é item
  separado na etapa 6 da constitution. Aqui, o painel mostra o estado do instante em que abriu.
- **A reserva congela o preço.** Como a 013 não permite editar sessão publicada, o preço não muda
  sob uma reserva viva. Gravar o valor cobrado por lugar (FR-020) é o que mantém isso verdadeiro
  mesmo se essa regra mudar depois.

## Dependências

- **007 — mapa de assentos**: fonte da ocupação consumida pelo painel (FR-008) e dona da seleção
  real (FR-007).
- **008 — pagamento e emissão**: dona do cálculo do total, que esta feature estende sem reabrir as
  garantias.
- **012 — telas de compra**: dona da grade por dia e sala que vira cartão na FR-001.
- **013 — painel do organizador**: dona do preço da sessão, do qual a meia é derivada.

## Fora de escopo

- Cota de 40% de meia-entrada.
- Categorias de meia (estudante, idoso, professor) e comprovação documental no sistema.
- Ocupação em tempo real nos painéis.
- Selo de áudio, favoritar sessão, nome e endereço de cinema.
- Preço diferenciado por assento (VIP, namoradeira) ou por dia da semana.
- Qualquer alteração nos quatro desfechos da portaria.
