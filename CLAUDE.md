<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/009-my-tickets-sharing/plan.md`
- Spec: `specs/009-my-tickets-sharing/spec.md`
- Research: `specs/009-my-tickets-sharing/research.md`
- Data model: `specs/009-my-tickets-sharing/data-model.md`
- Contracts: `specs/009-my-tickets-sharing/contracts/`
- Quickstart: `specs/009-my-tickets-sharing/quickstart.md`

Features anteriores, já implementadas:

- `specs/001-movie-highlights-carousel/` — carrossel da home, catálogo TMDb, página do filme
- `specs/002-site-header-navigation/` — cabeçalho global e busca por título (44/44)
- `specs/003-user-authentication/` — entrada, saída e sessão para os três papéis (52/52)

- `specs/004-home-movie-rows/` — trilhas Em cartaz, Em alta e Em breve na home (55/55 + emenda
  de 11 tarefas). A trilha Em alta exige sessão planejada desde a emenda de 2026-08-11.

- `specs/005-seed-and-carousel-tuning/` — carrossel de 3 e seed com 12 filmes à venda (22/22)
- `specs/006-visual-identity/` — linguagem visual e disciplina de tokens (47/47). Nenhum valor de
  cor, espaçamento, tipografia, raio ou duração pode ficar fora dos tokens.

- `specs/007-seat-selection/` — mapa da sala e reserva com prazo de 10 minutos, protegida por
  `UNIQUE(sessão, assento)` em `ReservedSeat`. A constraint é **absoluta, sem predicado**: o índice
  parcial era impossível porque `now()` não é imutável.

- `specs/008-payment-ticket-issuance/` — pagamento simulado e emissão do ingresso, inseparáveis
  (mesma transação, mesma migração). Duas constraints: `UNIQUE(reserva) WHERE aprovado` (parcial —
  o predicado é imutável, ao contrário da 007) e `UNIQUE(assento reservado)` no ingresso. O código
  do QR é assinado com `TICKET_SIGNING_KEY` — **segredo próprio, distinto da `DJANGO_SECRET_KEY`**,
  sem valor padrão utilizável, que nunca chega ao front-end, verificado em `services/ingressos.py`,
  um módulo **puro** que não importa modelo (é o que torna `num_queries == 0` verificável).

**A feature 009 dá endereço permanente ao ingresso e um link para mostrá-lo a outra pessoa.** Duas
decisões estruturam tudo:

1. **O token do link é distinto do código do QR**, e os ciclos de vida são independentes: revogar um
   convite não pode queimar uma entrada paga. `TicketShareLink` não conhece a chave de assinatura, e
   `services/ingressos.py` não conhece a existência de link nenhum. Teste obrigatório compara o
   código antes e depois de revogar.
2. **A página compartilhada é pública e mostra APENAS filme, sessão, sala, lugar e QR.** É servida
   pelo `TicketSerializer` da 008 **sem alteração** — o risco não é o que ele expõe hoje, é a pressão
   de crescimento, e por isso os campos da área do dono vão para um serializer separado. Teste de
   não vazamento inspeciona a resposta inteira e é requisito, não diferencial.

A constraint é `UNIQUE(ingresso) WHERE revogado_em IS NULL` — parcial, terceiro capítulo da mesma
história: 007 absoluta porque `now()` não é imutável, 008 e 009 parciais porque os predicados são.
Preservar os links revogados é o que faz "revogado nunca volta a valer" ser estrutura, não sorte.

**Armadilha herdada desta feature**: toda consulta de sessão da 001 à 008 passa por `sellable()`
(`published()` E `starts_at > now()`). É o filtro certo para **estoque** e errado para **histórico** —
usá-lo aqui esvaziaria para sempre o grupo "já aconteceram" e faria sumir o ingresso da sessão
cancelada, que é justamente sobre o qual o cliente precisa de explicação. Nenhuma constraint pega, e a
linha errada parece mais idiomática que a certa.

**Trade-off registrado**: o token do link fica em **texto claro** no banco, porque FR-028/FR-035
exigem que o dono recopie o link depois e hash torna isso impossível. Mitigado com 256 bits,
revogação imediata, `noindex` e `no-referrer`. Vai para o README pelo Princípio VI.

**Nada de estado "já utilizado" na 009** — a transição e a garantia de validação única nascem juntas
na feature da portaria.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
