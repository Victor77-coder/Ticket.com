<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/008-payment-ticket-issuance/plan.md`
- Spec: `specs/008-payment-ticket-issuance/spec.md`
- Research: `specs/008-payment-ticket-issuance/research.md`
- Data model: `specs/008-payment-ticket-issuance/data-model.md`
- Contracts: `specs/008-payment-ticket-issuance/contracts/`
- Quickstart: `specs/008-payment-ticket-issuance/quickstart.md`

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
  `UNIQUE(sessão, assento)` em `ReservedSeat` (202 asserções no back-end, 116 no front). A
  constraint é **absoluta, sem predicado**: o índice parcial era impossível porque `now()` não é
  imutável.

**A feature 008 emite o ingresso, e aprovação e emissão são inseparáveis.** O Princípio II diz que
"pagamento aprovado DEVE emitir o ingresso; não existe estado intermediário durável em que o
assento esteja preso sem dono" — então as duas entram na mesma transação e na mesma migração, pelo
mesmo motivo que a 007 criou modelo e constraint juntos. Duas constraints carregam a garantia:
`UNIQUE(reserva) WHERE aprovado` (parcial — aqui o predicado é imutável, ao contrário da 007) e
`UNIQUE(assento reservado)` no ingresso. O teste de concorrência é prova obrigatória e precisa
**falhar** se qualquer uma for removida.

**Armadilha herdada, corrigida nesta feature**: a 007 decide ocupação por `expires_at > now()`, em
três cópias. Reserva paga não mexe em `expires_at` — sem o segundo termo (`status = paid`), o lugar
vendido volta ao estoque e `_liberar_ou_recusar` **apaga a ocupação paga** sem violar constraint
alguma. É a única falha da 008 que o banco aceita sem reclamar.

O código do QR é assinado com `TICKET_SIGNING_KEY` — **segredo próprio, distinto da
`DJANGO_SECRET_KEY`**, sem valor padrão utilizável, que nunca chega ao front-end.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
