---
description: "Task list for feature implementation"
---

# Tasks: Pagamento Simulado e Emissão do Ingresso

**Input**: Design documents from `/specs/008-payment-ticket-issuance/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md),
[contracts/payment-ticket-api.md](./contracts/payment-ticket-api.md),
[quickstart.md](./quickstart.md)

**Tests**: **Sim, e três blocos deles não são opcionais.** A constitution exige o teste de
concorrência como prova do Princípio II (SC-004) e a rejeição de QR forjado como prova do
Princípio III (SC-010); a spec acrescenta que o de concorrência precisa **falhar** se a constraint
for removida (R4). A ordem é TDD nesses blocos: o teste que prova a garantia vem antes do serviço
que a implementa.

**Organization**: Cinco user stories. US1 (pagar e receber) e US2 (recusa) são ambas P1 e formam o
MVP — a constitution diz que "o caminho de recusa não é opcional", então entregar só a aprovação
não fecha o requisito de pagamento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (pagar e emitir), US2 (recusa), US3 (estados que não pagam), US4 (papéis),
  US5 (QR inforjável)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Domínio**: `backend/apps/screening/` — pagamento e ingresso são a continuação da venda (R12)
- **As garantias**: `backend/apps/screening/models.py` + a migração `0003`
- **A transação**: `backend/apps/screening/services/pagamentos.py`
- **A assinatura**: `backend/apps/screening/services/ingressos.py` — **puro, sem banco**
- **Front**: `frontend/app/pagamento/[id]/`, `frontend/components/payment/` e
  `frontend/components/tickets/`

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte, e declarar o segredo e os números que a feature usa

- [X] T001 Rodar `docker compose exec backend pytest` e `docker compose exec frontend npm run test` e conferir as contagens contra a linha de base já anotada em `specs/008-payment-ticket-issuance/quickstart.md` (202 back-end, 116 front-end) — é contra ela que SC-015 é medido no fim
- [X] T002 Acrescentar `qrcode` às dependências em `backend/pyproject.toml` — **sem** o extra `[pil]`, que arrastaria Pillow para desenhar quadrados (R11)
- [X] T003 Declarar `TICKET_SIGNING_KEY = env("TICKET_SIGNING_KEY")` em `backend/config/settings/base.py`, **sem valor padrão**, com comentário registrando que é segredo próprio e distinto da `SECRET_KEY` — vazar uma compromete sessões, vazar a outra compromete a catraca (FR-031, R5)
- [X] T004 Acrescentar `TICKET_SIGNING_KEY=` ao `.env.example` na seção Django, com o comando de geração e a advertência de que **precisa ser diferente** da `DJANGO_SECRET_KEY` (FR-031, quickstart.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Os dois modelos, as duas constraints, o estado `paid` — **na mesma migração** — e a
correção da regra de ocupação que a 007 deixou incompleta.

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar. E dentro dela,
T006–T011 formam **uma unidade indivisível**: nenhum commit pode existir com o modelo de pagamento
sem o de ingresso, nem com qualquer um deles sem a constraint que o protege — separar aprovação de
emissão é literalmente o que o Princípio II proíbe.

**⚠️ T012–T018 são a correção de R3**, e valem tanto quanto as constraints: é a única falha desta
feature que o banco aceita sem reclamar. Os testes vêm antes do conserto.

- [X] T005 Substituir a linha `Ticket permanece fora: emissão de ingresso é a próxima feature` no docstring de `backend/apps/screening/models.py` por nota registrando que `Payment` e `Ticket` nasceram na mesma migração, pelo mesmo motivo que `ReservedSeat` e sua constraint (data-model.md)
- [X] T006 Declarar `Payment` em `backend/apps/screening/models.py` com `reservation`, `status`, `decline_reason`, `amount`, `card_last4`, `card_brand`, `created_at` e a `UniqueConstraint(fields=["reservation"], condition=Q(status="approved"), name="um_pagamento_aprovado_por_reserva")` — **com `condition`**, e comentário explicando que o índice parcial é possível aqui porque o predicado é imutável, ao contrário do `now()` da 007 (R1)
- [X] T007 Declarar `Ticket` em `backend/apps/screening/models.py` com `public_id` (uuid), `reserved_seat` como **`OneToOneField`**, `payment` e `issued_at`, com comentário avisando que trocar por `ForeignKey` remove a garantia inteira sem mudar uma linha de lógica visível (R1, data-model.md)
- [X] T008 Acrescentar `PAID = "paid", "Paga"` a `Reservation.Status` em `backend/apps/screening/models.py`, com nota de que é estado **terminal** — não há estorno nesta feature (data-model.md)
- [X] T009 Declarar o predicado `Reservation.OCUPANDO = Q(status=PAID) | Q(expires_at__gt=Now())` em `backend/apps/screening/models.py`, com o comentário que registra por que os **dois** termos são necessários: só o prazo devolve o lugar vendido ao estoque, só o status exigiria a rotina agendada que a 007 evitou (R3)
- [X] T010 Gerar `backend/apps/screening/migrations/0003_*.py` com `makemigrations` e **conferir lendo o arquivo** que os dois modelos, as duas constraints e o novo estado estão todos nele — se saíram em migrações separadas, refazer (Princípio II)
- [X] T011 Aplicar a migração e verificar no banco que `um_pagamento_aprovado_por_reserva` aparece **com** `WHERE status = 'approved'` e que a unicidade de `reserved_seat_id` aparece **sem** cláusula `WHERE` — se estiver invertido, é a versão errada (quickstart.md)
- [X] T012 [P] Acrescentar a fixture `make_paid_reservation` em `backend/tests/conftest.py`, criando reserva com `status=paid` **sem** passar pelo serviço de pagamento, para que os testes de R3 não dependam da fase seguinte
- [X] T013 [P] Cobrir em `backend/tests/test_paid_seat_retention.py` que uma reserva **paga** com `expires_at` no passado continua exibindo seus lugares como `tomado` no mapa da sessão (R3, FR-018)
- [X] T014 [P] Cobrir em `backend/tests/test_paid_seat_retention.py` que outro cliente recebe `409` ao tentar reservar um lugar de reserva paga e vencida no relógio (R3, FR-018)
- [X] T015 Cobrir em `backend/tests/test_paid_seat_retention.py` que a linha de `ReservedSeat` de uma reserva paga e vencida no relógio **continua no banco** depois da tentativa do outro cliente — é o caminho que nenhuma constraint pega, porque apagar antes de inserir é operação legal (R3)
- [X] T016 Fazer `ocupacoes_vivas` em `backend/apps/screening/selectors.py` consumir `Reservation.OCUPANDO` em vez do filtro de vencimento, atualizando o docstring (R3)
- [X] T017 Fazer `Screening.seats_taken` em `backend/apps/screening/models.py` consumir `Reservation.OCUPANDO` em vez da cópia literal do filtro (R3)
- [X] T018 Fazer `_liberar_ou_recusar` em `backend/apps/screening/services/reservas.py` classificar as ocupações por `Reservation.OCUPANDO` e **nunca apagar ocupação de reserva paga**, com comentário registrando que a linha de uma reserva paga não é linha morta (R3)

**Checkpoint**: as duas constraints existem no banco e o lugar vendido não volta ao estoque —
provado por T013–T015. Ninguém paga nada ainda.

---

## Phase 3: User Story 1 — Pagar e receber o ingresso (Priority: P1) 🎯 MVP

**Goal**: A reserva vira compra, e a aprovação emite os ingressos na **mesma** transação

**Independent Test**: Como `cliente1`, reservar três lugares, pagar com `4242 4242 4242 4242` e
conferir que a confirmação traz **três** ingressos, cada um com seu lugar e seu QR distinto

**⚠️ Esta é a fase que a constitution vigia.** T019–T021 vêm **antes** do serviço: o teste de
concorrência escrito depois tende a ser escrito para passar, não para provar.

### Testes da User Story 1 — a prova do Princípio II

- [X] T019 [US1] Criar `backend/tests/test_payment_concurrency.py` com duas threads reais, **conexões de banco separadas**, `django_db(transaction=True)` e barreira sincronizando o ponto crítico: dois pagamentos da **mesma** reserva produzem exatamente uma aprovação e **um** conjunto de ingressos (R4, SC-004)
- [X] T020 [US1] Acrescentar em `backend/tests/test_payment_concurrency.py` as três asserções diretas no banco, que não dependem do código de resposta: nenhum par `(reserva)` com dois pagamentos aprovados, nenhum `reserved_seat` com dois ingressos, e **nenhuma reserva `paid` sem ingresso** — a última é o estado que o Princípio II proíbe pelo nome (SC-005)
- [X] T021 [US1] Acrescentar em `backend/tests/test_payment_concurrency.py` que dois pagamentos de reservas **diferentes** da mesma sessão aprovam **os dois** — o bloqueio é por reserva, não por sessão; sem isto, "resolver" a concorrência serializando a sala inteira passaria despercebido (R4)
- [X] T022 [P] [US1] Cobrir em `backend/tests/test_payment_api.py` que uma reserva de três lugares aprovada emite **três** ingressos, com três códigos distintos, um por assento (FR-014, FR-037, SC-003)
- [X] T023 [P] [US1] Cobrir em `backend/tests/test_payment_api.py` que a resposta `201` traz `pagamento` e `ingressos` na forma do contrato e **não contém** número de cartão, cvv, chave de assinatura, `id` interno de ingresso ou pagamento, nem dado de outro cliente (contrato, "campos proibidos")
- [X] T024 [P] [US1] Cobrir em `backend/tests/test_payment_api.py` que `GET /api/v1/reservas/<id>/` de uma reserva paga devolve `situacao: "paga"` com `pagamento` e `ingressos` — é o que faz a confirmação sobreviver a um recarregamento (US1-6, FR-022)

### Implementação da User Story 1

- [X] T025 [US1] Criar `backend/apps/screening/services/ingressos.py` com `assinar_codigo(public_id, screening_id)` e `verificar_codigo(codigo)` usando `django.core.signing` com `key=settings.TICKET_SIGNING_KEY` e `salt="ingresso.qr"` — **o arquivo não importa nenhum modelo**, e o docstring registra que essa ausência é o que torna `num_queries == 0` verificável em vez de aspiracional (R5, R7)
- [X] T026 [US1] Acrescentar `qr_data_uri(codigo)` em `backend/apps/screening/services/ingressos.py`, gerando **SVG** com `qrcode` e devolvendo `data:image/svg+xml;base64,...` para entrar num `<img>` sem `dangerouslySetInnerHTML` (R11)
- [X] T027 [US1] Criar `backend/apps/screening/services/pagamentos.py` com `pagar(cliente, reserva, cartao)` dentro de `transaction.atomic`, na ordem exata de data-model.md: **bloqueia** a reserva com `select_for_update` → revalida sob o bloqueio → autoriza → aprovado: grava `Payment`, marca a reserva `paid` e cria um `Ticket` por `ReservedSeat` (FR-013, FR-020, R2)
- [X] T028 [US1] Criar os ingressos em `bulk_create` dentro de `backend/apps/screening/services/pagamentos.py`, com `select_related` nas ocupações — a emissão não pode fazer uma consulta por ingresso (plan.md, Performance Goals)
- [X] T029 [US1] Traduzir a violação de `um_pagamento_aprovado_por_reserva` em `backend/apps/screening/services/pagamentos.py` para a recusa "esta reserva já foi paga", com comentário registrando que é **resultado esperado**, não falha de sistema — como na 007 (R1, R3 da 007)
- [X] T030 [US1] Acrescentar em `backend/apps/screening/serializers.py` o serializer de entrada do cartão e os de `Payment` e `Ticket`, com `codigo` e `qr_svg` juntos e **sem** `id` interno de nenhum dos dois (contrato)
- [X] T031 [US1] Ampliar o serializer de reserva em `backend/apps/screening/serializers.py` para incluir `pagamento` e `ingressos` quando a reserva estiver paga, **sem alterar nome nem significado de nenhum campo existente** (FR-050, contrato)
- [X] T032 [US1] Acrescentar `PaymentCreateView` em `backend/apps/screening/views.py` e registrar `reservas/<int:pk>/pagamento/` em `backend/apps/screening/urls.py` — **conferir que o servidor sobe** antes de seguir
- [X] T033 [P] [US1] Criar `frontend/app/api/pagar/route.ts` repassando corpo e cookie ao Django e devolvendo status e corpo **sem alterá-los**, no padrão de `frontend/app/api/reservar/route.ts`, com comentário registrando que é o único ponto por onde o número do cartão passa — e que passa **sem parar** (contrato, R10)
- [X] T034 [P] [US1] Acrescentar os tipos `Pagamento`, `Ingresso` e `RespostaPagamento` em `frontend/lib/types.ts`, espelhando o contrato
- [X] T035 [US1] Acrescentar `pagarReserva(...)` e `buscarReserva(id)` em `frontend/lib/api.ts`, seguindo o padrão de erro e degradação já usado pelos demais consumidores
- [X] T036 [P] [US1] Criar `frontend/components/payment/ResumoDaCompra.tsx` com filme, sessão, sala, lugares, valor unitário, total e o prazo restante (FR-002)
- [X] T037 [P] [US1] Criar `frontend/components/payment/FormularioDeCartao.tsx` com número, nome, validade e cvv, operável só por teclado e com o resultado anunciado a tecnologias assistivas (FR-047)
- [X] T038 [P] [US1] Criar `frontend/components/tickets/Ingresso.tsx` exibindo o QR em `<img>` com `alt` **e o código em texto ao lado** — é o texto que a portaria digita quando a câmera falha (FR-038)
- [X] T039 [US1] Criar `frontend/app/pagamento/[id]/page.tsx` e `pagamento.module.css` resolvendo os quatro estados da rota única — viva, paga, vencida, não encontrada (R13) —, declarando em `frontend/styles/tokens.css` os tokens novos que forem necessários, sem remover nem renomear nenhum existente (FR-051)

**Checkpoint**: o cliente paga e recebe os ingressos, e a corrida tem um vencedor só — provado por
teste. Metade do requisito de pagamento está entregue.

---

## Phase 4: User Story 2 — Entender a recusa e tentar de novo (Priority: P1) 🎯 MVP

**Goal**: Os três motivos de recusa são alcançáveis de propósito, com frase própria, e o lugar
continua com quem tentou

**Independent Test**: Com uma reserva viva, pagar com cada um dos três cartões de recusa e conferir
três mensagens **distintas**; em seguida pagar com o cartão aprovado e conferir a emissão normal

**Por que também é P1**: a constitution diz que "o caminho de recusa não é opcional" e que os dois
caminhos DEVEM ser exercitáveis pelo avaliador. Sem esta fase, metade do requisito de pagamento não
existe.

### Testes da User Story 2

- [X] T040 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que os três cartões de recusa produzem `402` com três valores de `motivo` e três frases **diferentes** — assim a tabela não pode ser silenciosamente reduzida a um caminho só (FR-008, FR-009, SC-006)
- [X] T041 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que uma recusa **não altera** `expires_at` nem `status` da reserva, e que `expira_em` volta no corpo do `402` com o valor original (FR-026, FR-027)
- [X] T042 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que os lugares continuam `tomado` no mapa depois de uma recusa, e que outro cliente continua recebendo `409` neles (FR-026, SC-007)
- [X] T043 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que depois de recusas seguidas uma tentativa aprovada dentro do prazo emite **um único** conjunto de ingressos (FR-028, US2-6)
- [X] T044 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que número mal formado devolve `400` — **não** `402` —, que **nenhum** `Payment` é gravado, e que o número enviado **não** aparece no corpo da resposta (FR-010, FR-011, R10)
- [X] T045 [P] [US2] Cobrir em `backend/tests/test_payment_api.py` que toda tentativa recusada **fica gravada** com seu motivo, e que o registro sobrevive à resposta — é o que prova que a recusa não está subindo como exceção dentro de `atomic()` (FR-012, R8)

### Implementação da User Story 2

- [X] T046 [US2] Declarar a tabela de cartões em `backend/config/settings/base.py` — os três números de recusa mapeados para seus motivos —, com comentário registrando que é contrato com o README e que sorteio foi descartado por não ser exercitável nem testável (FR-006, FR-007, R9)
- [X] T047 [US2] Criar o autorizador simulado em `backend/apps/screening/services/pagamentos.py`: normaliza o número, valida a forma por Luhn e decide pela tabela — número mal formado é **erro de preenchimento**, não recusa (FR-005, FR-006, FR-010)
- [X] T048 [US2] Fazer a recusa ser **retorno**, não exceção, em `backend/apps/screening/services/pagamentos.py`, gravando `Payment(declined)` que sobrevive à transação, com comentário registrando que como exceção ela desfaria o próprio registro no rollback (R8, FR-012)
- [X] T049 [US2] Mapear a recusa para `402` com `motivo`, `detail` e `expira_em` em `backend/apps/screening/views.py`, e guardar só `card_last4` e `card_brand` — nunca o número, nunca o cvv (contrato, FR-011)
- [X] T050 [US2] Exibir a recusa em `frontend/app/pagamento/[id]/page.tsx` com a frase do servidor, mantendo o formulário preenchível para nova tentativa e a contagem regressiva correndo do mesmo instante — e distinguir visualmente o `400` de preenchimento do `402` de cobrança (FR-028, FR-045, FR-046)

**Checkpoint**: MVP completo. Os dois caminhos do pagamento existem e são exercitáveis pelo
avaliador seguindo apenas o README.

---

## Phase 5: User Story 3 — Não pagar o que já venceu (Priority: P2)

**Goal**: Reserva vencida, já paga, cancelada ou de sessão indisponível não vira cobrança

**Independent Test**: Criar uma reserva, forçar seu vencimento, tentar pagar e conferir que a
cobrança é recusada, que nenhum ingresso é emitido e que a mensagem explica o que fazer

### Testes da User Story 3

- [X] T051 [P] [US3] Cobrir em `backend/tests/test_payment_api.py` que uma reserva vencida devolve `409` com `situacao: "expirada"` e que **nenhum** ingresso e **nenhum** `Payment` aprovado são criados (FR-023)
- [X] T052 [P] [US3] Cobrir em `backend/tests/test_payment_api.py` que pagar duas vezes a mesma reserva devolve `409` com `situacao: "paga"` na segunda, **com o mesmo conjunto de ingressos** da primeira (FR-022, US3-4)
- [X] T053 [P] [US3] Cobrir em `backend/tests/test_payment_api.py` que reserva cancelada e sessão cancelada ou já iniciada recusam com `409` e frase própria (FR-024, FR-025)
- [X] T054 [P] [US3] Cobrir em `backend/tests/test_payment_api.py` que a recusa por vencimento vem do **servidor** mesmo com a requisição feita direto na API, sem front-end no caminho (FR-029)

### Implementação da User Story 3

- [X] T055 [US3] Revalidar `é do cliente · não vencida · não paga · sessão vendável` **depois** do `select_for_update` em `backend/apps/screening/services/pagamentos.py` — ler o estado antes de travar é o padrão que a concorrência quebra (data-model.md)
- [X] T056 [US3] Mapear os três estados para `409` com `situacao` e frase própria em `backend/apps/screening/views.py`, conforme a tabela do contrato (FR-045)
- [X] T057 [US3] Exibir em `frontend/app/pagamento/[id]/page.tsx` o estado de reserva vencida com o caminho de volta ao mapa, e o de reserva já paga levando aos ingressos existentes em vez de a um formulário inútil (FR-045, R13)

**Checkpoint**: a expiração da 007 deixa de ser ficção. Nada que não possa ser pago é cobrado.

---

## Phase 6: User Story 4 — Pagar só o que é seu (Priority: P2)

**Goal**: Só o papel cliente paga, e só o dono paga a sua — a recusa é do servidor

**Independent Test**: Com a reserva de `cliente1` viva, tentar pagá-la como `cliente2`, como
organizador e como portaria, e conferir três recusas do servidor

### Testes da User Story 4

- [X] T058 [P] [US4] Cobrir em `backend/tests/test_payment_api.py` que `organizador` e `portaria` recebem `403` ao chamar a API de pagamento **diretamente**, sem passar pela interface (FR-041, FR-042, SC-012)
- [X] T059 [P] [US4] Cobrir em `backend/tests/test_payment_api.py` que `cliente2` recebe `404` — não `403` — ao tentar pagar a reserva de `cliente1`, porque um `403` confirmaria que ela existe (FR-040, FR-043)
- [X] T060 [P] [US4] Cobrir em `backend/tests/test_payment_api.py` que sem sessão ativa a resposta é `401` com "Entre para concluir o pagamento." e que **nenhuma** cobrança é registrada (FR-044)
- [X] T061 [P] [US4] Cobrir em `backend/tests/test_payment_api.py` que `cliente2` não alcança os ingressos de `cliente1` por nenhum caminho da API (FR-043)
- [X] T062 [P] [US4] Cobrir em `backend/tests/test_payment_api.py` que o pagamento funciona com a checagem de CSRF ligada, no molde de `test_reserva_funciona_com_a_checagem_de_csrf_ligada` — foi essa falha que a caminhada manual da 007 pegou e a suíte inteira não pegava (quickstart.md da 007)

### Implementação da User Story 4

- [X] T063 [US4] Aplicar `IsCustomer` em `PaymentCreateView` e acrescentar a mensagem própria do pagamento em `backend/apps/screening/permissions.py` — "Apenas clientes podem pagar reservas.", distinta da frase da reserva (FR-039, FR-041)
- [X] T064 [US4] Filtrar a reserva pelo dono em `backend/apps/screening/views.py` e traduzir `NotAuthenticated` em `401` com a frase do pagamento, reaproveitando `ReservationViewBase` da 007 (FR-040, FR-044)

**Checkpoint**: a autorização é do servidor em todos os caminhos novos.

---

## Phase 7: User Story 5 — Um QR que não dá para forjar (Priority: P2)

**Goal**: Provar que o código assinado resiste a adulteração e a assinatura com outro segredo

**Independent Test**: Tomar o código de um ingresso emitido, alterar um caractere e conferir que a
verificação rejeita; gerar um código com outro segredo e conferir que também rejeita, sem que o
banco tenha sido consultado

**Nota de dependência**: a US1 **constrói** a assinatura porque não há como emitir ingresso sem
ela; esta fase é onde ela é **atacada**. As duas primeiras tarefas são a prova do Princípio III e
não são diferenciais.

### Testes da User Story 5 — a prova do Princípio III

- [X] T065 [US5] Criar `backend/tests/test_ticket_signature.py` cobrindo que um código com **um caractere alterado** é rejeitado, em cada posição relevante — conteúdo e assinatura (FR-035, SC-010)
- [X] T066 [US5] Acrescentar em `backend/tests/test_ticket_signature.py` que um código **assinado com outro segredo**, com conteúdo perfeitamente bem formado, é rejeitado — só a assinatura não confere, e é só isso que importa (FR-036, SC-010)
- [X] T067 [US5] Acrescentar em `backend/tests/test_ticket_signature.py` a verificação de um código adulterado dentro de `django_assert_num_queries(0)` — se alguém acrescentar uma consulta, nem que seja um `.exists()` de conveniência, o teste quebra e diz por quê (FR-034, R7)
- [X] T068 [P] [US5] Acrescentar em `backend/tests/test_ticket_signature.py` que o código carrega a **identidade da sessão** e a identidade pública do ingresso, e que essa identidade é UUID — nunca a chave primária (FR-032, FR-033)
- [X] T069 [P] [US5] Acrescentar em `backend/tests/test_ticket_signature.py` que dois ingressos da mesma reserva têm códigos distintos e que nenhum permite deduzir o outro (FR-037)

### Implementação da User Story 5

- [X] T070 [US5] Conferir que `backend/apps/screening/services/ingressos.py` continua sem importar modelo algum e que `verificar_codigo` não recebe `request` nem sessão — no dia em que importar, `num_queries == 0` deixa de ser garantido pela estrutura e passa a depender de disciplina (plan.md, Post-Design Re-check)

**Checkpoint**: o QR nasce inforjável, e a feature da portaria pode ser construída sobre ele.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Provar que as garantias são reais, que nada da 001–007 quebrou, e deixar o avaliador
capaz de percorrer os dois caminhos sozinho

- [X] T071 **Provar que o teste de concorrência testa**: comentar a `UniqueConstraint` `um_pagamento_aprovado_por_reserva` em `backend/apps/screening/models.py`, gerar e aplicar a migração, rodar `backend/tests/test_payment_concurrency.py` e **confirmar que FALHA**. Desfazer alteração e migração, e registrar o resultado em `specs/008-payment-ticket-issuance/quickstart.md` (R4)
- [X] T072 **Provar a segunda garantia**: trocar `OneToOneField` por `ForeignKey` em `Ticket`, gerar e aplicar a migração, e confirmar que `backend/tests/test_payment_concurrency.py` **FALHA** — é a forma mais fácil de remover a garantia sem perceber, porque não muda uma linha de lógica visível. Desfazer e registrar no quickstart (R1)
- [X] T073 [P] Varrer `frontend/app/pagamento/[id]/pagamento.module.css`, `frontend/components/payment/payment.module.css` e `frontend/components/tickets/tickets.module.css` com os comandos de `specs/006-visual-identity/contracts/token-contract.md` e confirmar **zero** valores de cor, espaçamento, tipografia, raio ou duração fora dos tokens (FR-051)
- [X] T074 [P] Cobrir em `frontend/tests/pagamento.test.tsx` os estados da rota — revisão, recusa com frase do servidor, vencida e paga —, que nenhum exibe texto genérico nem área em branco, e que o formulário é operável só por teclado (FR-045, FR-046, FR-047)
- [X] T075 [P] Cobrir em `frontend/tests/ingresso.test.tsx` que cada ingresso exibe o QR **e** o código em texto, e que uma reserva de três lugares rende três ingressos na tela (FR-014, FR-038)
- [X] T076 [P] Criar `frontend/tests/e2e/pagamento.spec.ts` cobrindo o percurso mapa → reserva → pagamento recusado → nova tentativa aprovada → ingresso com QR (Princípio I)
- [X] T077 Atualizar `README.md` com a variável `TICKET_SIGNING_KEY` (e a advertência de que precisa ser diferente da `DJANGO_SECRET_KEY`), a **tabela de cartões de teste** com os quatro números e seus desfechos, e a nota de que a reserva paga não volta ao estoque — sem a tabela, o avaliador não tem como alcançar a recusa (FR-007, FR-052, Princípio VI)
- [X] T078 Rodar a suíte inteira do back-end e do front-end, confirmar que **nenhuma asserção das features 001–007 mudou** nem falhou, anotar as contagens finais ao lado da linha de base em `specs/008-payment-ticket-issuance/quickstart.md`, e então percorrer o quickstart de ponta a ponta — incluindo a corrida manual e as duas tentativas de forjar o QR — corrigindo o que divergir do implementado (FR-049, FR-050, SC-015)

---

## Dependencies

```
Phase 1 (Setup)
   └─> Phase 2 (Foundational — os modelos, as duas constraints, e a correção de R3)  ⚠️ bloqueia tudo
          ├─> Phase 3 (US1 — pagar e emitir)   P1 ─┐
          │                                        ├─> MVP
          └─> Phase 4 (US2 — recusa)           P1 ─┘
                 ├─> Phase 5 (US3 — estados que não pagam)   P2
                 ├─> Phase 6 (US4 — papéis)                  P2
                 └─> Phase 7 (US5 — QR inforjável)           P2
                        └─> Phase 8 (Polish)
```

**Dependências entre stories**:

- **US1 e US2 são ambas P1** e se completam: a US2 reaproveita a transação da US1 e acrescenta o
  caminho de recusa. Entregar só a US1 deixaria metade do requisito de pagamento fora.
- **US3 depende da US1**: não há o que recusar por estado antes de existir cobrança.
- **US4 depende da US1**: não há o que autorizar antes de existir endpoint de pagamento.
- **US5 depende da US1** para ter código emitido a atacar — a US1 **constrói** a assinatura, a US5
  a **ataca**.
- **US3, US4 e US5 são independentes entre si** e podem correr em paralelo.

**Dependências internas rígidas**:

- **T006 → T011 é uma unidade.** Nenhum commit intermediário pode conter o modelo de pagamento sem
  o de ingresso, nem qualquer um deles sem sua constraint. Se o trabalho for interrompido no meio,
  não commitar.
- **T013–T015 vêm antes de T016–T018.** A correção de R3 escrita antes do teste tende a ser
  escrita para o caso que a pessoa lembrou, não para os três.
- **T019–T021 vêm antes de T027.** Mesma razão da 007: teste de concorrência escrito depois do
  serviço tende a ser escrito para passar.
- **T046 antes de T047.** A tabela é o contrato; o autorizador só a consome.
- **T071 e T072 só fazem sentido depois de T019–T021 passarem.** São a verificação de que a prova
  prova.
- **T077 é pré-requisito da avaliação, não polimento.** Sem a tabela de cartões no README, o
  caminho de recusa é inalcançável para quem não leu o código — e a constitution exige que ele seja
  exercitável.

## Parallel Execution Examples

**Fase 2** — depois de T011: `T012`, `T013` e `T014` em paralelo. `T015` depende de `T014` (mesmo
cenário). `T016`, `T017` e `T018` tocam três arquivos distintos e podem correr juntas depois dos
testes.

**Fase 3** — `T022`, `T023` e `T024` juntos (mesmo arquivo, casos independentes: escrever de uma
vez). No front, `T033`, `T034`, `T036`, `T037` e `T038` tocam arquivos distintos.

**Fase 4** — os seis testes `T040`–`T045` juntos.

**Fases 5, 6 e 7** podem correr em paralelo entre si, inteiras.

**Fase 8** — `T073`, `T074`, `T075` e `T076` são independentes. `T071` e `T072` são sequenciais
entre si: as duas mexem em migração.

## Implementation Strategy

**MVP = Fases 1, 2, 3 e 4.** Ao fim da Fase 4 a feature entrega o que a constitution cobra: o
cliente paga, recebe um ingresso por assento com QR assinado, e o caminho de recusa é exercitável
de propósito.

**Ordem sugerida de entrega incremental**:

1. **Fases 1–2** — as constraints existem e o lugar vendido não volta ao estoque. Nada visível,
   mas é onde mora o risco.
2. **Fase 3** — pagamento aprovado emitindo ingressos, com a prova de concorrência verde.
3. **Fase 4** — os três motivos de recusa, e o MVP fecha.
4. **Fases 5–7** — estados, papéis e a prova de que o QR não se forja.
5. **Fase 8** — a verificação de que as provas provam, e o README que torna tudo alcançável.

**Dois pontos de não avançar**:

- **Se T071 ou T072 passar em vez de falhar, parar.** Um teste de concorrência que passa sem a
  constraint está provando que o `SELECT FOR UPDATE` funciona, não que a garantia é do banco — e
  seguir com ele verde é pior do que não tê-lo.
- **Se T013–T015 passarem antes de T016–T018, parar e reler.** Eles precisam falhar contra o
  código atual: uma reserva paga e vencida no relógio **é** tratada como abandonada hoje. Se
  passarem de primeira, o cenário não está sendo montado — provavelmente a fixture não está
  forçando `expires_at` para o passado.
