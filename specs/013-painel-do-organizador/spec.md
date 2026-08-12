# Feature Specification: Painel do Organizador — Programar Filmes, Salas e Sessões

**Feature Branch**: `main` — sem branch própria, como nas 003–012

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Painel do organizador — programar filmes, salas e sessões. O papel
organizador autentica, mas não tem tela nenhuma. Objetivo: o organizador autenticado pousa numa
área de trabalho, busca filme no TMDb (pelo back-end), persiste localmente, define
sala/capacidade/preço/horário e publica a sessão."

> **Esta é a etapa 6 da constitution — a primeira depois do fluxo fechado.** As features 001–010
> fecharam catálogo → sessão → assento → pagamento → ingresso → portaria. A ordem obrigatória do
> "Fluxo de Desenvolvimento" libera o painel do organizador só agora, e é este.
>
> **O Princípio IV define o organizador como quem "cria e gerencia filmes, sessões, salas,
> capacidade e preços". Hoje isso só existe no `seed_demo`.** A conta `organizador` entra e cai no
> catálogo de quem compra. `CASA_DO_PAPEL` registra a ausência por escrito — *"`organizer` está
> AUSENTE de propósito... Quando o painel existir, ele entra aqui e as duas telas passam a
> conhecê-lo de graça."* Esta feature é o item que entra nessa tabela.
>
> **Nenhuma regra de negócio de compra é reaberta.** Reservar, pagar, emitir, compartilhar e
> validar continuam idênticos. O que muda é que a grade passa a ter uma origem além do seed.
>
> **A armadilha desta feature é a segunda regra.** O mapa físico da sala já é gerado a partir da
> capacidade — dentro do `seed_demo`. Escrever de novo essa regra no painel cria duas verdades sobre
> onde ficam os lugares de acessibilidade, e a segunda diverge da primeira na primeira correção. A
> regra é **extraída e reusada**, nunca copiada.

## O que já existe e NÃO é refeito

| Já existe | Nesta feature |
|---|---|
| Modelos `Movie`, `Room`, `Seat`, `Screening` (draft/published/cancelled) | **Reusados** — nenhum modelo novo é necessário |
| `UNIQUE(room, starts_at)` = `uma_sessao_por_sala_e_horario` | **É a garantia** do conflito de horário; o form não a substitui |
| Geração do mapa físico da sala a partir da capacidade | **Extraída** do `seed_demo` para ser chamada pelos dois |
| `TMDBClient` com timeout e `TMDBError` em pt-BR | **Reusado** e ganha busca por texto; a chave nunca sai do Django |
| Persistência local de título, pôster, duração, sinopse, trailer | **Reusada** — o caminho de compra não volta a depender do TMDb |
| `sellable()` = `published()` E `starts_at > now()` | **Intocado.** Responde só "dá para comprar?"; a portaria não usa |
| Comportamento de sessão cancelada em "Meus ingressos" (009) e na portaria (010) | **Intocado** |
| Home, carrossel, trilhas, busca, telas de compra da 012 | **Intocados** |

## Clarifications

### Session 2026-08-12

- Q: O que "gerenciar" cobre além de criar (a descrição da feature foi cortada neste ponto)? → A: Criar + publicar + cancelar + **editar rascunho**. Sessão publicada é imutável em filme, sala, horário e preço; cancelar vale tanto para rascunho quanto para publicada.
- Q: O que se persiste ao escolher um filme no TMDb, e ele fica público antes de ter sessão? → A: **Sincronização completa reusada** — o mesmo mapeamento que a sincronização de catálogo já faz, incluindo trailers, gêneros e classificação — e o filme **entra no catálogo público de imediato**. Sem sessão, a página dele usa o estado vazio que a 012 já entrega. Nenhuma regra de visibilidade nova; as marcas de trilha da home continuam falsas.
- Q: Sessões que se sobrepõem no tempo na mesma sala devem ser recusadas? → A: **Não.** A duração do filme não é modelada como bloqueio de sala; a garantia continua sendo horário de início idêntico. A recusa seria inaplicável a filme sem duração cadastrada, não é expressável como constraint — seria a primeira garantia deste projeto a viver só na aplicação — e "quanto tempo uma sala fica ocupada" é regra de negócio nova.
- Q: O cenário de demonstração deve destruir a programação feita pelo painel? → A: Não em silêncio. O comando **recusa rodar** quando já existe grade e exige confirmação destrutiva explícita para prosseguir. Nenhuma coluna de origem é criada — sem marcador, "existe grade" é lido de forma conservadora (qualquer sessão), então a segunda execução em diante sempre pede a confirmação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - O organizador pousa onde trabalha (Priority: P1)

A conta `organizador` entra e chega direto à área de programação, não ao catálogo de quem compra. O
menu da conta oferece o destino de trabalho dela, do mesmo jeito que já oferece "Meus ingressos" ao
cliente e "Validar ingressos" à portaria. Diferente da portaria, o organizador **continua alcançando
o catálogo público**: é ali que ele confere que a sessão que publicou apareceu à venda.

**Why this priority**: sem isto o painel só existe para quem decorou o endereço — e uma tela que
depende de endereço decorado, na prática, não existe. É o mesmo argumento que já está escrito no
teste da portaria.

**Independent Test**: entrar com `organizador`, verificar que a primeira tela é a área de
programação, abrir o menu da conta e confirmar o item de trabalho, navegar até a home e confirmar
que ela **não** redireciona de volta.

**Acceptance Scenarios**:

1. **Given** a conta `organizador` sem destino pedido explicitamente, **When** ela conclui a entrada,
   **Then** pousa na área de programação.
2. **Given** a conta `organizador` conduzida à entrada ao tentar abrir uma página específica,
   **When** ela entra, **Then** volta àquela página — o destino pedido continua vencendo a casa do
   papel.
3. **Given** um organizador autenticado, **When** ele abre o menu da conta, **Then** vê o item de
   trabalho com rótulo próprio, ao lado de "Sair".
4. **Given** um organizador autenticado, **When** ele abre a home, o detalhe de um filme ou uma
   busca, **Then** a página abre normalmente — sem redirecionamento para o painel.
5. **Given** um visitante sem sessão, **When** ele abre a área de programação, **Then** é conduzido à
   entrada e, depois de entrar como organizador, volta à área de programação.
6. **Given** um cliente ou um usuário de portaria autenticado, **When** abre a área de programação,
   **Then** recebe recusa explícita por papel, escrita em português, sem ser mandado para a entrada.

---

### User Story 2 - Publicar uma sessão de um filme que já está no catálogo (Priority: P1)

O organizador escolhe um filme que o catálogo local já tem, escolhe uma sala, define horário e preço,
e publica. Em seguida abre o filme no catálogo público e vê a sessão nova entre as disponíveis para
compra — o mesmo caminho que o cliente percorre.

**Why this priority**: é o motivo de a feature existir. É a primeira vez que a grade tem origem
diferente do `seed_demo`, e é o que permite ao avaliador montar um cenário próprio sem rodar comando
nenhum. Sozinha, já entrega o painel inteiro em versão mínima.

**Independent Test**: com o catálogo já sincronizado, criar uma sessão publicada para um filme
existente e comprá-la até o ingresso, pelo fluxo do cliente, sem tocar em nenhum comando.

**Acceptance Scenarios**:

1. **Given** um filme no catálogo local e uma sala com lugares, **When** o organizador informa
   filme, sala, horário futuro e preço e publica, **Then** a sessão é criada com estado "publicada" e
   aparece na grade do painel.
2. **Given** a sessão publicada do cenário anterior, **When** um cliente abre a página daquele filme,
   **Then** o horário aparece entre os disponíveis e leva ao mapa de assentos daquela sala.
3. **Given** uma sessão já existente naquela sala e naquele horário exato, **When** o organizador
   tenta criar outra, **Then** a criação é recusada com frase que nomeia a sala e o horário em
   conflito, e nenhuma sessão duplicada é gravada.
4. **Given** um horário no passado, **When** o organizador tenta publicar, **Then** é recusado com
   explicação — uma sessão publicada no passado não é vendável e apareceria no painel como uma
   promessa que a loja não cumpre.
5. **Given** um preço ausente, zero ou negativo, **When** o organizador envia, **Then** é recusado
   com a frase do campo, sem gravar.
6. **Given** o organizador escolheu "salvar como rascunho", **When** a sessão é criada, **Then** ela
   aparece na grade do painel marcada como rascunho e **não** aparece em nenhuma tela de cliente.

---

### User Story 3 - Trazer um filme novo do TMDb (Priority: P2)

O organizador quer programar um filme que o catálogo local ainda não tem. Ele digita o título, o
back-end consulta o TMDb, e ele escolhe um dos resultados. A escolha **persiste o filme localmente**
— título, pôster, duração, sinopse, trailer — e a partir daí o filme está disponível para receber
sessões como qualquer outro.

**Why this priority**: é o que o Princípio VII descreve por escrito ("no momento em que o organizador
cria a sessão") e o que tira o catálogo da dependência de rodar `sync_tmdb` na mão. Vem depois da
US2 porque a US2 já fecha o laço com o catálogo que existe.

**Independent Test**: buscar um título que não está no catálogo local, escolher um resultado,
confirmar que o filme passou a existir localmente com pôster e sinopse, e criar uma sessão para ele.

**Acceptance Scenarios**:

1. **Given** um termo de busca, **When** o organizador pesquisa, **Then** vê os resultados do TMDb com
   título, ano e pôster, e cada um indica se já está no catálogo local.
2. **Given** um resultado que ainda não existe localmente, **When** o organizador o escolhe, **Then** o
   filme é persistido localmente com tudo o que a sincronização de catálogo já traz — título, pôster,
   duração, sinopse, gêneros, classificação e trailers — e fica pronto para receber sessão.
3. **Given** o filme recém-trazido, **When** um cliente abre a página dele, **Then** as abas Sobre e
   Trailers têm o mesmo conteúdo que teriam se o filme tivesse chegado pela sincronização, e a área
   de sessões mostra o estado vazio, porque ainda não há grade.
4. **Given** o filme recém-trazido, **When** a home é aberta, **Then** ele **não** aparece nas trilhas
   "Em alta" nem "Em breve" — programar é operação de grade, não curadoria de vitrine.
5. **Given** um filme que **já** existe no catálogo local, **When** o organizador o escolhe de novo,
   **Then** nenhum filme duplicado é criado e ele segue para a sessão com o filme existente.
6. **Given** o TMDb indisponível ou lento além do prazo, **When** o organizador busca, **Then** vê uma
   mensagem em português dizendo o que aconteceu e qual a próxima ação, e **continua podendo**
   programar com os filmes do catálogo local.
7. **Given** uma busca sem resultado nenhum, **When** a resposta chega, **Then** o estado vazio diz que
   nada foi encontrado para aquele termo — não uma área em branco.
8. **Given** qualquer momento desta história, **When** o tráfego do navegador é inspecionado, **Then**
   a chave do TMDb não aparece: a busca passa pelo back-end.

---

### User Story 4 - Criar uma sala e ganhar o mapa de lugares (Priority: P2)

O organizador vê as salas que existem, com nome, capacidade e quantos lugares foram gerados. Cria uma
sala nova informando nome e capacidade; os lugares nascem junto, com a mesma regra que o cenário de
demonstração já usa — fileiras identificadas por letra e os lugares de acessibilidade na última
fileira.

**Why this priority**: sem sala nova o organizador está preso às duas do seed. Vem depois da US2/US3
porque programar nas salas existentes já é útil.

**Independent Test**: criar uma sala de capacidade conhecida, abrir uma sessão nela pelo fluxo do
cliente e conferir que o mapa exibido tem exatamente aqueles lugares, com a acessibilidade na última
fileira.

**Acceptance Scenarios**:

1. **Given** um nome e uma capacidade válida, **When** o organizador cria a sala, **Then** a sala
   aparece na lista com a quantidade de lugares gerada, e o mapa da sala segue a mesma regra do
   cenário de demonstração.
2. **Given** capacidade zero, ausente ou não numérica, **When** o organizador envia, **Then** é
   recusado com a frase do campo, sem criar sala nem lugares.
3. **Given** capacidade acima do teto de 26 fileiras, **When** o organizador envia, **Then** é
   recusado com frase que informa o teto — em vez de gerar em silêncio uma identificação de fileira
   ilegível.
4. **Given** uma sala **sem** nenhuma ocupação, **When** o organizador altera a capacidade, **Then** o
   mapa de lugares é refeito para a capacidade nova.
5. **Given** uma sala com reserva viva ou ingresso emitido em qualquer sessão dela, **When** o
   organizador tenta alterar a capacidade, **Then** é recusado com frase que explica que há lugares
   ocupados, e nenhum lugar é apagado.
6. **Given** a lista de salas vazia, **When** a página abre, **Then** o estado vazio convida a criar a
   primeira sala.

---

### User Story 5 - Conduzir a grade: corrigir, publicar e cancelar (Priority: P3)

O organizador vê sua grade separada por estado — rascunho, publicada, cancelada. Corrige um rascunho
enquanto ele ainda não está à venda, publica quando decide colocá-lo à venda, e cancela quando a
sessão não vai acontecer. Cancelar **para de vender**; não estorna, não devolve ao estoque o lugar já
pago.

**Why this priority**: é gestão do que a US2 criou. O painel entrega valor sem isto, mas fica sem
resposta para "programei errado".

**A fronteira da correção é a publicação, e ela é deliberada**: enquanto a sessão é rascunho, nenhum
cliente a viu e nada pode ter sido comprado — corrigir não muda nada sob ninguém. Depois de
publicada, filme, sala, horário e preço ficam imutáveis: mudar qualquer um deles reabriria "o que
acontece com quem já comprou", que é regra de negócio nova e esta feature declara não reabrir
nenhuma. O caminho para uma sessão publicada errada é cancelar e programar outra.

**Independent Test**: criar um rascunho com o horário errado, corrigi-lo, confirmar que nenhum
cliente o viu em momento algum, publicá-lo, confirmar que passou a aparecer, cancelá-lo e confirmar
que parou de aparecer — enquanto um ingresso já emitido daquela sessão continua na lista do cliente.

**Acceptance Scenarios**:

1. **Given** sessões nos três estados, **When** o organizador abre a grade, **Then** distingue
   rascunho, publicada e cancelada sem depender só de cor.
2. **Given** uma sessão em rascunho, **When** o organizador altera filme, sala, horário ou preço,
   **Then** a alteração é gravada e a sessão continua em rascunho.
3. **Given** uma sessão publicada ou cancelada, **When** o organizador tenta alterar filme, sala,
   horário ou preço, **Then** é recusado com frase que explica que só rascunho é editável.
4. **Given** um rascunho sendo movido para uma (sala, horário) já ocupada por outra sessão, **When** a
   alteração é enviada, **Then** é recusada pelo mesmo conflito da criação, e nada é gravado.
5. **Given** um rascunho com horário futuro, **When** o organizador publica, **Then** a sessão passa a
   aparecer à venda para o cliente.
6. **Given** um rascunho com horário já passado, **When** o organizador tenta publicar, **Then** é
   recusado com explicação.
7. **Given** uma sessão publicada, **When** o organizador cancela, **Then** ela deixa de aparecer para
   compra e nenhuma reserva nova é aceita.
8. **Given** um rascunho que o organizador não quer mais, **When** ele cancela, **Then** a sessão sai
   da grade ativa sem nunca ter sido vendida — cancelar não exige ter publicado antes.
9. **Given** um ingresso já emitido para a sessão cancelada, **When** o cliente abre "Meus ingressos",
   **Then** o ingresso continua lá, com o mesmo comportamento que a feature 009 já entrega — o
   cancelamento não apaga histórico de venda.
10. **Given** uma sessão cancelada, **When** o organizador a observa na grade, **Then** o estado é
    final: não há "descancelar" e não há edição.
11. **Given** a grade vazia, **When** a página abre, **Then** o estado vazio diz que nenhuma sessão foi
    programada e aponta o caminho para programar a primeira.

---

### Edge Cases

- **Duas abas do mesmo organizador publicam a mesma (sala, horário) ao mesmo tempo.** A garantia é a
  constraint do banco, não a checagem prévia do formulário: exatamente uma vence, a outra recebe a
  frase de conflito. Uma consulta "já existe sessão nesse horário?" antes do INSERT é o padrão que a
  concorrência quebra — as duas verificam, nenhuma encontra, ambas tentam gravar.
- **O organizador escolhe no TMDb um filme cujo `tmdb_id` já existe localmente.** Não duplica: o
  `tmdb_id` é único. A escolha reaproveita o filme que já está lá.
- **O TMDb cai no meio da feature.** A busca degrada com mensagem útil; criar sessão a partir do
  catálogo local, criar sala, publicar e cancelar continuam funcionando. Comprar, ver ingresso e
  validar na portaria não são afetados em nenhum momento.
- **Capacidade exatamente no teto** (26 fileiras cheias): aceita. Um lugar acima: recusada.
- **Capacidade que não fecha a última fileira**: a última fileira fica incompleta — nenhum lugar é
  inventado para completá-la.
- **Sala com capacidade menor que a cota de lugares de acessibilidade**: todos os lugares da última
  fileira viram acessíveis; a criação não falha.
- **Alterar capacidade de sala cujas ocupações estão todas vencidas e não pagas**: permitido — reserva
  vencida não ocupa. É a mesma leitura de ocupação viva que o resto do sistema já usa; nenhuma
  segunda definição é criada aqui.
- **Cancelar uma sessão que ainda tem reserva viva não paga**: a reserva não é convertida em compra
  porque a sessão parou de vender; o lugar volta ao estoque pelo vencimento, como sempre.
- **Publicar sessão numa sala sem nenhum lugar**: recusado — uma sessão sem assento não é comprável, e
  publicá-la coloca à venda algo que o mapa não consegue exibir.
- **Recriar o cenário de demonstração depois de o organizador ter programado**: o comando recusa e
  explica, em vez de apagar. Com a confirmação explícita, apaga tudo como sempre fez. Em base vazia,
  roda direto.

## Requirements *(mandatory)*

### Functional Requirements

#### Casa do papel e navegação

- **FR-001**: A tabela que define a casa de cada papel MUST ganhar o organizador, com endereço e
  rótulo próprios, para que o menu da conta e o destino pós-entrada passem a conhecê-lo pela mesma
  fonte — sem que nenhum dos dois consumidores precise saber que o painel existe.
- **FR-002**: A tabela MUST distinguir **dois fatos hoje unidos**: "este papel pousa na tela dele ao
  entrar" e "este papel não alcança nenhuma outra tela". O organizador tem o primeiro e **não** tem o
  segundo. Reusar o campo de tela única para os dois significaria trancar o organizador fora do
  catálogo público, que é onde ele confere o próprio trabalho.
- **FR-003**: O organizador MUST pousar na área de programação ao concluir a entrada quando não houver
  destino pedido explicitamente; um destino pedido explicitamente MUST continuar vencendo.
- **FR-004**: O organizador MUST continuar alcançando todas as páginas públicas do catálogo, sem
  redirecionamento.
- **FR-005**: Os testes que hoje afirmam "o organizador não tem tela própria" — a ausência do item no
  menu da conta e a ausência de destino — MUST ser atualizados para afirmar o comportamento novo, e
  não removidos.

#### A área de trabalho

- **FR-006**: O sistema MUST oferecer uma área autenticada de programação, alcançável pelo menu da
  conta e por endereço próprio.
- **FR-007**: Toda superfície da área MUST ter estado de sucesso, estado de erro e estado vazio,
  escritos em português para o usuário final, dizendo o que aconteceu e qual a próxima ação. Nenhuma
  seção pode ser entregue como "em breve".
- **FR-008**: Um visitante sem sessão que abra a área MUST ser conduzido à entrada e MUST voltar à
  área depois de entrar como organizador.

#### Filmes

- **FR-009**: O organizador MUST poder buscar filmes por título; a consulta ao TMDb MUST ser feita
  pelo back-end, com prazo máximo explícito e erro traduzido em frase acionável em português.
- **FR-010**: A chave da API do TMDb MUST NOT ser exposta ao navegador em nenhuma forma.
- **FR-011**: Escolher um resultado da busca MUST persistir localmente os dados necessários para
  vender o ingresso — título, pôster, duração e sinopse —, de modo que compra, exibição de ingresso e
  validação na portaria nunca dependam do TMDb.
- **FR-011a**: A persistência MUST usar o **mesmo mapeamento** que a sincronização de catálogo já
  aplica, trazendo também gêneros, classificação indicativa e trailers. Um filme trazido pelo painel
  MUST NOT ser um filme de segunda classe: as abas Sobre e Trailers que a 012 entregou têm de ter o
  mesmo conteúdo que teriam se ele tivesse chegado pela sincronização. MUST NOT existir um segundo
  mapeamento reduzido.
- **FR-012**: Escolher um filme que já existe no catálogo local MUST reaproveitar o registro existente
  e MUST NOT criar um segundo.
- **FR-013**: O organizador MUST poder escolher um filme diretamente do catálogo local, sem passar
  pela busca no TMDb.
- **FR-014**: A indisponibilidade do TMDb MUST NOT impedir criar sala, criar sessão a partir do
  catálogo local, publicar ou cancelar.

#### Salas

- **FR-015**: O organizador MUST poder listar as salas com nome, capacidade e quantidade de lugares.
- **FR-016**: O organizador MUST poder criar uma sala informando nome e capacidade.
- **FR-017**: Criar uma sala MUST gerar os lugares dela pela **mesma regra** já usada pelo cenário de
  demonstração — fileiras identificadas por letra, última fileira possivelmente incompleta, lugares de
  acessibilidade na última fileira. A regra MUST passar a viver num único lugar consumido pelos dois;
  MUST NOT existir uma segunda implementação.
- **FR-018**: O sistema MUST recusar capacidade ausente, zero, negativa ou acima do teto de 26
  fileiras, com frase que informe o limite.
- **FR-019**: O organizador MUST poder alterar a capacidade de uma sala **sem ocupação viva**, e o mapa
  de lugares MUST ser refeito para a capacidade nova.
- **FR-020**: O sistema MUST recusar a alteração de capacidade de sala com ocupação viva — reserva
  válida ou ingresso emitido —, com frase que explique a razão, e MUST NOT apagar nenhum lugar nesse
  caso.
- **FR-021**: A leitura de "ocupação viva" MUST ser a que o sistema já usa; MUST NOT ser redefinida
  nesta feature.

#### Sessões

- **FR-022**: O organizador MUST poder criar uma sessão informando filme, sala, horário e preço, e
  escolhendo entre gravar como rascunho ou publicar.
- **FR-023**: O organizador MUST poder alterar filme, sala, horário e preço de uma sessão **em
  rascunho**, que permanece em rascunho depois da alteração.
- **FR-024**: O sistema MUST recusar alterar filme, sala, horário ou preço de sessão **publicada ou
  cancelada**, com frase que explique que só rascunho é editável. Corrigir uma sessão publicada
  reabriria "o que acontece com quem já comprou", e nenhuma regra de compra é reaberta nesta feature.
- **FR-025**: A unicidade de (sala, horário) MUST ser garantida pelo banco, tanto ao criar quanto ao
  alterar um rascunho. Uma verificação prévia no formulário pode melhorar a mensagem, mas MUST NOT ser
  o que impede a duplicata.
- **FR-025a**: O sistema MUST NOT recusar duas sessões que se sobreponham no tempo na mesma sala. A
  duração do filme não é modelada como bloqueio de sala. A ausência é deliberada e MUST ser tratada
  como decisão, não como esquecimento: a duração é anulável para parte do catálogo, a regra não é
  expressável como constraint, e ela viveria só na aplicação — o oposto de como as três garantias
  anteriores deste projeto foram construídas.
- **FR-026**: O sistema MUST recusar publicar sessão com horário no passado.
- **FR-027**: O sistema MUST recusar preço ausente, zero ou negativo.
- **FR-028**: O sistema MUST recusar publicar sessão em sala sem nenhum lugar.
- **FR-029**: O organizador MUST poder listar a própria grade com os três estados distinguíveis sem
  depender só de cor.
- **FR-030**: O organizador MUST poder publicar um rascunho e MUST poder cancelar uma sessão — tanto
  em rascunho quanto publicada. Sem o cancelamento de rascunho, um rascunho errado ficaria na grade
  para sempre, já que apagar sessão está fora de escopo.
- **FR-031**: Cancelar uma sessão MUST fazê-la parar de vender. MUST NOT estornar pagamento, MUST NOT
  apagar ingresso emitido e MUST NOT devolver ao estoque o lugar já pago.
- **FR-032**: Sessão em rascunho e sessão cancelada MUST NOT aparecer em nenhuma superfície de compra
  do cliente.
- **FR-033**: A regra que decide "dá para comprar?" MUST permanecer como está — publicada e no futuro
  — e MUST NOT ganhar responsabilidade nova nesta feature. A portaria continua sem consumi-la.

#### Autorização

- **FR-034**: Toda operação de escrita de programação — filme, sala, sessão — MUST negar por padrão no
  servidor e exigir o papel organizador.
- **FR-035**: Cliente e portaria autenticados que chamem uma escrita de programação MUST receber
  recusa por papel (não recusa por falta de autenticação), com frase que descreva a operação que eles
  tentaram — não a de outra tela.
- **FR-036**: A suíte de testes MUST cobrir pelo menos uma tentativa de escrita de programação negada
  por papel para cliente e para portaria.
- **FR-037**: Esconder um controle na interface MUST NOT contar como autorização em nenhum ponto desta
  feature.

#### Não-regressão

- **FR-038**: O caminho do cliente — catálogo, filme, assentos, pagamento, ingresso — e o da portaria
  MUST permanecer funcionalmente idênticos. As telas recompostas pela 012 não são reabertas.
- **FR-039**: A identidade visual MUST vir dos tokens já definidos. Nenhum valor de cor, espaçamento,
  tipografia, raio ou duração pode ser escrito fora deles; espaço novo, se necessário, nasce como
  token.
- **FR-040**: O README MUST ser atualizado com o que a feature muda para quem avalia — que a grade
  pode ser montada pelo painel, e não só pelo seed, e que recriar o cenário de demonstração passou a
  exigir confirmação explícita.

#### O cenário de demonstração

- **FR-041**: O comando que recria o cenário de demonstração MUST NOT destruir uma grade existente
  sem confirmação destrutiva explícita de quem o executa. Ele MUST recusar-se a rodar, explicando o
  que seria apagado e como prosseguir.
- **FR-042**: A detecção MUST ser conservadora: o sistema **não registra a origem de uma sessão**, e
  esta feature MUST NOT criar esse registro. Logo, "existe grade" significa *existe qualquer sessão* —
  o comando não distingue o que ele mesmo criou do que o painel criou, e trata as duas como perda
  possível. A consequência é aceita: da segunda execução em diante, recriar a demonstração sempre
  exige a confirmação.
- **FR-043**: Com a confirmação dada, o comportamento MUST ser exatamente o de hoje — apagar e
  recriar o cenário inteiro, na mesma ordem que os vínculos protegidos exigem. Nenhuma remoção
  seletiva é introduzida.
- **FR-044**: A primeira execução em base vazia MUST continuar funcionando sem nenhum passo extra —
  é o caminho do avaliador, e ele não tem nada a perder.

#### O catálogo público

- **FR-045**: Um filme trazido pelo painel MUST entrar no catálogo público imediatamente, como
  qualquer filme sincronizado — a busca o encontra e a página dele abre. Sem sessão publicada, essa
  página MUST usar o estado vazio que a 012 já entrega. MUST NOT nascer um conceito novo de
  visibilidade no catálogo.
- **FR-046**: Trazer um filme pelo painel MUST NOT marcá-lo como "em alta" nem como "em breve". As
  trilhas da home continuam decididas pela sincronização de catálogo: programar uma sessão é
  operação de grade, não curadoria de vitrine.

### Key Entities

Nenhuma entidade nova. A feature usa as que já existem:

- **Filme**: obra do catálogo, identificada de forma única pela sua identidade no TMDb. Guarda
  localmente o que é preciso para vender e exibir o ingresso.
- **Sala**: espaço físico com nome e capacidade. Possui lugares.
- **Lugar**: posição física da sala — fileira, número e tipo (comum ou de acessibilidade). É o mesmo
  em todas as sessões daquela sala.
- **Sessão**: exibição de um filme numa sala, em um horário, a um preço, em um dos três estados
  (rascunho, publicada, cancelada). Duas sessões nunca ocupam a mesma sala no mesmo horário.
- **Ocupação de lugar**: relação entre uma reserva e um lugar em uma sessão. Nesta feature é apenas
  **lida**, para decidir se a capacidade de uma sala pode mudar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Partindo da entrada, o organizador coloca um filme do catálogo local à venda — sessão
  publicada, visível para o cliente — em menos de 2 minutos e sem executar nenhum comando de terminal.
- **SC-002**: 100% das sessões publicadas pelo painel aparecem no caminho de compra do cliente sem
  qualquer passo intermediário manual.
- **SC-003**: Um filme trazido do catálogo externo pelo painel permanece completo — título, pôster,
  duração, sinopse — e continua comprável mesmo com o catálogo externo fora do ar.
- **SC-004**: Duas tentativas simultâneas de programar a mesma sala no mesmo horário resultam em
  exatamente uma sessão gravada, e a perdedora recebe frase que nomeia o conflito.
- **SC-005**: Nenhuma tentativa de escrita de programação feita por cliente ou por portaria é aceita —
  0% —, e a recusa distingue "não pode" de "não entrou".
- **SC-006**: Uma sala criada pelo painel produz um mapa de lugares indistinguível, na regra, de uma
  sala criada pelo cenário de demonstração com a mesma capacidade.
- **SC-007**: Nenhuma superfície da área de programação chega à entrega sem estado de erro e estado
  vazio escritos em português; auditável percorrendo cada tela com o servidor indisponível e com a
  base vazia.
- **SC-008**: A chave da API externa não aparece em nenhuma resposta entregue ao navegador.
- **SC-009**: Cancelar uma sessão publicada com ingresso emitido não altera nenhum ingresso: o cliente
  continua vendo o dele e a portaria continua dando o mesmo desfecho de antes.

## Assumptions

- **A grade é do sistema, não "do organizador que a criou".** Há um único organizador no cenário do
  desafio; a programação não é particionada por dono, e nenhuma noção de propriedade de sessão é
  introduzida.
- **Apagar sala e apagar sessão estão fora de escopo.** Sessão sai de circulação sendo cancelada —
  inclusive em rascunho; sala não some porque sessões passadas apontam para ela.
- **Renomear uma sala é permitido a qualquer momento** — o nome não afeta nenhum lugar nem nenhuma
  venda.
- **A grade do painel mostra a ocupação de cada sessão** (lugares tomados sobre capacidade), lida das
  reservas existentes. É valor derivado, nunca contador materializado.
- **A busca no catálogo externo devolve uma página de resultados**, não paginação infinita. O objetivo
  é achar um filme para programar, não navegar o catálogo mundial.
- **O sistema não impede sessões sobrepostas na mesma sala** — decidido, não esquecido; ver FR-025a e
  a nota de 2026-08-12 em Clarifications.
- **O cenário de demonstração continua existindo e continua sendo o caminho do avaliador.** O painel
  não o substitui; o que muda é que recriá-lo por cima de uma grade existente passa a exigir
  confirmação explícita (FR-041 a FR-044).
- **Autenticação e sessão são as que a feature 003 entregou.** Nenhum mecanismo novo de login.
- **Fila, aprovação ou revisão de programação não existem.** O organizador publica direto.
