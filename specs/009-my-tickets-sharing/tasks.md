---
description: "Task list for feature implementation"
---

# Tasks: Meus Ingressos e Compartilhamento por Link

**Input**: Design documents from `/specs/009-my-tickets-sharing/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/my-tickets-api.md](./contracts/my-tickets-api.md),
[quickstart.md](./quickstart.md)

**Tests**: **Sim, e quatro deles não são opcionais.** O Princípio III exige a prova de que o link não
vaza nada além do ingresso (FR-042); o Princípio II exige que a unicidade do link ativo seja do banco
e prove-se sob concorrência (FR-029); SC-010 exige a prova de que revogar não toca o código do QR; e
a armadilha herdada (R10) só é pega por teste, porque nenhuma constraint reclama dela. Nesses quatro
a ordem é TDD: o teste vem antes do código que ele guarda.

**Organization**: Sete user stories, seis delas P1. O MVP é US1 + US2 + US3 — a área alcançável com
o QR legível —, porque é ela que fecha a metade "Meus ingressos" da etapa 4 da constitution. US4–US6
fecham a outra metade, o compartilhamento, e são indivisíveis entre si: **não existe entregar o link
sem a revogação**, porque um link ao portador sem revogação é uma credencial que não se pode
cancelar.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (lista), US2 (estado vazio), US3 (QR legível), US4 (gerar e abrir link),
  US5 (não vazar), US6 (revogar), US7 (papéis e posse)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Domínio**: `backend/apps/screening/` — o link pende do `Ticket`, então mora na app dele
- **A garantia**: `backend/apps/screening/models.py` + a migração `0004`
- **A escrita**: `backend/apps/screening/services/compartilhamento.py` — **arquivo novo**, porque
  `services/ingressos.py` é puro e não pode ganhar acesso ao banco (R15, plan.md)
- **As consultas**: `backend/apps/screening/selectors.py` — e **nenhuma delas usa `sellable()`** (R10)
- **Front**: `frontend/app/meus-ingressos/`, `frontend/app/ingresso/[token]/` e
  `frontend/components/tickets/`

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte, e confirmar que esta feature não precisa de nada novo

- [X] T001 Rodar `docker compose exec backend pytest`, `docker compose exec frontend npm run test` e `npx playwright test`, conferindo contra a linha de base registrada em `specs/008-payment-ticket-issuance/quickstart.md` (**288** back-end, **137** front-end em 9 arquivos, **32** e2e) — é contra ela que SC-019 é medido no fim
- [X] T002 Confirmar em `backend/config/settings/base.py` que `SITE_URL` já existe (linha 167) e é o que monta o endereço público do link — **nenhuma variável de ambiente nova entra nesta feature**, e o `.env.example` não muda (contracts/my-tickets-api.md)
- [X] T003 Confirmar que `backend/pyproject.toml` e `frontend/package.json` **não** precisam de alteração: o token é `secrets.token_urlsafe`, biblioteca padrão, e o QR reaproveita o `qrcode` que a 008 já trouxe (R15)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: O modelo do link com sua constraint — na mesma migração — e as consultas de leitura que
todas as histórias consomem.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

**⚠️ T004–T008 são uma unidade indivisível.** Nenhum commit pode conter `TicketShareLink` sem
`um_link_ativo_por_ingresso`. É a mesma regra que fez a 007 criar `ReservedSeat` com sua constraint e
a 008 criar pagamento com emissão. Aqui a consequência de separar é menor que nas duas anteriores —
nenhum assento é vendido duas vezes por causa de um link —, mas abrir exceção na regra é como as
regras acabam.

**⚠️ T009–T013 são a defesa contra a armadilha herdada (R10)**, e os testes vêm antes das consultas.
Escrever o selector primeiro e o teste depois produz um teste escrito para o que o selector faz, não
para o que a spec exige.

- [X] T004 Declarar `TicketShareLink` em `backend/apps/screening/models.py` com `ticket` (FK → `Ticket`, **`on_delete=CASCADE`**), `token` (`CharField(64)`, `unique=True`, `editable=False`), `created_at` e `revoked_at` (nulável, default `None`), com comentário registrando por que o `CASCADE` diverge do `PROTECT` usado no resto do projeto: link é autorização de leitura, não histórico de venda, e um link sobrevivendo ao ingresso seria credencial órfã (data-model.md)
- [X] T005 Acrescentar a `TicketShareLink.Meta.constraints` a `UniqueConstraint(fields=["ticket"], condition=Q(revoked_at__isnull=True), name="um_link_ativo_por_ingresso")`, com comentário registrando que o índice parcial é possível porque `revoked_at IS NULL` é imutável — terceiro capítulo da sequência 007 (absoluta, `now()` não é imutável) → 008 (parcial) → 009 (parcial) — e que uma `UNIQUE` sem condição impediria gerar link depois de revogar, que é o que FR-032 promete (R2, data-model.md)
- [X] T006 Escrever no docstring de `backend/apps/screening/models.py` a nota de que `TicketShareLink` e sua constraint nasceram na mesma migração, e de que o token do link **não** deriva do código do QR e não conhece a `TICKET_SIGNING_KEY` — os dois segredos têm ciclos de vida independentes (decisão 2 da spec)
- [X] T007 Gerar `backend/apps/screening/migrations/0004_*.py` com `makemigrations` e **conferir lendo o arquivo** que o modelo e a constraint estão no mesmo arquivo; se saíram separados, refazer
- [X] T008 Aplicar a migração e verificar no banco com `\d screening_ticketsharelink` que `um_link_ativo_por_ingresso` aparece **com** `WHERE (revoked_at IS NULL)` e que a unicidade de `token` aparece **sem** cláusula `WHERE` — invertido, um token revogado poderia ser reemitido e FR-031 cai (quickstart.md)
- [X] T009 [P] Acrescentar a `backend/tests/conftest.py` uma fixture que cria ingressos emitidos para um cliente em **três** sessões: uma futura, uma já iniciada e uma cancelada — é o cenário que todos os testes de R10 consomem
- [X] T010 [P] Cobrir em `backend/tests/test_my_tickets_api.py` que o ingresso de uma sessão **já iniciada** aparece na resposta, no grupo `passados` (FR-009) — deve **falhar** enquanto o selector não existir
- [X] T011 [P] Cobrir em `backend/tests/test_my_tickets_api.py` que o ingresso de uma sessão **cancelada** aparece na resposta, com `sessao_cancelada: true` (FR-011) — é o pior caso da armadilha, porque some justamente o ingresso que precisa de explicação
- [X] T012 Escrever `selectors.ingressos_do_cliente(cliente)` em `backend/apps/screening/selectors.py` devolvendo dois conjuntos — futuros por `starts_at` crescente e passados por `starts_at` decrescente —, filtrando **apenas** por `reserved_seat__reservation__customer`, com docstring registrando explicitamente que **não pode usar `sellable()` nem `get_sellable_screening`**: é filtro de estoque, e usá-lo aqui esvazia o grupo dos passados e faz sumir a sessão cancelada (R10)
- [X] T013 Acrescentar em `selectors.ingressos_do_cliente` o `select_related("reserved_seat__seat", "reserved_seat__screening__movie", "reserved_seat__screening__room")` e a ordenação **explícita** por `reserved_seat__screening__starts_at`, com comentário de que herdar `Ticket.Meta.ordering` daria uma lista ordenada por poltrona — plausível e errada (R10 corolário, R11)
- [X] T014 [P] Escrever `selectors.ingresso_do_dono(cliente, public_id)` em `backend/apps/screening/selectors.py`, filtrando por `public_id` **e** dono na mesma consulta, devolvendo `None` para ingresso alheio (R12)
- [X] T015 [P] Escrever `selectors.ingresso_por_token(token)` em `backend/apps/screening/selectors.py` filtrando por `token` **e** `revoked_at__isnull=True`, com docstring registrando que token inexistente e token revogado convergem para o mesmo `None` **na consulta** — a mesma técnica de `get_sellable_screening` da 007, porque quando os casos convergem cedo não sobra caminho por onde a distinção vaze (FR-043)

**Checkpoint**: as constraints existem, as consultas devolvem passado e sessão cancelada, e T010–T011
passam. Nada visível ainda.

---

## Phase 3: US1 — Voltar ao próprio ingresso (P1)

**Goal**: O cliente entra na conta e reencontra seus ingressos, com o da próxima sessão no topo.

**Independent Test**: Autenticado como `cliente1`, com ingressos de uma sessão futura e de uma
passada, abrir "Meus ingressos" e conferir que o da próxima sessão é o primeiro e que o passado
aparece separado.

- [X] T016 [P] [US1] Cobrir em `backend/tests/test_my_tickets_api.py` que a resposta traz `futuros` e `passados` como listas separadas, e que uma compra de dois lugares produz **dois** itens, um por lugar (FR-004)
- [X] T017 [P] [US1] Cobrir em `backend/tests/test_my_tickets_api.py` que `futuros` vem em ordem **crescente** de sessão e `passados` em ordem **decrescente**, com pelo menos três sessões distintas (FR-007, FR-008, SC-002)
- [X] T018 [P] [US1] Cobrir em `backend/tests/test_my_tickets_api.py`, com `django_assert_num_queries`, que a lista de 12 ingressos não faz uma consulta por ingresso — o teste falha se o `select_related` de T013 for removido (R11)
- [X] T019 [US1] Escrever `MeuIngressoSerializer` em `backend/apps/screening/serializers.py` **compondo** o `TicketSerializer` da 008 e acrescentando `id` (`public_id`), `grupo` e `sessao_cancelada`, com docstring registrando que o `TicketSerializer` **não pode ganhar campo nenhum**: o risco não é o que ele expõe hoje, é a pressão de crescimento, e um campo novo lá aparece na página pública no mesmo commit (R6, FR-058)
- [X] T020 [US1] Escrever `IsCustomerParaIngressos` em `backend/apps/screening/permissions.py`, subclasse de `IsCustomer` só para a mensagem "Apenas clientes têm ingressos." — a frase da reserva descreveria outra tela, que o Princípio V proíbe (R12)
- [X] T021 [US1] Escrever `MyTicketsView` em `backend/apps/screening/views.py` para `GET /api/v1/meus-ingressos/`, com `handle_exception` traduzindo `NotAuthenticated` em `401` com "Entre para ver seus ingressos." — sem a tradução o DRF devolve `403` e o front não sabe se conduz à entrada ou explica o papel (R12, FR-051)
- [X] T022 [US1] Registrar `meus-ingressos/` em `backend/apps/screening/urls.py`
- [X] T023 [P] [US1] Acrescentar os tipos `MeuIngresso` e `ListaDeIngressos` em `frontend/lib/types.ts`
- [X] T024 [US1] Acrescentar `fetchMeusIngressos(sessionKey)` em `frontend/lib/api.ts`, seguindo o padrão de `fetchReserva`
- [X] T025 [US1] Escrever `frontend/app/meus-ingressos/page.tsx` como Server Component, com `dynamic = "force-dynamic"`, redirecionando visitante para `/entrar?next=/meus-ingressos` e renderizando os dois grupos na ordem que o servidor mandou — **sem reordenar nem recomparar datas no cliente** (FR-010)
- [X] T026 [US1] Escrever `frontend/app/meus-ingressos/meus-ingressos.module.css` com títulos de seção para os dois grupos, distinguindo-os **sem depender só de cor** (FR-006), usando exclusivamente tokens da 006 (FR-059)
- [X] T027 [US1] Marcar o ingresso de sessão cancelada com aviso em português na lista, a partir de `sessao_cancelada` (FR-011)
- [X] T028 [US1] Acrescentar o item "Meus ingressos" ao `frontend/components/header/AccountMenu.tsx`, como `role="menuitem"`, visível **apenas** quando `sessao.papel === "customer"` (FR-002, R14)
- [X] T029 [US1] Acrescentar em `frontend/app/pagamento/[id]/page.tsx`, no estado pago, um caminho para `/meus-ingressos` (FR-003)
- [X] T030 [P] [US1] Cobrir em `frontend/tests/meus-ingressos.test.tsx` a ordem dos grupos, a contagem de itens e o aviso de sessão cancelada

**Checkpoint**: US1 entregue e testável sozinha.

---

## Phase 4: US2 — Estado vazio de quem ainda não comprou (P1)

**Goal**: O cliente sem ingressos lê uma frase escrita para gente, e sai dali para o catálogo.

**Independent Test**: Autenticado como `cliente2`, abrir "Meus ingressos" e conferir texto em
português e caminho para o catálogo.

- [X] T031 [P] [US2] Cobrir em `backend/tests/test_my_tickets_api.py` que um cliente sem ingressos recebe `200` com `{"futuros": [], "passados": []}` — **não** `404` e **não** `204`: o estado vazio é uma tela, não a ausência de um recurso (contracts/my-tickets-api.md)
- [X] T032 [US2] Escrever o estado vazio em `frontend/app/meus-ingressos/page.tsx`, exibido **apenas** quando os dois grupos estão vazios, com frase em português dizendo o que houve e a próxima ação, e caminho para o catálogo a uma interação (FR-012, SC-004)
- [X] T033 [P] [US2] Cobrir em `frontend/tests/meus-ingressos.test.tsx` que quem tem **apenas** ingressos passados **não** vê o estado vazio (FR-013) — é o contra-teste que pega a condição olhando só o grupo dos futuros

**Checkpoint**: as duas telas da área existem e nenhuma delas fica em branco.

---

## Phase 5: US3 — Mostrar o QR na portaria (P1)

**Goal**: O QR na tela é lido por um leitor de terceiro, inclusive em tela estreita, e o código
continua disponível em texto.

**Independent Test**: Abrir o ingresso a 320px e ler o QR com um aplicativo leitor de terceiro,
conferindo que o conteúdo lido é igual ao código em texto.

- [X] T034 [US3] Tornar `indice` e `total` **opcionais** em `frontend/components/tickets/Ingresso.tsx`, preservando o comportamento atual quando presentes — a alteração é **aditiva** e nenhuma asserção de `frontend/tests/ingresso.test.tsx` pode mudar (FR-057, Complexity Tracking)
- [X] T035 [US3] Renderizar cada item da lista com o `Ingresso` da 008 em `frontend/app/meus-ingressos/page.tsx`, dentro de `<ul>`, em vez de escrever um cartão novo — duas cópias do mesmo cartão divergiriam primeiro no tamanho do QR, que é o que SC-005 protege (R8)
- [X] T036 [P] [US3] Cobrir em `frontend/tests/meus-ingressos.test.tsx` que cada ingresso renderiza seu **próprio** `qr_svg` e seu **próprio** código, e que dois ingressos da mesma compra têm códigos diferentes (FR-021)
- [X] T037 [P] [US3] Cobrir em `frontend/tests/ingresso.test.tsx` que o `Ingresso` renderizado sem `indice`/`total` continua exibindo filme, sessão, sala, lugar, QR e o código em texto, e **não** exibe "Ingresso 1 de 1"
- [X] T038 [US3] Conferir em `frontend/components/tickets/tickets.module.css` que o QR mantém pelo menos 8rem de lado a 320px e o fundo claro do token `--cor-fundo-qr` — o leitor precisa do contraste, e é por isso que essa superfície não segue o tema escuro (SC-005, plan.md)
- [ ] T039 [US3] **PENDENTE — exige celular físico.** Executar a verificação **manual** do quickstart (Percurso 3): janela a 320px, leitor de QR de terceiro no celular, e conferir que o texto decodificado é idêntico ao código exibido — SC-005 não é automatizável aqui sem trazer biblioteca nativa, e isso está dito no plano em vez de escondido atrás de um teste que verifica outra coisa

**Checkpoint**: **MVP fechado.** A metade "Meus ingressos" da etapa 4 da constitution está entregue.

---

## Phase 6: US4 — Mandar o ingresso para quem vai comigo (P1)

**Goal**: O dono gera um link e outra pessoa abre o ingresso sem entrar em conta nenhuma.

**Independent Test**: Gerar o link de um ingresso como `cliente1`, abri-lo em janela anônima e
conferir que o ingresso aparece com o QR.

**⚠️ US4, US5 e US6 são indivisíveis entre si.** Não existe entregar o link sem a revogação: um link
ao portador sem revogação é uma credencial que não se pode cancelar, e a decisão 1 da spec assume a
consequência de exibir o QR justamente porque a revogação existe.

- [X] T040 [US4] Escrever `backend/tests/test_share_link_concurrency.py` com **`transaction=True`** e threads reais, provando que N pedidos simultâneos de link para o mesmo ingresso produzem **um único** link ativo e o **mesmo** endereço para todos (FR-029, SC-008) — deve falhar enquanto o serviço não existir, e precisa **falhar também** se a constraint de T005 for removida
- [X] T041 [US4] Escrever `gerar_link(ingresso)` em `backend/apps/screening/services/compartilhamento.py`: procura link ativo e devolve; se não houver, cria com `secrets.token_urlsafe(32)` dentro de `atomic()`; ao receber `IntegrityError` da constraint, **relê e devolve o link do vencedor** — quem perde a corrida não vê erro, vê idempotência, que é o que FR-028 promete (data-model.md)
- [X] T042 [US4] Registrar no docstring de `services/compartilhamento.py` por que o módulo é separado de `services/ingressos.py`: aquele é **puro** por decisão da 008, e é a ausência de acesso ao banco que torna `num_queries == 0` verificável no Princípio III (plan.md)
- [X] T043 [US4] Registrar no mesmo docstring **por que não há `SELECT FOR UPDATE`**: na 007 o bloqueio era necessário por haver leitura-antes-de-escrita sobre linhas de terceiros; aqui a única linha em jogo é a que está sendo criada, e acrescentar bloqueio moveria a garantia do banco para a aplicação (data-model.md)
- [X] T044 [P] [US4] Escrever `LinkSerializer` em `backend/apps/screening/serializers.py` devolvendo `{"ativo": bool, "endereco": str | null}`, montando o endereço a partir de `settings.SITE_URL` — completo e pronto para copiar, porque montá-lo no navegador erra atrás de proxy (FR-024)
- [X] T045 [P] [US4] Cobrir em `backend/tests/test_share_link_api.py` que `POST` devolve `201` na criação e `200` com o **mesmo** endereço quando já há link ativo (FR-028, contracts/my-tickets-api.md)
- [X] T046 [US4] Escrever `TicketDetailView` em `backend/apps/screening/views.py` para `GET /api/v1/ingressos/<public_id>/`, devolvendo o ingresso do dono com o estado do link
- [X] T047 [US4] Escrever `TicketShareLinkView` em `backend/apps/screening/views.py` com `POST` (gerar) e `DELETE` (revogar) em `/api/v1/ingressos/<public_id>/link/` — dois verbos num endereço, porque gerar e revogar são criar e apagar o mesmo recurso (R4)
- [X] T048 [US4] Escrever `SharedTicketView` em `backend/apps/screening/views.py` para `GET /api/v1/ingressos-compartilhados/<token>/`, com `permission_classes = [AllowAny]` **e `authentication_classes = []`**, e comentário registrando que a segunda metade é o que faz FR-036 ser estrutura: sem autenticador não existe caminho pelo qual a view enxergue um usuário (R5)
- [X] T049 [US4] Registrar os quatro endereços novos em `backend/apps/screening/urls.py`
- [X] T050 [P] [US4] Acrescentar `fetchIngresso`, `fetchIngressoCompartilhado`, `postLink` e `deleteLink` em `frontend/lib/api.ts`, e o tipo `LinkDeCompartilhamento` em `frontend/lib/types.ts`
- [X] T051 [US4] Escrever `frontend/app/api/link-do-ingresso/route.ts` com `POST` e `DELETE`, repassando cookie de sessão e devolvendo status e corpo **sem alterá-los**, no padrão de `app/api/pagar/route.ts`
- [X] T052 [US4] Escrever `frontend/app/meus-ingressos/[id]/page.tsx` — o ingresso do dono, com o `Ingresso` da 008 e o painel de link
- [X] T053 [US4] Escrever `frontend/components/tickets/PainelDeLink.tsx` como ilha cliente com copiar, gerar e revogar, anunciando o resultado de cada ação a tecnologias assistivas (FR-035, FR-054)
- [X] T054 [US4] Escrever `frontend/app/ingresso/[token]/page.tsx` como Server Component que **não repassa o cookie de sessão**, renderizando o `Ingresso` dentro de um `<ul>` de um item (FR-036, R8)
- [X] T055 [US4] Declarar em `frontend/app/ingresso/[token]/page.tsx` o `export const dynamic = "force-dynamic"`, com comentário registrando que sem ele a revogação continua correta no banco e **irrelevante na tela** — a credencial seguiria sendo servida do cache, e nenhum teste de back-end pegaria (R13, SC-009)
- [X] T056 [US4] Escrever `frontend/app/ingresso/[token]/publico.module.css` com tokens da 006, garantindo QR legível a 320px
- [X] T057 [P] [US4] Cobrir em `frontend/tests/ingresso-publico.test.tsx` que a página pública renderiza filme, sessão, sala, lugar e QR, e **não** exibe convite para entrar nem link para a conta

**Checkpoint**: o link existe e abre. **Não commitar a feature aqui** — sem US6 é credencial sem cancelamento.

---

## Phase 7: US5 — A página compartilhada não conta nada além do ingresso (P1)

**Goal**: Quem recebe o link vê o ingresso, e nada mais.

**Independent Test**: Gerar o link de um ingresso de uma compra de três lugares e inspecionar a
resposta pública inteira, conferindo a ausência de comprador, dos outros ingressos, de valor e de
dado de pagamento.

**⚠️ T058 é requisito da constitution, não diferencial.** O Princípio III é explícito sobre o link de
compartilhamento, e a spec exige a prova no mesmo espírito do que a 001 já faz com o catálogo
público.

- [X] T058 [US5] Escrever `backend/tests/test_share_link_leakage.py` inspecionando a resposta pública **inteira**, serializada, e falhando se aparecer — **pelo valor, não pelo nome do campo** — nome, e-mail, `username` ou id do comprador; qualquer outro ingresso da mesma compra; valor, `total`, `cartao_final` ou `bandeira`; id de reserva, de pagamento ou o `public_id`; `expira_em` ou `situacao`; capacidade, status da sessão ou preço; o próprio token ecoado; ou a `TICKET_SIGNING_KEY` em qualquer forma (FR-042, contracts/my-tickets-api.md)
- [X] T059 [US5] Fazer `SharedTicketView` responder com o `TicketSerializer` da 008 **sem alteração nenhuma**, e registrar em comentário que os campos da área do dono vivem em `MeuIngressoSerializer` justamente para que a pressão de crescimento aponte para o lado não público (R6)
- [X] T060 [P] [US5] Cobrir em `backend/tests/test_share_link_leakage.py` que a compra de três lugares gera três links **distintos**, e que cada um exibe **apenas** o seu ingresso — nenhum caminho leva aos outros dois (FR-039)
- [X] T061 [US5] Declarar em `frontend/app/ingresso/[token]/page.tsx` o `metadata` com `robots: { index: false, follow: false }` e `referrer: "no-referrer"`, com comentário registrando que o endereço **é** a credencial e que o `no-referrer` impede o token de vazar no cabeçalho `Referer` no dia em que alguém acrescentar um link de saída (FR-044, R9)
- [X] T062 [P] [US5] Cobrir em `frontend/tests/ingresso-publico.test.tsx` a ausência dos campos proibidos no que é renderizado **e** no estado serializado da página — o vazamento pode estar num `<script>` que não aparece na tela

**Checkpoint**: a prova exigida pelo Princípio III está verde.

---

## Phase 8: US6 — Cancelar um link que foi longe demais (P1)

**Goal**: O dono revoga; o endereço antigo morre para sempre; o ingresso continua valendo.

**Independent Test**: Gerar link, conferir que abre, revogar, conferir que o mesmo endereço não
exibe mais nada, e conferir que o código do QR é o mesmo de antes.

- [X] T063 [US6] Acrescentar a `backend/tests/test_ticket_signature.py` a prova de SC-010: capturar o `codigo` de um ingresso, gerar link, revogar, e conferir que o `codigo` é **byte a byte o mesmo** e continua verificando (FR-033) — é o teste que pega o dia em que alguém "simplificar" fundindo os dois segredos
- [X] T064 [US6] Escrever `revogar_link(ingresso)` em `backend/apps/screening/services/compartilhamento.py` como **`UPDATE` condicional** (`WHERE ticket = ... AND revoked_at IS NULL`), com comentário registrando que a condição no próprio `WHERE` torna a operação idempotente sem transação e sem bloqueio, e que **a linha nunca é apagada** (FR-031, FR-043)
- [X] T065 [P] [US6] Cobrir em `backend/tests/test_share_link_api.py` que `DELETE` devolve `200` também quando não há link ativo — um `404` na segunda chamada faria o front exibir erro por uma ação que produziu o resultado desejado (contracts/my-tickets-api.md)
- [X] T066 [P] [US6] Cobrir em `backend/tests/test_share_link_api.py` que o token revogado responde `404` com a frase "Este link não vale mais. Peça um novo a quem enviou o ingresso." e que um token **inventado** responde **exatamente igual**, byte a byte (FR-043, SC-014)
- [X] T067 [P] [US6] Cobrir em `backend/tests/test_share_link_api.py` que gerar link depois de revogar produz endereço **diferente**, e que o revogado continua morto para sempre (FR-031, FR-032, SC-011)
- [X] T068 [P] [US6] Cobrir em `backend/tests/test_share_link_api.py` que o token não coincide com o `codigo` do QR, não é derivável dele e não é sequencial — dois tokens gerados não permitem deduzir um terceiro (FR-026, FR-027, SC-012)
- [X] T069 [US6] Escrever o estado "link não vale mais" em `frontend/app/ingresso/[token]/page.tsx` como tela própria com frase em português — **não** `notFound()`, que renderizaria a 404 genérica do site e mandaria quem recebeu o ingresso concluir que o site quebrou (FR-052)
- [X] T070 [US6] Exibir no `PainelDeLink` o estado do link ativo com as duas ações, copiar e revogar, e o estado sem link com a ação de gerar (FR-035)
- [X] T071 [P] [US6] Cobrir em `frontend/tests/ingresso-publico.test.tsx` que o estado de link revogado exibe a frase própria e não a 404 genérica

**Checkpoint**: **a metade "compartilhamento" da etapa 4 está fechada.** US4+US5+US6 podem ser commitadas juntas.

---

## Phase 9: US7 — Cada um vê e mexe só no que é seu (P2)

**Goal**: Outro cliente, organizador e portaria são recusados pelo servidor nas quatro operações.

**Independent Test**: Com ingressos de `cliente1`, tentar listar, abrir, gerar e revogar como
`cliente2`, organizador e portaria, e conferir a recusa nas 12 combinações.

- [X] T072 [P] [US7] Cobrir em `backend/tests/test_my_tickets_api.py` que `cliente2` vê apenas os próprios ingressos, e nenhum de `cliente1` (FR-047)
- [X] T073 [P] [US7] Cobrir em `backend/tests/test_share_link_api.py` que `cliente2` recebe **`404`, não `403`** ao abrir, gerar e revogar ingresso de `cliente1` — um `403` confirmaria que aquele `public_id` existe, e `public_id` é o valor que vai dentro do código assinado (R12, FR-048)
- [X] T074 [P] [US7] Cobrir em `backend/tests/test_share_link_api.py` que gerar link para ingresso alheio **não cria link nenhum**, e que revogar link alheio deixa o link **ativo** (US7-3, US7-4)
- [X] T075 [P] [US7] Cobrir em `backend/tests/test_my_tickets_api.py` que organizador e portaria recebem `403` com "Apenas clientes têm ingressos." nas quatro operações — `401` os mandaria à entrada, que é caminho sem saída porque entrar de novo não muda o papel (FR-049, R12)
- [X] T076 [P] [US7] Cobrir em `backend/tests/test_my_tickets_api.py` que visitante sem sessão recebe `401` com "Entre para ver seus ingressos." e que nenhum dado de ingresso aparece na resposta (FR-051)
- [X] T077 [US7] Conferir que as recusas de T073–T076 acontecem chamando o Django **direto**, sem passar pela interface — esconder o botão nunca é o controle de acesso (FR-050, SC-016)
- [X] T078 [US7] Redirecionar visitante para `/entrar?next=/meus-ingressos/<id>` em `frontend/app/meus-ingressos/[id]/page.tsx`, e tratar `403` com a frase do servidor em vez de conduzir à entrada (FR-051)

**Checkpoint**: as 12 combinações recusadas.

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Verificar que as provas provam, fechar o ponta a ponta e escrever o que o avaliador
precisa ler.

- [X] T079 Remover temporariamente a `condition` da constraint `um_link_ativo_por_ingresso`, rodar `test_share_link_concurrency.py` e conferir que ele **falha**; restaurar. Se passar sem a constraint, o teste está provando outra coisa e é pior tê-lo verde do que não tê-lo (SC-008)
- [X] T080 Acrescentar um campo qualquer ao `TicketSerializer`, rodar `test_share_link_leakage.py` e conferir que ele **falha**; remover. É a verificação de que a prova de FR-042 pega a pressão de crescimento descrita em R6
- [X] T081 Trocar `ingressos_do_cliente` para usar `sellable()`, rodar `test_my_tickets_api.py` e conferir que T010 e T011 **falham**; restaurar. É a verificação de que a armadilha herdada está guardada (R10)
- [X] T082 [P] Escrever `frontend/tests/e2e/compartilhamento.spec.ts`: entrar como cliente, abrir Meus ingressos, gerar link, abrir em contexto **sem sessão**, revogar e conferir que o endereço deixa de exibir o ingresso na primeira recarga (SC-009)
- [X] T083 [P] Cobrir navegação por teclado em `frontend/tests/meus-ingressos.test.tsx`: percorrer a lista, copiar e revogar sem mouse, com o resultado anunciado a tecnologias assistivas (FR-054, FR-055, SC-018)
- [X] T084 [P] Conferir a 320px que lista, ingresso e página pública permanecem completos, sem rolagem horizontal e com o QR legível (FR-056)
- [X] T085 [P] Conferir com o TMDb indisponível que as três superfícies funcionam idênticas (FR-014, FR-045, SC-017)
- [X] T086 Conferir que nenhum valor de cor, espaçamento, tipografia, raio ou duração ficou fora dos tokens nos três CSS novos (FR-059, Princípio V)
- [X] T087 Atualizar `README.md` com a área "Meus ingressos", o comportamento do link, e — **obrigatoriamente** — a decisão de guardar o token em **texto claro**, com o que se ganha (FR-028/FR-035: o dono recopia o link depois) e o que se perde (um dump do banco entrega links utilizáveis; a `TICKET_SIGNING_KEY` **não** está no banco, então o dump sozinho não permite forjar código) e as mitigações — 256 bits, revogação imediata, `noindex`, `no-referrer` (FR-061, Princípio VI)
- [X] T088 Registrar no `README.md` que a leitura do QR por leitor de terceiro (SC-005) é verificada **à mão**, pelo quickstart, e o que os testes automatizados cobrem no lugar — o Princípio VI pede honestidade sobre o que não está coberto
- [X] T089 Rodar a suíte inteira e comparar com a linha de base de T001, confirmando que **nenhuma** asserção das features 001–008 foi removida ou enfraquecida, e que o item novo do `AccountMenu` não exigiu tocar em asserção de navegação (FR-057, SC-019)
- [X] T090 Confirmar que `backend/pyproject.toml`, `frontend/package.json` e `.env.example` continuam **sem alteração** — se algum mudou, uma decisão foi tomada sem passar pelo research (R15, T002, T003)
- [ ] T091 **PARCIAL** — percursos 1, 2, 4, 5, 6, 7 e 8 verificados (por teste automatizado, `curl` e consulta ao banco); o **percurso 3** depende de T039. Percorrer o `quickstart.md` inteiro contra a aplicação rodando

---

## Dependencies & Execution Order

**Fases 1 → 2 são bloqueantes.** Nenhuma user story começa antes de a constraint existir e das
consultas devolverem passado e sessão cancelada.

**Depois da Fase 2:**

```text
Fase 3 (US1) ──┬── Fase 4 (US2)     ← MVP: a área alcançável
               └── Fase 5 (US3)

Fase 6 (US4) ── Fase 7 (US5) ── Fase 8 (US6)   ← indivisíveis entre si
                                                  não commitar US4 sozinha

Fase 9 (US7) — depende dos endereços das fases 3 e 6 existirem
Fase 10 — depois de tudo
```

**Ordens que não podem inverter:**

- **T009–T011 antes de T012–T013.** O selector escrito antes do teste produz um teste escrito para o
  que o selector faz. E a armadilha de R10 é invisível: a linha errada é mais parecida com o resto do
  projeto do que a certa.
- **T040 antes de T041.** Mesma razão da 007 e da 008: teste de concorrência escrito depois do
  serviço tende a ser escrito para passar.
- **T058 antes de T059.** A lista de campos proibidos é o contrato; a view só o cumpre.
- **T063 antes de T064.** A prova de que revogar não toca o código precisa existir antes de a
  revogação existir — senão ela é escrita já sabendo o que a implementação faz.
- **T004–T008 são uma unidade.** Se o trabalho for interrompido no meio, não commitar.
- **T079, T080 e T081 só fazem sentido depois de as fases correspondentes estarem verdes.** São a
  verificação de que as provas provam.
- **T087 é pré-requisito da avaliação, não polimento.** A decisão do token em texto claro é
  exatamente o tipo de escolha que "pareceria estranha numa leitura rápida", e o Princípio VI exige
  que esteja escrita.

## Parallel Execution Examples

**Fase 2** — depois de T008: `T009`, `T010` e `T011` juntas (arquivos distintos, cenários
independentes). Depois de T013: `T014` e `T015` juntas.

**Fase 3** — `T016`, `T017` e `T018` juntas no mesmo arquivo (casos independentes: escrever de uma
vez). No front, `T023`, `T026` e `T030` tocam arquivos distintos.

**Fase 6** — `T044`, `T045`, `T050` e `T057` são independentes entre si. `T046`–`T049` são
sequenciais: mesmo arquivo.

**Fase 8** — `T065`, `T066`, `T067` e `T068` juntas.

**Fase 9** — as seis tarefas são independentes e podem correr juntas.

**Fase 10** — `T082`, `T083`, `T084` e `T085` em paralelo. `T079`, `T080` e `T081` são sequenciais
entre si: cada uma quebra o código de propósito e restaura.

## Implementation Strategy

**MVP = Fases 1, 2, 3, 4 e 5.** Ao fim da Fase 5 o ingresso deixa de ser inalcançável: o cliente
reencontra o que comprou, com o da próxima sessão no topo e o QR legível na fila. É metade da etapa 4
da constitution, e é a metade que resolve o problema que originou a feature.

**Ordem sugerida de entrega incremental**:

1. **Fases 1–2** — a constraint existe e as consultas não usam `sellable()`. Nada visível, mas é onde
   moram os dois riscos da feature.
2. **Fases 3–5** — a área, o estado vazio e o QR legível. MVP fecha.
3. **Fases 6–8** — o link, a prova de não vazamento e a revogação. **Entram juntas**, sempre.
4. **Fase 9** — as 12 recusas.
5. **Fase 10** — a verificação de que as provas provam, e o README.

**Três pontos de não avançar**:

- **Se T079 passar em vez de falhar, parar.** Um teste de concorrência verde sem a constraint está
  provando que o serviço é sequencial, não que a garantia é do banco.
- **Se T081 passar em vez de falhar, parar e reler R10.** Significa que o cenário de sessão iniciada
  ou cancelada não está sendo montado pela fixture — e a armadilha continua sem guarda.
- **Se US4 estiver pronta e US6 não, não commitar.** A decisão 1 da spec assume a consequência de
  exibir o QR na página pública **porque** a revogação existe. Entregar uma sem a outra publica uma
  credencial que ninguém pode cancelar.
