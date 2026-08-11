---
description: "Task list for feature implementation"
---

# Tasks: Escolha de Assentos

**Input**: Design documents from `/specs/007-seat-selection/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/reservation-api.md](./contracts/reservation-api.md),
[quickstart.md](./quickstart.md)

**Tests**: **Sim, e não são opcionais aqui.** A constitution exige o teste de concorrência como
prova do Princípio II (SC-002), e o spec acrescenta a exigência de que ele **falhe** se a
constraint for removida (R4). A ordem é TDD nas fases de reserva: o teste que prova a garantia
vem antes do serviço que a implementa.

**Organization**: Quatro user stories. US1 (mapa) e US2 (reserva) são ambas P1 e formam o MVP —
ver sem poder reservar não entrega nada, e reservar sem ver não é escolha de assento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (mapa), US2 (reserva), US3 (autorização), US4 (expiração)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Domínio**: `backend/apps/screening/` — assento, reserva e sessão são o mesmo domínio
- **A garantia**: `backend/apps/screening/models.py` + a migração `0002`
- **A transação**: `backend/apps/screening/services/reservas.py`
- **Front**: `frontend/app/sessoes/[id]/` e `frontend/components/seats/`

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte, e declarar os números que a feature usa

- [X] T001 Rodar `docker compose exec backend pytest` e `docker compose exec frontend npm run test` e registrar as contagens atuais em `specs/007-seat-selection/quickstart.md` — é a linha de base contra a qual SC-012 é medido no fim (FR-033)
- [X] T002 Declarar `RESERVATION_HOLD_MINUTES = 10` e `MAX_SEATS_PER_RESERVATION = 6` em `backend/config/settings/base.py`, com comentário apontando para as suposições da spec

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Os três modelos e a constraint — **na mesma migração**. É a fase que atravessa a
fronteira aberta desde a 001.

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar. E dentro dela,
T003–T007 formam **uma unidade indivisível**: nenhum commit pode existir com modelo de ocupação
sem a constraint que o protege — é literalmente o que o Princípio II proíbe.

- [X] T003 Remover o bloco `FRONTEIRA COM A FEATURE DE RESERVA` do docstring de `backend/apps/screening/models.py` e substituí-lo por nota apontando que a constraint desta feature é o que o aviso exigia
- [X] T004 Declarar `Seat` em `backend/apps/screening/models.py` com `room`, `row`, `number`, `kind` e `UniqueConstraint(room, row, number)` (data-model.md)
- [X] T005 Declarar `Reservation` em `backend/apps/screening/models.py` com `screening`, `customer`, `status`, `expires_at`, `idempotency_key` único e `created_at`
- [X] T006 Declarar `ReservedSeat` em `backend/apps/screening/models.py` com `reservation`, `screening` denormalizado, `seat` e a `UniqueConstraint(fields=["screening", "seat"], name="unico_assento_por_sessao")` — **sem `condition`**, com comentário explicando por que um índice parcial sobre `now()` é impossível (R1)
- [X] T007 Gerar `backend/apps/screening/migrations/0002_*.py` com `makemigrations` e **conferir lendo o arquivo** que os três modelos e a constraint estão todos nele — se saíram em migrações separadas, refazer
- [X] T008 Aplicar a migração e verificar no banco com `\d screening_reservedseat` que `unico_assento_por_sessao` aparece como `UNIQUE (screening_id, seat_id)` **sem cláusula `WHERE`** (quickstart.md)
- [X] T009 Substituir o corpo de `Screening.seats_taken` em `backend/apps/screening/models.py` para contar ocupações não vencidas da sessão, atualizando o docstring que anunciava o retorno zero (data-model.md)
- [X] T010 Gerar os assentos das salas em `backend/apps/catalog/management/commands/seed_demo.py`: fileiras de 10 lugares, letra por fileira, 3 lugares de acessibilidade na última — idempotente como o resto do comando (R7)
- [X] T011 [P] Cobrir a geração de assentos em `backend/tests/test_seed_demo.py`: contagem por sala, última fileira incompleta quando a capacidade não fecha, e rodar duas vezes não duplica
- [X] T012 [P] Acrescentar as fixtures `seats`, `make_reservation` e `occupy_seat` em `backend/tests/conftest.py`, reaproveitando `room` e `make_screening` já existentes

**Checkpoint**: a constraint existe no banco e o seed produz salas com assentos. Nada é exibido
nem reservável ainda.

---

## Phase 3: User Story 1 — Ver a sala e entender o que está livre (Priority: P1) 🎯 MVP

**Goal**: O cliente chega ao mapa a partir da sessão e reconhece de imediato o que está livre

**Independent Test**: Autenticado como `cliente1`, abrir uma sessão publicada e futura e conferir
que o mapa exibe todos os lugares, com os estados distinguíveis sem depender de cor

### Testes da User Story 1

- [X] T013 [P] [US1] Cobrir em `backend/tests/test_seat_map_api.py` que `GET /api/v1/sessoes/<id>/mapa/` devolve `200` com todas as fileiras da sala, na ordem de leitura, e o total de assentos igual à capacidade (FR-004)
- [X] T014 [P] [US1] Cobrir em `backend/tests/test_seat_map_api.py` que sessão inexistente, em rascunho, cancelada e já iniciada devolvem **a mesma** `404` com "Sessão não encontrada." (FR-003)
- [X] T015 [P] [US1] Cobrir em `backend/tests/test_seat_map_api.py` que o mapa responde `200` **sem sessão ativa** (FR-010) e que `situacao` só assume `livre` ou `tomado` (contrato)
- [X] T016 [P] [US1] Cobrir em `backend/tests/test_seat_map_api.py` que o mapa de uma sessão com reservas de outro cliente **não contém** nome, `id` de usuário, `id` de reserva nem `expires_at` de terceiro — gate do Princípio IV (contrato, "campos proibidos")
- [X] T017 [P] [US1] Cobrir em `backend/tests/test_seat_map_api.py` que o mapa é montado em **uma** consulta de assentos, com `django_assert_num_queries` (R8)

### Implementação da User Story 1

- [X] T018 [US1] Criar `backend/apps/screening/selectors.py` com `get_seat_map(screening)`: assentos da sala anotados com ocupação viva por subconsulta, ordenados por fileira e número (R8, data-model.md)
- [X] T019 [US1] Criar `backend/apps/screening/serializers.py` com o mapa agrupado por fileira, `tipo` separado de `situacao`, e `esgotada` derivado (contrato)
- [X] T020 [US1] Criar `backend/apps/screening/views.py` com `SeatMapView`, permissão `AllowAny`, resolvendo a sessão por `Screening.objects.sellable()` para que rascunho e cancelada caiam no mesmo `404` (FR-002, FR-003)
- [X] T021 [US1] Criar `backend/apps/screening/urls.py` com `sessoes/<int:pk>/mapa/` e registrá-lo em `backend/config/urls.py` sob `api/v1/` — **conferir que o servidor sobe** antes de seguir
- [X] T022 [P] [US1] Acrescentar os tipos `MapaSessao`, `Fileira` e `Assento` em `frontend/lib/types.ts`, espelhando o contrato
- [X] T023 [US1] Acrescentar `buscarMapaSessao(id)` em `frontend/lib/api.ts`, seguindo o padrão de erro e degradação já usado pelos demais consumidores
- [X] T024 [P] [US1] Criar `frontend/components/seats/Seat.tsx`: `<button>` real, `aria-pressed` para seleção, `aria-disabled` para tomado, e rótulo com fileira, número e situação (R11, FR-011)
- [X] T025 [P] [US1] Criar `frontend/components/seats/seats.module.css` com os quatro estados distinguíveis por **forma e marca**, não só por cor — contorno, preenchido, traço e símbolo (FR-008)
- [X] T026 [US1] Declarar em `frontend/styles/tokens.css` os tokens novos que os estados exigirem, sem remover nem renomear nenhum existente (FR-035)
- [X] T027 [US1] Criar `frontend/components/seats/SeatMap.tsx`: a sala em fileiras, com a tela indicada no topo, letra por fileira e corredor entre o quinto e o sexto lugar (FR-005, R7)
- [X] T028 [US1] Criar `frontend/app/sessoes/[id]/page.tsx` e `sessao.module.css`, buscando o mapa no servidor e tratando `404` com `not-found` (FR-003)
- [X] T029 [US1] Tornar cada sessão da lista em `frontend/app/filmes/[slug]/page.tsx` um caminho para o mapa daquela sessão — **uma interação** (FR-001, SC-001)
- [X] T030 [US1] Exibir o estado explicativo de sessão esgotada em `frontend/app/sessoes/[id]/page.tsx`, em português, dizendo o que houve e a próxima ação — nunca área em branco (FR-030, FR-031)
- [X] T031 [P] [US1] Cobrir em `frontend/tests/seats.test.tsx` que os quatro estados têm marca própria além da cor, que acionar um lugar tomado não seleciona, e que o lugar de acessibilidade não entra no fluxo comum (FR-008, FR-009, FR-014)
- [X] T032 [P] [US1] Cobrir em `frontend/tests/seats.test.tsx` que o mapa inteiro é alcançável e acionável por teclado, sem armadilha de foco (FR-011, SC-008)

**Checkpoint**: o mapa abre, é legível e é público. Ninguém reserva nada ainda.

---

## Phase 4: User Story 2 — Reservar os lugares escolhidos (Priority: P1) 🎯 MVP

**Goal**: A seleção vira reserva com prazo, e **exatamente uma** vence a corrida

**Independent Test**: Selecionar dois lugares livres, confirmar, e conferir que a reserva aparece
com prazo e que os dois lugares passam a constar tomados para outra pessoa

**⚠️ Esta é a fase que a constitution vigia.** T033 e T034 vêm **antes** do serviço: o teste que
prova a garantia é escrito contra um serviço que ainda não existe, e é assim que se sabe que ele
está testando a garantia e não o código.

### Testes da User Story 2 — a prova do Princípio II

- [X] T033 [US2] Criar `backend/tests/test_reservation_concurrency.py` com duas threads reais, **conexões de banco separadas**, `django_db(transaction=True)` e barreira sincronizando o ponto crítico: exatamente uma reserva vence, a outra recebe recusa (por bloqueio **ou** por constraint, tanto faz), e o banco fica com **uma** ocupação (R4, SC-002)
- [X] T034 [US2] Acrescentar em `backend/tests/test_reservation_concurrency.py` a asserção direta de que não existe par `(screening, seat)` duplicado após a corrida — a prova que não depende do código de resposta (SC-003)
- [X] T035 [P] [US2] Cobrir em `backend/tests/test_reservation_api.py` que uma seleção com qualquer lugar já tomado **não reserva nenhum** e nomeia o culpado no `409` (FR-018, FR-019, SC-009)
- [X] T036 [P] [US2] Cobrir em `backend/tests/test_reservation_api.py` as recusas de `400`: seleção vazia, acima de 6 lugares, assento de outra sala, assento de acessibilidade (FR-009, FR-013, FR-014)
- [X] T037 [P] [US2] Cobrir em `backend/tests/test_reservation_api.py` que dois envios com a mesma `chave_idempotencia` produzem `201` e depois `200`, **com o mesmo `id`** — uma reserva só (FR-023)
- [X] T038 [P] [US2] Cobrir em `backend/tests/test_reservation_api.py` que sessão em rascunho, cancelada ou já iniciada recusa a reserva com `404` (FR-002, FR-003)

### Implementação da User Story 2

- [X] T039 [US2] Criar `backend/apps/screening/services/reservas.py` com `criar_reserva(cliente, sessao, assentos, chave)` dentro de `transaction.atomic`, na ordem exata de data-model.md: valida a sessão → **bloqueia** as ocupações com `select_for_update` → apaga as vencidas / recusa as vivas → cria a reserva → cria as ocupações (FR-017, R2)
- [X] T040 [US2] Traduzir `IntegrityError` da inserção em recusa de negócio dentro de `backend/apps/screening/services/reservas.py`, com comentário registrando que é **resultado esperado**, não falha de sistema (R3)
- [X] T041 [US2] Resolver a idempotência em `backend/apps/screening/services/reservas.py` pela violação de `UNIQUE(idempotency_key)`, devolvendo a reserva existente — nunca por consulta prévia, que é o padrão que a concorrência quebra (R9)
- [X] T042 [US2] Acrescentar o serializer de entrada e o de reserva criada em `backend/apps/screening/serializers.py`, com `expira_em` como instante absoluto (contrato, FR-020)
- [X] T043 [US2] Acrescentar `ReservationCreateView` em `backend/apps/screening/views.py`, mapeando as recusas para `400`, `404` e `409` com as frases do contrato (FR-030)
- [X] T044 [US2] Registrar `reservas/` em `backend/apps/screening/urls.py` e **conferir que o servidor sobe**
- [X] T045 [P] [US2] Criar `frontend/app/api/reservar/route.ts` repassando corpo e cookie ao Django e devolvendo status e corpo **sem alterá-los**, no padrão de `frontend/app/api/entrar/route.ts` (contrato)
- [X] T046 [US2] Criar `frontend/components/seats/SelectionSummary.tsx` com quantidade, total e o botão de confirmar, impondo o limite de 6 e informando ao ser atingido (FR-013, FR-015)
- [X] T047 [US2] Gerar a `chave_idempotencia` **uma vez por seleção** em `frontend/components/seats/SelectionSummary.tsx`, não por clique (R9)
- [X] T048 [US2] Exibir a reserva confirmada em `frontend/app/sessoes/[id]/page.tsx`: lugares nomeados, até quando vale, e o caminho para o pagamento (FR-020, FR-028)
- [X] T049 [US2] Tratar o `409` em `frontend/app/sessoes/[id]/page.tsx` com a frase que nomeia o lugar perdido e recarregar o mapa — nada de erro genérico (FR-030, FR-031)
- [X] T050 [P] [US2] Cobrir em `frontend/tests/seats.test.tsx` a seleção e o desmarque, o limite de 6, o total exibido e a recusa por seleção vazia (FR-012, FR-013, FR-015)

**Checkpoint**: MVP completo. O cliente vê a sala, escolhe, reserva, e a corrida tem um vencedor
só — provado por teste.

---

## Phase 5: User Story 3 — Entrar para poder reservar (Priority: P2)

**Goal**: O visitante é conduzido à entrada e volta ao mesmo mapa; quem não compra recebe recusa
**do servidor**

**Independent Test**: Sem sessão ativa, abrir o mapa, tentar reservar, entrar com `cliente1` e
conferir que o retorno é para o mapa daquela sessão

### Testes da User Story 3

- [X] T051 [P] [US3] Cobrir em `backend/tests/test_reservation_api.py` que `organizador` e `portaria` recebem `403` ao chamar a API de reserva **diretamente**, sem passar pela interface (FR-024, FR-025, SC-005)
- [X] T052 [P] [US3] Cobrir em `backend/tests/test_reservation_api.py` que sem sessão ativa a resposta é `401` com "Entre para reservar." (FR-026)
- [X] T053 [P] [US3] Cobrir em `backend/tests/test_reservation_api.py` que `cliente2` recebe `404` — não `403` — ao pedir a reserva de `cliente1`, porque `403` confirmaria que ela existe (FR-027, SC-006)

### Implementação da User Story 3

- [X] T054 [US3] Criar a permissão `IsCustomer` em `backend/apps/screening/permissions.py`, decidindo pelo papel do usuário da sessão, e aplicá-la em `ReservationCreateView` (FR-024, Princípio IV)
- [X] T055 [US3] Acrescentar `ReservationDetailView` em `backend/apps/screening/views.py` filtrando pelo dono, e registrar `reservas/<int:pk>/` em `backend/apps/screening/urls.py` (FR-027)
- [X] T056 [US3] Conduzir a `/entrar?next=` a partir do `401` em `frontend/app/sessoes/[id]/page.tsx`, reaproveitando o retorno seguro já validado na `003` — sem introduzir destino externo
- [X] T057 [P] [US3] Cobrir em `frontend/tests/seats.test.tsx` que o visitante vê o mapa e que a confirmação sem sessão conduz à entrada com o motivo (FR-010, FR-026)

**Checkpoint**: a autorização é do servidor, e o caminho do visitante fecha.

---

## Phase 6: User Story 4 — Recuperar o lugar de quem não pagou (Priority: P2)

**Goal**: Passado o prazo, os lugares voltam ao estoque — sem rotina agendada

**Independent Test**: Criar uma reserva, forçar seu vencimento, e conferir que outro cliente
consegue reservar os mesmos lugares

### Testes da User Story 4

- [X] T058 [P] [US4] Cobrir em `backend/tests/test_reservation_api.py` que uma reserva vencida deixa seus lugares como `livre` no mapa, **sem** que nenhuma rotina tenha rodado (FR-021, SC-004)
- [X] T059 [P] [US4] Cobrir em `backend/tests/test_reservation_api.py` que outro cliente reserva os lugares vencidos com sucesso, e que a linha antiga foi removida — não duplicada (R2)
- [X] T060 [P] [US4] Cobrir em `backend/tests/test_reservation_api.py` que uma reserva **dentro** do prazo continua bloqueando os lugares para outro cliente (US4 cenário 4)
- [X] T061 [P] [US4] Cobrir em `backend/tests/test_reservation_api.py` que consultar uma reserva vencida devolve `situacao: expirada` com a frase de reescolha, e que ela não serve para prosseguir (FR-022)

### Implementação da User Story 4

- [X] T062 [US4] Filtrar ocupação viva por `expires_at > now()` em `backend/apps/screening/selectors.py` — a liberação é por consulta, não por processo agendado (spec, Assumptions)
- [X] T063 [US4] Devolver `situacao` derivada do vencimento em `ReservationDetailView` de `backend/apps/screening/views.py`, com a frase própria da reserva expirada (FR-022, FR-030)
- [X] T064 [US4] Exibir a contagem regressiva a partir do instante absoluto `expira_em`, e o estado de reserva expirada com o caminho para escolher de novo (FR-020, FR-030) — implementado em `frontend/components/seats/ReservationPanel.tsx`, não em `SelectionSummary.tsx` como a tarefa previa: o prazo só existe **depois** que a reserva é criada, e o resumo da seleção já não está em tela nessa hora

**Checkpoint**: o estoque não morre. As quatro user stories estão fechadas.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Provar que a garantia é real, que nada da 001–006 quebrou, e registrar a limitação

- [X] T065 **Provar que o teste de concorrência testa**: comentar a `UniqueConstraint` em `backend/apps/screening/models.py`, gerar e aplicar a migração, rodar `backend/tests/test_reservation_concurrency.py` e **confirmar que FALHA**. Desfazer alteração e migração em seguida, e registrar o resultado em `specs/007-seat-selection/quickstart.md` (R4, R12)
- [X] T066 [P] Varrer `frontend/components/seats/seats.module.css` e `frontend/app/sessoes/[id]/sessao.module.css` com os comandos de `specs/006-visual-identity/contracts/token-contract.md` e confirmar **zero** valores de cor, espaçamento, tipografia, raio ou duração fora dos tokens (FR-035)
- [X] T067 [P] Conferir o mapa em escala de cinza (emulação de acromatopsia) e registrar o resultado em `specs/007-seat-selection/quickstart.md` — os quatro estados continuam distinguíveis (SC-007)
- [X] T068 [P] Criar `frontend/tests/e2e/reserva.spec.ts` cobrindo o percurso filme → sessão → mapa → seleção → reserva confirmada (Princípio I)
- [X] T069 Rodar a suíte inteira do back-end e do front-end, confirmar que **nenhuma asserção das features 001–006 mudou** nem falhou, e anotar as contagens finais ao lado da linha de base em `specs/007-seat-selection/quickstart.md` (FR-033, FR-034, SC-012)
- [X] T070 Registrar em `README.md`, nas limitações conhecidas, que a expiração não é demonstrável ao vivo — prazo fixo de 10 minutos — e apontar qual teste prova o comportamento (spec, "Limitação assumida da demonstração")
- [X] T071 Percorrer `specs/007-seat-selection/quickstart.md` de ponta a ponta, incluindo a reprodução manual da corrida, e corrigir o que divergir do implementado — **a caminhada achou o que a suíte não achava**: a reserva devolvia `403` para cliente legítimo por exigência de CSRF da `SessionAuthentication`, invisível para o `Client()` de teste. Corrigido e coberto por `test_reserva_funciona_com_a_checagem_de_csrf_ligada`; registrado no quickstart

---

## Dependencies

```
Phase 1 (Setup)
   └─> Phase 2 (Foundational — a migração e a constraint)   ⚠️ bloqueia tudo
          ├─> Phase 3 (US1 — mapa)          P1 ─┐
          │                                     ├─> MVP
          └─> Phase 4 (US2 — reserva)       P1 ─┘
                 ├─> Phase 5 (US3 — autorização)   P2
                 └─> Phase 6 (US4 — expiração)     P2
                        └─> Phase 7 (Polish)
```

**Dependências entre stories**:

- **US1 e US2 são ambas P1** e se completam: a US2 depende do mapa da US1 para ter o que
  selecionar. Podem ser desenvolvidas em paralelo depois da Fase 2, mas só entregam juntas.
- **US3 depende da US2**: não há o que autorizar antes de existir criação de reserva.
- **US4 depende da US2**: não há o que expirar antes de existir reserva.
- **US3 e US4 são independentes entre si** e podem correr em paralelo.

**Dependências internas rígidas**:

- **T003 → T008 é uma unidade.** Nenhum commit intermediário pode conter modelo de ocupação sem a
  constraint. Se o trabalho for interrompido no meio, não commitar.
- **T033 e T034 vêm antes de T039.** O teste de concorrência escrito depois do serviço tende a
  ser escrito para passar, não para provar.
- **T065 só faz sentido depois de T033–T034 passarem.** É a verificação de que a prova prova.

## Parallel Execution Examples

**Fase 2** — depois de T010: `T011` e `T012` em arquivos diferentes.

**Fase 3** — os cinco testes de back-end `T013`–`T017` juntos; e no front, `T022`, `T024`, `T025`
tocam arquivos distintos.

**Fase 4** — `T035`–`T038` juntos (mesmo arquivo, mas casos independentes: escrever de uma vez).
`T045` e `T050` são de arquivos separados dos demais.

**Fase 5 e 6** podem correr em paralelo entre si, inteiras.

**Fase 7** — `T066`, `T067` e `T068` são independentes.

## Implementation Strategy

**MVP = Fases 1, 2, 3 e 4.** Ao fim da Fase 4 a feature entrega o que a constitution cobra: o
cliente escolhe onde sentar, reserva, e o banco garante que ninguém mais tem aquele lugar.

**Ordem sugerida de entrega incremental**:

1. **Fases 1–2** — a constraint existe. Nada visível, mas é o alicerce.
2. **Fase 3** — o mapa abre e é público. Já dá para avaliar a interface.
3. **Fase 4** — reserva funcionando, com a prova de concorrência verde.
4. **Fases 5–6** — autorização e expiração fecham as bordas.
5. **Fase 7** — a verificação de que a prova prova, e o registro das limitações.

**O ponto de não avançar**: se T065 passar em vez de falhar, **parar**. Um teste de concorrência
que passa sem a constraint não está provando o Princípio II, e seguir em frente com ele verde é
pior do que não tê-lo — dá segurança falsa exatamente onde o sistema mais depende de segurança
verdadeira.
