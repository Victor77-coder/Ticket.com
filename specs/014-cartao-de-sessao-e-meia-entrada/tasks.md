---
description: "Lista de tarefas — Cartão de Sessão e Meia-Entrada"
---

# Tasks: Cartão de Sessão e Meia-Entrada

**Input**: documentos de design em `/specs/014-cartao-de-sessao-e-meia-entrada/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md` (R1–R9), `data-model.md`,
`contracts/reserva-com-tipo.md`, `contracts/paineis-do-cartao.md`, `quickstart.md`

**Tests**: incluídos, e não por gosto — o `plan.md` fixa **três obrigações** (`T-CONC`, `T-DONO`,
`T-VAZAMENTO`) que só existem como teste, e a constitution exige teste de concorrência em toda
feature que toque assento, reserva ou pagamento. A US4 toca os três.

**Uma migração, e ela vive dentro da US4.** Nenhuma tarefa das fases 1 a 5 cria coluna. Isso é o que
torna o corte de escopo real: descartar a Fase 6 devolve o projeto ao estado atual sem deixar
esquema órfão.

## Format: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US4, conforme `spec.md`

---

## Phase 1: Setup

**Purpose**: linha base verde e os arquivos novos com o docstring que declara a regra, sem
implementação ainda. O docstring primeiro é o que impede a segunda cópia de nascer.

- [X] T001 Rodar a linha base e registrar que está verde antes de tocar em qualquer coisa: `docker compose exec backend python -m pytest` , `cd frontend && npx vitest run` e `docker compose exec backend python manage.py makemigrations --check --dry-run`
- [X] T002 [P] Criar `backend/apps/screening/services/precos.py` com apenas o docstring declarando que ele é o **dono único** da derivação do valor por lugar, que a meia é metade arredondada **para baixo** e que o total é soma de valores gravados, nunca `preço × quantidade` (R1, R2, R3, FR-017, FR-018)
- [X] T003 [P] Criar `frontend/lib/meia.ts` com apenas o docstring declarando que ele é **espelho puro** da regra do servidor, usado só na prévia antes de reservar, e que valor nenhum daqui é enviado (R6, FR-019)
- [X] T004 [P] Criar `frontend/components/sessao/sessao.module.css` vazio, com o comentário de que todo valor vem de token da 006/011 — cor, espaço, raio e duração soltos são reprovados por `frontend/tests/tokens.test.ts` (M7)
- [X] T005 [P] Conferir em `CLAUDE.md` que os marcadores `SPECKIT` apontam para `specs/014-cartao-de-sessao-e-meia-entrada/` e acrescentar a 013 à lista de features anteriores já implementadas

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a sobreposição compartilhada pelos dois painéis.

**⚠️ Escopo do bloqueio, dito com precisão**: T006–T008 bloqueiam **US2 e US3**. A **US1 não depende
delas** — o cartão é markup e pode ser feito em paralelo. Declarar que "nenhuma história começa"
seria falso aqui, e a lista prefere ser exata a ser convencional.

- [X] T006 [P] Escrever `frontend/tests/sobreposicao.test.tsx` cobrindo M1–M6 de `contracts/paineis-do-cartao.md`: fecha com `Esc`, fecha por botão com nome acessível, prende o foco enquanto aberto, **devolve o foco à origem** ao fechar, é anunciada como diálogo rotulado, e um painel por vez. Vermelho até T007
- [X] T007 Implementar `frontend/components/sessao/Sobreposicao.tsx` sobre `<dialog>` nativo — ele já entrega `Esc` e foco preso; o componente existe para padronizar a **devolução de foco** (M4) e a redação dos estados de espera e erro (depende de T006)
- [X] T008 Acrescentar os estilos da sobreposição em `frontend/components/sessao/sessao.module.css`, só com tokens (depende de T007)

**Checkpoint**: sobreposição acessível por teclado, com teste verde. US2 e US3 liberadas.

---

## Phase 3: User Story 1 — Ler a sessão num cartão (P1) 🎯 MVP

**Goal**: a grade de horários vira cartão por sala, com cabeçalho, régua e as duas ações no topo.

**Independent Test**: abrir um filme com sessões em duas salas → dois cartões, cada um nomeando a
sua sala, horários dentro, ações **Assentos** e **Preços** visíveis com texto, e o horário
disponível continuando a levar ao mapa.

### Tests for User Story 1

- [X] T009 [P] [US1] Escrever `frontend/tests/cartao-de-sessao.test.tsx` cobrindo C1–C7 de `contracts/paineis-do-cartao.md`: um cartão por sala, cabeçalho rotulando a região, ações com nome acessível em texto, horário esgotado distinguível sem cor, preço presente em cada horário. Vermelho até T011
- [X] T010 [P] [US1] Acrescentar a `frontend/tests/filme.test.tsx` a asserção de que o nome acessível `/^Escolher lugares —/` **continua** casando depois da recomposição (C5, FR-004) — é o contrato que o e2e da 007 depende

### Implementation for User Story 1

- [X] T011 [US1] Criar `frontend/components/sessao/CartaoDeSessao.tsx` recebendo `{ sala, horarios }` e rendendo cabeçalho, régua, ações e a grade de horários; as ações ainda não abrem nada (depende de T009)
- [X] T012 [US1] Reescrever a seção de sala de `frontend/app/filmes/[slug]/GradeDoDia.tsx` para delegar a `CartaoDeSessao`, preservando o agrupamento por dia e por sala que a 012 entregou
- [X] T013 [US1] Mover os estilos de horário e sala de `frontend/app/filmes/[slug]/filme.module.css` para `frontend/components/sessao/sessao.module.css`, deixando no primeiro só o que é da página (depende de T012)
- [X] T014 [US1] Implementar a regra de "qual sessão as ações operam" de `contracts/paineis-do-cartao.md` §C4: as ações do topo apontam para o **primeiro horário disponível**; sem nenhum disponível, apontam para o primeiro do cartão
- [X] T015 [US1] Rodar `npx vitest run` e confirmar que `filme.test.tsx`, `grade-sessoes.test.ts` e `tokens.test.ts` continuam verdes sem edição de asserção

**Checkpoint**: o cartão está em pé e o caminho para o mapa não mudou. **Entregável sozinho.**

---

## Phase 4: User Story 2 — Espiar a lotação (P2)

**Goal**: a ação **Assentos** abre uma prévia somente leitura da sala, com livres, ocupados e
contagem, mais o caminho para o mapa real.

**Independent Test**: abrir o painel numa sessão com lugares vendidos → os ocupados aparecem como
ocupados, a contagem bate com o mapa, nenhum assento é acionável, e "Escolher lugares" leva ao mapa.

### Tests for User Story 2

- [X] T016 [P] [US2] Escrever `frontend/tests/painel-de-assentos.test.tsx` cobrindo A1–A7: livre e ocupado distinguíveis sem cor, contagem de livres, **nenhum assento acionável** (nem botão, nem link), caminho para o mapa presente com lugares e ausente quando esgotada, estado de espera, estado de erro em português, e sala sem lugares explicada. Vermelho até T019

### Implementation for User Story 2

- [X] T017 [P] [US2] Criar a rota-proxy `frontend/app/api/mapa/[id]/route.ts` repassando `GET /api/v1/sessoes/<id>/mapa/` — o painel é componente de cliente e `API_BASE_URL` só resolve no servidor, então a chamada direta de `lib/api.ts` não serve. Sem cookie: o mapa é público, como já era
- [X] T018 [P] [US2] Acrescentar em `frontend/lib/api.ts` o cliente que o proxy usa, reusando `fetchSeatMap` — **sem** criar segunda leitura de ocupação (R4)
- [X] T019 [US2] Implementar `frontend/components/sessao/PainelDeAssentos.tsx` dentro de `Sobreposicao`, desenhando `fileiras[].assentos[].situacao` **como vem** do servidor, sem reinterpretar quem ocupa (R4, FR-008) — depende de T007, T016, T017
- [X] T020 [US2] Reusar em `frontend/components/sessao/PainelDeAssentos.tsx` a linguagem visual de assento de `frontend/components/seats/seats.module.css` sem importar `Seat.tsx`: o painel desenha, não seleciona (FR-007)
- [X] T021 [US2] Acrescentar o seletor dos demais horários do cartão dentro do painel, conforme `contracts/paineis-do-cartao.md` §C4
- [X] T022 [US2] Ligar a ação **Assentos** do `CartaoDeSessao` ao painel, com devolução de foco (M4)
- [X] T023 [US2] Conferir em escala de cinza que livre e ocupado continuam distinguíveis no painel, acrescentando a asserção a `frontend/tests/painel-de-assentos.test.tsx` pelo mesmo critério que `frontend/tests/seats.test.tsx` aplica ao mapa (A1, SC-003)

**Checkpoint**: metade do pedido da imagem entregue. **Entregável sozinho.**

---

## Phase 5: User Story 3 — Saber quanto custa (P2)

**Goal**: a ação **Preços** abre a tabela de inteira e meia daquela sessão.

**Independent Test**: abrir o painel numa sessão de R$ 32,00 → "Inteira R$ 32,00" e "Meia
R$ 16,00"; abrir numa sessão de preço diferente → valores diferentes.

### Tests for User Story 3

- [X] T024 [P] [US3] Escrever `frontend/tests/meia.test.ts` com a **tabela de casos compartilhada** com o back-end: preços exatos, preços com centavo ímpar (25,01 → 12,50), preço zero. É esta tabela que faz o espelho e o servidor concordarem por verificação, não por presunção (R6)
- [X] T025 [P] [US3] Escrever `frontend/tests/painel-de-precos.test.tsx` cobrindo P1–P4: os dois valores, valores por sessão, a frase sobre conferência na entrada, e que o exibido é o que será cobrado

### Implementation for User Story 3

- [X] T026 [US3] Implementar `frontend/lib/meia.ts`: metade arredondada para baixo em centavos, função pura, sem formatação — a formatação é de `frontend/lib/moeda.ts`, que já tem dono (depende de T024)
- [X] T027 [US3] Implementar `frontend/components/sessao/PainelDePrecos.tsx` dentro de `Sobreposicao`, consumindo `meia.ts` e `moeda.ts` (depende de T007, T025, T026)
- [X] T028 [US3] Ligar a ação **Preços** do `CartaoDeSessao` ao painel, com devolução de foco (M4) e um painel por vez (M6)
- [ ] T029 [US3] Escrever `frontend/tests/e2e/cartao-de-sessao.spec.ts` percorrendo o Percurso 2 do `quickstart.md` **só pelo teclado**: abrir Assentos, circular o foco, `Esc`, conferir que o foco voltou à ação

**Checkpoint**: o pedido da imagem está **completo**. Daqui para trás, nada tocou em dinheiro.

---

## Phase 6: User Story 4 — Meia-entrada comprável (P3)

**Goal**: o cliente define o tipo por lugar, o servidor soma os valores gravados, e cada ingresso
declara o seu tipo.

**⚠️ É a fase que abre o cálculo do total.** Ela sai inteira se o prazo apertar, e o projeto volta
ao estado da Fase 5 sem esquema órfão.

**Independent Test**: reservar dois lugares numa sessão de R$ 32,00, marcar um como meia → total
R$ 48,00 na tela, o mesmo total vindo do servidor no pagamento, e dois ingressos com tipos
diferentes.

### Tests for User Story 4

- [X] T030 [P] [US4] Escrever `backend/tests/test_precos.py` com a **mesma tabela de casos** de T024, provando a derivação e o arredondamento para baixo (R3, FR-017, FR-018). Vermelho até T033
- [X] T031 [P] [US4] Escrever `backend/tests/test_meia_entrada.py` cobrindo: `meias` ausente → tudo inteira (FR-016); `meias` subconjunto → total somado; `meias` com id fora de `assentos` → `400` com mensagem em português; `meias` igual a `assentos` → válido, sem cota (contracts/reserva-com-tipo.md)
- [X] T032 [P] [US4] Estender `backend/tests/test_payment_concurrency.py` com o caso de **tipos mistos** na mesma reserva, provando que continua havendo um único conjunto de ingressos e que o valor cobrado é a soma (`T-CONC`, SC-007) — e conferir que ele ainda **falha** se qualquer uma das duas garantias de banco for removida

### Model & Service for User Story 4

- [X] T033 [US4] Implementar `backend/apps/screening/services/precos.py`: `valor_do_lugar(preco_sessao, tipo)` com `ROUND_DOWN` em duas casas, e `total_da_reserva(reserva)` como **soma de `unit_price`** (depende de T030)
- [X] T034 [US4] Acrescentar `ticket_type` (escolhas `inteira`/`meia`, padrão `inteira` **no banco**) e `unit_price` (decimal 8,2, sem padrão) a `ReservedSeat` em `backend/apps/screening/models.py`, com o comentário de por que **não há `CHECK`** amarrando o valor ao preço da sessão (data-model.md)
- [X] T035 [US4] Gerar a migração `backend/apps/screening/migrations/0006_*.py` incluindo o passo de dados que preenche as linhas existentes com `unit_price = screening.price` e `ticket_type = 'inteira'` (data-model.md §migração)
- [X] T036 [US4] Atualizar o comentário de `Payment.amount` em `backend/apps/screening/models.py`, que hoje diz "a partir do preço da sessão e da quantidade de lugares" e deixa de ser verdade (data-model.md)
- [X] T037 [US4] Gravar `ticket_type` e `unit_price` no `bulk_create` de `ReservedSeat` dentro de `services/reservas.py` — **na transação que já existe**, sem transação nova (depende de T033, T034)
- [X] T038 [US4] Trocar `total_da_reserva` em `backend/apps/screening/services/pagamentos.py` pela soma de `precos.py`, apagando `reserva.screening.price * reserva.seats.count()` (`T-DONO`)

### API for User Story 4

- [X] T039 [US4] Aceitar `meias` opcional em `ReservationInputSerializer` (`backend/apps/screening/serializers.py`), validando que todo id consta em `assentos` → `400` (contracts/reserva-com-tipo.md §regras de `meias`)
- [X] T040 [US4] Repassar `meias` de `backend/apps/screening/views.py` a `criar_reserva`, mantendo a ordem atual de idempotência antes de disponibilidade
- [X] T041 [US4] Acrescentar `tipo` e `valor` a `LugarSerializer`/`ReservationSerializer` e trocar `get_total` pelo serviço, apagando a segunda cópia de `price × len(...)` (`T-DONO`)
- [X] T042 [P] [US4] Acrescentar `tipo` a `TicketSerializer`, lido por travessia de `reserved_seat` — **sem coluna nova em `Ticket`** (data-model.md)
- [X] T043 [P] [US4] Acrescentar `tipo` a `MeuIngressoSerializer` (FR-021)
- [X] T044 [US4] Acrescentar `tipo` ao serializer público de ingresso compartilhado **e** atualizar `backend/tests/test_share_link_leakage.py` incluindo o tipo na lista de permitidos **com a razão escrita dentro do teste** (`T-VAZAMENTO`, FR-023) — nunca afrouxando a inspeção
- [X] T045 [US4] Acrescentar `tipo` à resposta de validação da portaria em `backend/apps/screening/serializers.py`, e escrever em `backend/tests/test_gate_api.py` a asserção de que `desfecho` continua tendo **exatamente quatro** valores e que nenhum ramo de decisão lê o tipo (FR-024)

### Frontend for User Story 4

- [X] T046 [P] [US4] Acrescentar `tipo` e `valor` a `LugarReservado`, e `tipo` a `Ingresso`, em `frontend/lib/types.ts`
- [X] T047 [US4] Acrescentar o controle de tipo por lugar em `frontend/components/seats/SeatSelection.tsx`, com **inteira como padrão** e o total previsto por `lib/meia.ts` (FR-015, FR-016, R6)
- [X] T048 [US4] Apagar `const total = ids.size * Number(mapa.preco)` de `SeatSelection.tsx`, substituindo pela soma dos valores previstos por lugar (terceira cópia da regra, R2)
- [X] T049 [US4] Exibir uma linha por lugar com tipo e valor em `frontend/components/seats/SelectionSummary.tsx`
- [X] T050 [US4] Enviar `meias` em `frontend/lib/api.ts` (`postReserva`) **e** liberar o campo em `frontend/app/api/reservar/route.ts`, que hoje filtra o corpo campo a campo e descartaria `meias` em silêncio
- [X] T051 [P] [US4] Exibir o tipo no ingresso emitido em `frontend/components/tickets/Ingresso.tsx` e em `frontend/app/meus-ingressos/`
- [X] T052 [P] [US4] Exibir o tipo no desfecho da portaria em `frontend/components/gate/Desfecho.tsx`, como informação de conferência — nunca como condição (FR-024)
- [ ] T053 [P] [US4] Escrever `frontend/tests/meia-selecao.test.tsx`: padrão inteira, marcar meia recalcula o total, dois lugares com tipos diferentes somam certo
- [ ] T054 [US4] Escrever `frontend/tests/e2e/meia-entrada.spec.ts` percorrendo os Percursos 5 e 6 do `quickstart.md`: comprar uma inteira e uma meia, conferir R$ 48,00 no pagamento, e validar a meia na portaria com desfecho **pode entrar**

**Checkpoint**: meia comprável, ponta a ponta, com a portaria intacta.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T055 Conferir `T-DONO`: `grep -rn "price \*" backend/` não pode retornar nenhuma linha de cálculo de total
- [X] T056 [P] Rodar `docker compose exec backend python manage.py makemigrations --check --dry-run` e confirmar que só a 0006 existe de nova
- [ ] T057 [P] Rodar as três suítes e comparar com a linha base de T001: `pytest`, `vitest`, `playwright`
- [ ] T058 Percorrer o `quickstart.md` inteiro, os sete percursos, incluindo o Percurso 7 (centavo ímpar) que precisa de sessão de R$ 25,01 criada pelo painel do organizador
- [X] T059 [P] Atualizar `README.md`: o cartão e os dois painéis em "O que está pronto"; a meia-entrada e o que ela **não** faz (sem cota de 40%, sem categoria, conferência na porta) em "Limitações conhecidas"
- [X] T060 [P] Acrescentar a 014 à seção "Uso de IA" de `README.md`, no mesmo formato das 011–013
- [ ] T061 Fazer a checagem anti-slop do cartão contra R8, registrando o resultado em `specs/014-cartao-de-sessao-e-meia-entrada/contracts/anti-slop-review.md` — a mesma disciplina da 011, e ela é obrigatória aqui porque esta feature nasceu de captura de tela de concorrente
- [ ] T062 Registrar em `specs/014-cartao-de-sessao-e-meia-entrada/spec.md` o que ficou de fora e o que a implementação descobriu, como as features anteriores fizeram ao fechar

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências
- **Foundational (Fase 2)**: depende da Fase 1; bloqueia **US2 e US3** — não a US1
- **US1 (Fase 3)**: depende só da Fase 1
- **US2 (Fase 4)** e **US3 (Fase 5)**: dependem da Fase 2; ambas **consomem** o cartão da US1 para ter onde pendurar a ação
- **US4 (Fase 6)**: depende da Fase 1. **Não depende de US1, US2 nem US3** — toca o mapa de assentos e o back-end, não o cartão
- **Polish (Fase 7)**: depende do que tiver sido entregue

### A dependência que não existe, e vale dizer

**A US4 é independente do cartão.** Ela vive no mapa de assentos, no pagamento e no ingresso. Se o
prazo obrigar a escolher, dá para entregar US1+US2+US3 (o pedido da imagem) **ou** a US4 (meia
comprável) — as duas metades não se bloqueiam.

### Parallel Opportunities

- T002, T003, T004 em paralelo (arquivos distintos, só docstring)
- **US1 e a Fase 2 em paralelo**: o cartão não depende da sobreposição
- T016 (teste da US2) e T024/T025 (testes da US3) em paralelo
- T017 e T018 em paralelo (proxy e cliente)
- Na US4: T030, T031, T032 em paralelo; T042, T043 em paralelo; T046, T051, T052, T053 em paralelo
- Na Fase 7: T056, T057, T059, T060 em paralelo

### Parallel Example: User Story 4

```
Simultâneo (arquivos distintos, todos vermelhos de propósito):
  T030  backend/tests/test_precos.py
  T031  backend/tests/test_meia_entrada.py
  T032  backend/tests/test_payment_concurrency.py

Depois, em série (mesma cadeia de dados):
  T033 → T034 → T035 → T037 → T038
```

---

## Implementation Strategy

### MVP

**Fase 1 + Fase 3 (US1).** O cartão em pé, sem painel nenhum. Já muda a página do filme e não toca
em regra de negócio.

### Incremento recomendado, dado o prazo

1. **US1** — o cartão (baixo risco, alto retorno visual)
2. **Fase 2 + US3** — painel de preços antes do de assentos: é o mais barato dos dois e cobre a
   exigência do desafio de preço visível
3. **US2** — painel de assentos
4. **US4** — meia comprável, **só se houver dia inteiro sobrando**

### O corte, escrito antes de precisar dele

Se a Fase 6 não couber: ela sai **inteira** — tarefas T030 a T054. Nenhuma tela fica pela metade,
porque nenhuma das outras histórias menciona meia fora do painel de preços, que é informativo por
natureza. O único ajuste é a redação do painel de preços, que passa a dizer que a meia é adquirida
na bilheteria — uma frase, não uma tela.
