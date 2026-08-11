# Feature Specification: Ajuste da Vitrine — Seed e Carrossel

**Feature Branch**: `main` (o projeto trabalha sem branches de feature)

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "aumente o seed, adicione sessoes nos filmes "homem aranha", "a odisseia", "minions" e "moana". abaixe o carrosel para apenas 3 filmes ( a odisseia, homem aranha e minions )"

> **Esta feature emenda a `001-movie-highlights-carousel`** (o limite do carrossel, hoje 5) e o
> comando de seed, que nasceu na 001 e foi ajustado pela 004. Não há tela nova nem endpoint novo:
> o que muda é **quantos** filmes o carrossel mostra e **quais** filmes a demonstração coloca à
> venda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encontrar uma vitrine reconhecível ao abrir o site (Priority: P1)

Quem abre a home — em especial quem vai avaliar o projeto — vê no topo um carrossel com **três**
filmes de cinema conhecidos, e logo abaixo trilhas com catálogo suficiente para não parecerem
vazias. A primeira impressão é de um cinema de verdade, não de um banco de dados de demonstração.

**Why this priority**: É a primeira tela do produto e a primeira coisa que um avaliador vê. Hoje o
carrossel exibe cinco filmes escolhidos por data de lançamento, e o resultado inclui títulos que
ninguém associa a uma sala de cinema. O Princípio V da constitution cobra que a interface
demonstre escolha — e uma vitrine é exatamente onde isso aparece.

**Independent Test**: Rodar a sincronização e o seed em ambiente limpo, abrir a home e confirmar
que o carrossel exibe exatamente três filmes, sendo eles A Odisseia, Homem-Aranha e Minions.

**Acceptance Scenarios**:

1. **Given** o catálogo sincronizado e o seed aplicado, **When** o visitante abre a home,
   **Then** o carrossel exibe **três** filmes, não mais.
2. **Given** o carrossel exibe três filmes, **When** o visitante os percorre, **Then** vê
   A Odisseia, Homem-Aranha e Minions.
3. **Given** o carrossel tem três filmes, **When** o visitante avança a partir do terceiro,
   **Then** volta ao primeiro — a navegação circular continua valendo.
4. **Given** menos de três filmes têm sessão à venda, **When** a home é carregada, **Then** o
   carrossel exibe quantos existirem, sem espaço vazio nem painel em branco.
5. **Given** nenhum filme tem sessão à venda, **When** a home é carregada, **Then** vale o estado
   vazio que já existe.

---

### User Story 2 - Percorrer o fluxo de compra com filmes de verdade (Priority: P1)

O avaliador entra com uma das contas semeadas e encontra sessões à venda para filmes que
reconhece — incluindo **Moana**, que tem sessão mas não ocupa o carrossel. As trilhas da home têm
catálogo suficiente para que Em cartaz e Em alta não fiquem quase idênticas.

**Why this priority**: É o que o desafio exige explicitamente — cenário semeado para percorrer o
fluxo sem montar nada. Compartilha P1 com a US1 porque as duas juntas formam a vitrine.

**Independent Test**: Aplicar o seed e confirmar que os quatro filmes nomeados têm sessão
publicada e futura, e que a trilha Em cartaz lista mais filmes do que o carrossel exibe.

**Acceptance Scenarios**:

1. **Given** o seed aplicado, **When** a trilha Em cartaz é exibida, **Then** ela inclui
   A Odisseia, Homem-Aranha, Minions e **Moana**.
2. **Given** Moana tem sessão publicada, **When** a home é carregada, **Then** ela aparece em Em
   cartaz mas **não** no carrossel.
3. **Given** o seed aplicado, **When** a trilha Em cartaz é exibida, **Then** ela lista mais
   filmes do que os três do carrossel — a trilha e o destaque não são a mesma lista.
4. **Given** um dos filmes nomeados não existe no catálogo, **When** o seed roda, **Then** ele
   informa quais não foram encontrados e conclui com os demais, sem falhar.
5. **Given** o seed roda duas vezes seguidas, **When** a segunda execução termina, **Then** o
   resultado é idêntico ao da primeira — nenhuma sessão duplicada.

---

### Edge Cases

- **Filme nomeado ausente do catálogo**: o seed avisa quais faltaram e segue com os que existem.
  Não pode falhar nem deixar o banco pela metade.
- **Título divergente do esperado**: o catálogo externo pode renomear um filme. A busca precisa
  tolerar diferença de acento, caixa e sufixo de título.
- **Mais de um filme casando com o mesmo nome**: o seed escolhe um de forma determinística e
  informa qual, para que duas execuções não produzam vitrines diferentes.
- **Filme nomeado sem cartaz ou sem arte**: entra assim mesmo; os estados de imagem ausente já
  existem e são exercitados.
- **Menos de três filmes com sessão**: o carrossel exibe quantos houver.
- **Carrossel com um único filme**: os controles de navegação e a rotação automática não são
  apresentados — comportamento que já existe.

## Requirements *(mandatory)*

### Carrossel

- **FR-001**: O carrossel da home DEVE exibir no máximo **3** filmes, substituindo o limite
  anterior de 5.
- **FR-002**: A regra de elegibilidade do carrossel NÃO muda: apenas filmes com ao menos uma
  sessão publicada e futura, ordenados pela sessão mais próxima.
- **FR-003**: Todo comportamento já entregue do carrossel — navegação circular, rotação
  automática e suas pausas, trailer no painel, estados de carregamento, vazio e erro — DEVE
  continuar valendo com três filmes.

### Cenário de demonstração

- **FR-004**: O seed DEVE criar sessões publicadas e futuras para **A Odisseia**,
  **Homem-Aranha**, **Minions** e **Moana**.
- **FR-005**: O seed DEVE agendar as sessões de forma que **A Odisseia, Homem-Aranha e Minions**
  sejam os três filmes com sessão mais próxima, e portanto os ocupantes do carrossel.
- **FR-006**: **Moana** DEVE ter sessão publicada e futura, mas não pode estar entre as três mais
  próximas.
- **FR-007**: O seed DEVE colocar à venda **mais** filmes do que os quatro nomeados, para que a
  trilha Em cartaz tenha conteúdo além do carrossel.
- **FR-008**: Os filmes não nomeados DEVEM ser escolhidos pelo critério que já existe — longa
  com arte, preferindo os já lançados.
- **FR-009**: O seed DEVE continuar criando o organizador, os dois clientes e o usuário de
  portaria, com as credenciais publicadas no README.

### Robustez do seed

- **FR-010**: A busca pelos filmes nomeados DEVE tolerar diferença de acento, de caixa e de
  sufixo de título.
- **FR-011**: Quando um filme nomeado não for encontrado, o seed DEVE informar qual faltou e
  concluir com os demais, sem interromper a execução.
- **FR-012**: Quando mais de um filme casar com o mesmo nome, o seed DEVE escolher um de forma
  determinística e informar qual escolheu.
- **FR-013**: O seed DEVE continuar sendo idempotente: duas execuções seguidas produzem o mesmo
  resultado, sem sessão duplicada.
- **FR-014**: A saída do seed DEVE indicar quais filmes ficaram no carrossel e quais entraram
  apenas na trilha, para que a vitrine seja conferível sem abrir o navegador.

## Success Criteria *(mandatory)*

- **SC-001**: O carrossel da home exibe exatamente 3 filmes quando há 3 ou mais com sessão à
  venda.
- **SC-002**: Após sincronizar e semear em ambiente limpo, os três filmes do carrossel são
  A Odisseia, Homem-Aranha e Minions — verificável sem abrir o navegador, pela saída do seed.
- **SC-003**: Moana aparece na trilha Em cartaz e não aparece no carrossel.
- **SC-004**: A trilha Em cartaz lista ao menos o dobro de filmes do que o carrossel exibe.
- **SC-005**: Duas execuções seguidas do seed produzem exatamente a mesma vitrine.
- **SC-006**: Com um filme nomeado ausente do catálogo, o seed conclui sem erro e informa a
  ausência.

## Assumptions

- **"Aumente o seed" = mais filmes com sessão** — o pedido não deu número. Assume-se **cerca de
  12** filmes com sessão publicada, contra os 5 de hoje. É o suficiente para a trilha Em cartaz
  ter substância, para a trilha Em alta deixar de ser quase idêntica a ela, e para o carrossel de
  3 ser claramente um recorte, não a lista inteira. Valor exato a definir no plano.

- **Os nomes são fragmentos, não títulos exatos** — o pedido cita "homem aranha", "a odisseia",
  "minions" e "moana"; o catálogo tem *Homem-Aranha: Um Novo Dia*, *A Odisseia*,
  *Minions & Monstros* e *Moana*. Confirmado no catálogo antes desta redação: os quatro existem,
  com cartaz e arte.

- **Fixar filmes por nome é frágil, e a fragilidade é assumida** — o catálogo externo pode
  renomear ou parar de listar um filme. Por isso FR-011 exige degradação graciosa em vez de falha:
  um seed que quebra porque um título mudou é pior do que uma vitrine com um filme a menos.

- **O limite de 3 é regra de produto, não coincidência do seed** — o carrossel passa a exibir no
  máximo 3 em qualquer catálogo, não apenas no cenário semeado.

- **Moana fora do carrossel decorre da ordenação** — não há lista fixa no produto. O carrossel
  continua sendo "os N com sessão mais próxima"; o seed é que agenda A Odisseia, Homem-Aranha e
  Minions antes de Moana. Nenhuma lógica de curadoria entra no código de produto.

### Escopo excluído

Curadoria manual de destaque pelo organizador, campo de "filme fixado", alteração das trilhas
Em alta e Em breve, e qualquer mudança no comportamento do carrossel além do limite.

### Dependências

- Carrossel e seed (`001-movie-highlights-carousel`)
- Trilhas da home (`004-home-movie-rows`), que consomem o mesmo seed
- Catálogo sincronizado do TMDb — os filmes nomeados precisam ter sido importados
