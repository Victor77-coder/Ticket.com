---
description: "Task list for feature implementation"
---

# Tasks: Telas de Compra — Filme, Assentos e Pagamento

**Input**: Design documents from `/specs/012-telas-de-compra/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/filme-detalhe.md](./contracts/filme-detalhe.md),
[contracts/composicao.md](./contracts/composicao.md), [quickstart.md](./quickstart.md)

**Tests**: **Sim.** A spec exige testes novos de apresentação e proíbe afrouxar asserção de
negócio (FR-023, R11). O contrato de `trailers[]` tem testes obrigatórios. O e2e da 007
(`frontend/tests/e2e/reserva.spec.ts`) é a defesa do clique até o mapa — o nome acessível
`Escolher lugares —` **não muda**.

**A armadilha é o clique, não a cor.** Recompor o horário quebra o caminho se o alvo deixar de
ser o link com aquele rótulo. A segunda armadilha é harmonizar `--cor-fundo-qr` no
ingresso-objeto.

**Organization**: Cinco user stories, todas P1. As fases seguem **dependência de arquivo**, não
só a numeração: US1 e US2 compartilham a página do filme (sequenciais); US3 e US4 tocam
árvores distintas e podem andar em paralelo depois da fundação; US5 verifica o recorte.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (grade de sessões), US2 (Sobre e Trailers), US3 (resumo ao lado do mapa),
  US4 (pagamento e ingresso-objeto), US5 (catálogo e regras intactos)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Página do filme**: `frontend/app/filmes/[slug]/page.tsx` (Server Component) + ilha
  `FilmeCliente.tsx`
- **Grade**: `frontend/lib/grade-sessoes.ts` — agrupamento no cliente, `screenings[]` intacto
- **Trailers aditivo**: `backend/apps/catalog/serializers.py` (`MovieDetailSerializer` só) +
  `backend/tests/test_filme_detalhe.py`
- **Mapa**: `frontend/components/seats/SeatSelection.tsx` + `seats.module.css` — **não**
  `Seat.tsx`
- **Ingresso-objeto**: variante em `frontend/components/tickets/Ingresso.tsx` — padrão intacto
- **Congelados**: `frontend/components/highlights/` (importar `TrailerFrame`, não editar),
  `frontend/components/rows/`, `frontend/components/header/`, `frontend/app/page.tsx`,
  `frontend/app/api/busca/`, `backend/apps/catalog/services/tmdb_sync.py`, seed

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte, e o que esta feature **não** pode tocar

- [X] T001 Rodar `docker compose exec backend pytest`, `docker compose exec frontend npm run test` e, de `frontend/`, `npx playwright test --workers=2`, registrando a linha de base (contagens) contra a qual SC-009 é medido no fim
- [X] T002 [P] Conferir que os caminhos congelados estão limpos no git: `git diff -- frontend/components/highlights frontend/components/rows frontend/components/header frontend/app/page.tsx frontend/app/api/busca backend/apps/catalog/services/tmdb_sync.py` deve ser vazio. Qualquer diff pré-existente aqui **não** se mistura com esta feature (FR-002, R9)
- [X] T003 [P] Confirmar que `prototipo/index.html` permanece fora do produto: nenhum import a partir de `frontend/` ou `backend/`. A spec extrai arquitetura de informação, não o HTML do protótipo
- [X] T004 [P] Localizar em `frontend/styles/tokens.css` o bloco de `--largura-conteudo` (irmã da medida nova) e em `frontend/components/seats/seats.module.css` a regra `.resumo` (hoje sticky inferior) — é o ponto de partida do layout da US3, não para editar ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: O token de medida e os tipos que as histórias consomem. Sem tabela, sem lib nova.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

- [X] T005 Declarar `--largura-coluna-resumo` em `frontend/styles/tokens.css` junto das medidas de conteúdo, com comentário de que é largura da coluna do resumo (mapa e, se couber, pagamento) — **nenhum valor de cor**. Literal no CSS do assento é exatamente o que a 006 tirou (R10, FR-024)
- [X] T006 Acrescentar em `frontend/lib/types.ts` o tipo `TrailerDoFilme` (`provider`, `external_key`, `kind`: `"trailer" | "teaser"`, `name`) **distinto** do `Trailer` da home (que não tem `kind`/`name`), e o campo `trailers: TrailerDoFilme[]` em `MovieDetail` — lista, nunca opcional, nunca `null` (data-model.md, R2)
- [X] T007 Confirmar que `Highlight` em `frontend/lib/types.ts` **não** ganhou `kind` nem `name`. Reaproveitar `Trailer` da home no detalhe, ou o contrário, vazaria o contrato da 001

**Checkpoint**: tipos e token existem; a API ainda não envia `trailers` — os testes de contrato da US2 vão falhar por isso, de propósito.

---

## Phase 3: User Story 1 — Escolher sessão como grade de cinema (Priority: P1) 🎯 MVP

**Goal**: Na página do filme, dia primeiro, horários agrupados por sala, um clique até o mapa.

**Independent Test**: Abrir um filme com sessões em mais de um dia e mais de uma sala, escolher
um dia, acionar um horário disponível e chegar ao mapa numa interação.

### Tests for User Story 1 ⚠️

> Escritos primeiro. Sem a função e sem a grade, **falham**. Se já passarem, não estão medindo
> a composição nova.

- [X] T008 [P] [US1] Escrever `frontend/tests/grade-sessoes.test.ts` cobrindo: duas sessões no mesmo dia civil e salas diferentes caem no mesmo dia em salas distintas; dia sem sessão **não** aparece; um único dia continua no seletor; fuso `America/Sao_Paulo` (uma ISO que cruza meia-noite UTC mas não a civil em São Paulo) — data-model.md, R1
- [X] T009 [P] [US1] Escrever em `frontend/tests/filme.test.tsx` (arquivo novo) os casos da grade: seletor de dia presente; horários do dia ativo agrupados por sala; sessão com `has_available_seats: false` **não** é `link` e mostra "Esgotada"; sessão disponível é `link` com nome `/^Escolher lugares —/` apontando para `/sessoes/{id}` (FR-007, FR-008, R5)

### Implementation for User Story 1

- [X] T010 [US1] Implementar `agruparSessoesPorDia` em `frontend/lib/grade-sessoes.ts` a partir de `Screening[]` — dia civil em `America/Sao_Paulo`, rótulo "Hoje" quando for hoje nesse fuso, senão dia da semana abreviado + `DD/MM`; salas em ordem estável; horários por `starts_at`. **Não** chama API (R1)
- [X] T011 [US1] Rodar `npm run test -- grade-sessoes` em `frontend/` e conferir que T008 passou. Se um caso de fuso falhar, corrigir a função — não o relógio do teste
- [X] T012 [US1] Extrair a lista atual de `frontend/app/filmes/[slug]/page.tsx` para `frontend/app/filmes/[slug]/GradeDoDia.tsx` (`"use client"`), recebendo `screenings` e `release_date` já carregados. `page.tsx` permanece Server Component e **não** refaz fetch (R3)
- [X] T013 [US1] Trocar a lista única em `GradeDoDia.tsx` pelo seletor de dia + grade: dia ativo em estado local; um único dia **permanece** no seletor (edge case da spec)
- [X] T014 [US1] Horário disponível em `GradeDoDia.tsx`: alvo compacto visualmente, semanticamente `<Link href={/sessoes/${id}}>` com `aria-label={`Escolher lugares — ${horário}, ${sala}`}`. Chip que parece botão e é `<a>` — o mesmo critério da lista atual (R5). **Não** usar `<button>` + `router.push`
- [X] T015 [US1] Horário esgotado em `GradeDoDia.tsx`: texto "Esgotada", **não** é link, distinguível por texto e comportamento — não só por cor (FR-008)
- [X] T016 [US1] Preservar em `GradeDoDia.tsx` o vazio atual de `ListaDeSessoes`: filme sem sessão explica em português e mostra "Estreia em DD/MM/AAAA" quando `estreiaFutura` aplicar — a lógica já está em `page.tsx` (FR-026)
- [X] T017 [US1] Recompor `frontend/app/filmes/[slug]/filme.module.css` para seletor de dia e alvos compactos por sala, **somente tokens**. Sem pílula fina genérica, sem ícone de biblioteca (FR-028)
- [X] T018 [US1] Rodar `npm run test -- filme` em `frontend/` e conferir que T009 passou, inclusive o nome acessível
- [X] T019 [US1] Abrir `frontend/tests/e2e/reserva.spec.ts` e confirmar que `getByRole("link", { name: /^Escolher lugares —/ })` continua válido. Se o DOM mudou e o nome **não**, o ajuste é na implementação (T014), não no teste (FR-023, R11)
- [X] T020 [P] [US1] Conferir a 320px em `filme.module.css` / DevTools que a grade não gera rolagem lateral da página (FR-025, SC-008)
- [X] T021 [P] [US1] Conferir que o dia ativo é evidente sem cor só (forma, `aria-current` ou equivalente) — FR-005 antecipa a US2 nas abas; aqui vale para o seletor de dia

**Checkpoint**: a página do filme já vende horário como programação. Sinopse ainda pode estar
acima — a US2 é quem vira isso em seções.

---

## Phase 4: User Story 2 — Sobre e trailers no mesmo filme (Priority: P1)

**Goal**: Três seções na mesma página — Sessões, Sobre, Trailers — com dado que o filme já tem.

**Independent Test**: Filme com sinopse e trailer: Sessões → Sobre → Trailers, reproduzir, voltar
às sessões sem perder o filme.

**Depende da US1** (`page.tsx` / `filme.module.css` / `GradeDoDia.tsx`). Não paralelizar com a US1.

### Tests for User Story 2 ⚠️

> O teste de contrato **falha** enquanto `MovieDetailSerializer` não tiver `trailers`. Rodar
> antes de T026 e confirmar o vermelho. Se passar, o campo já vazou de outro lugar.

- [X] T022 [P] [US2] Escrever `backend/tests/test_filme_detalhe.py` conforme `contracts/filme-detalhe.md`: filme com trailers persistidos — lista não vazia, primário primeiro, `provider` e `external_key` batem; filme sem trailer — `"trailers": []` (chave existe, nunca `null`); `GET /api/v1/highlights/` **não** inclui `kind` nem `name`; detalhe continua sem status de sessão, custo, capacidade (Princípio IV)
- [X] T023 [US2] Rodar `docker compose exec backend pytest backend/tests/test_filme_detalhe.py` **antes** do serializer e conferir que falha por ausência de `trailers`. Se passar, parar — o campo não deveria existir ainda
- [X] T024 [P] [US2] Acrescentar em `frontend/tests/filme.test.tsx` os casos das três seções: Sessões/Sobre/Trailers mutuamente exclusivas; Sobre mostra sinopse e omite campo ausente (nunca "N/A"); Trailers com lista reproduz (iframe ou `TrailerFrame`); Trailers vazia explica em português e **não** renderiza alvo `disabled`; filme sem `screenings` ainda oferece Sobre e Trailers (FR-011, FR-012)

### Implementation for User Story 2

- [X] T025 [US2] Criar `MovieDetailTrailerSerializer` em `backend/apps/catalog/serializers.py` com `provider`, `external_key`, `kind`, `name`. **Não** acrescentar `kind`/`name` em `TrailerSerializer` — esse é o da home, e enriquecê-lo vazaria o contrato da 001 (R2, Complexity Tracking)
- [X] T026 [US2] Acrescentar `trailers` em `MovieDetailSerializer` (`backend/apps/catalog/serializers.py`): lista, nunca `null`; ordem primário primeiro, depois `published_at` descendente, desempate por `pk` (data-model.md)
- [X] T027 [US2] Prefetch de `trailers` em `get_movie_by_slug` em `backend/apps/catalog/selectors.py`. `views.py` permanece o mesmo `MovieDetailView`. **Não** editar `tmdb_sync.py`
- [X] T028 [US2] Rodar `docker compose exec backend pytest backend/tests/test_filme_detalhe.py backend/tests/test_highlights_api.py` e conferir: detalhe verde; highlights **inalterado** (nenhuma asserção removida)
- [X] T029 [US2] Quebrar de propósito: omitir `trailers` no serializer, rerodar `test_filme_detalhe.py`, conferir que falha, restaurar (quickstart.md, percurso 5)
- [X] T030 [US2] Criar `frontend/app/filmes/[slug]/FilmeCliente.tsx` (`"use client"`): recebe o `MovieDetail` já buscado; estado local da seção ativa (`sessoes` \| `sobre` \| `trailers`), padrão `sessoes`; **sem** `?aba=` na URL (R3)
- [X] T031 [US2] Ligar `page.tsx` à ilha: o Server Component continua fazendo `fetchMovie` e `notFound()`; a ilha não refetch. Mover a grade da US1 para a seção Sessões
- [X] T032 [US2] Implementar Sobre em `FilmeCliente.tsx` (ou `SecaoSobre.tsx` ao lado): sinopse completa; classificação, duração, gênero **se existirem**; ausentes somem — nunca "N/A", nunca direção/elenco/idioma inventados (FR-004, FR-009, SC-003)
- [X] T033 [US2] Implementar Trailers importando `TrailerFrame` de `frontend/components/highlights/TrailerFrame.tsx`. **Não editar** nenhum arquivo em `frontend/components/highlights/`. Filme sem trailer: frase em português, seção visível, nenhum botão desabilitado (FR-011, R4)
- [X] T034 [US2] Tratar trailer cujo provedor falha (iframe) com a mesma honestidade do `TrailerFrame` da home — não deixar retângulo mudo (edge case da spec). Se o frame já explica, não reimplementar iframe em `filme.module.css`
- [X] T035 [US2] Estilizar as três seções em `frontend/app/filmes/[slug]/filme.module.css` com tokens; seção ativa evidente sem cor só; as três **sempre** existem na página (FR-005)
- [X] T036 [US2] Rodar `npm run test -- filme` em `frontend/` e conferir T024. Confirmar que T009 (grade, nome acessível, esgotada) **continua** passando
- [X] T037 [P] [US2] `git diff -- frontend/components/highlights/` deve ser vazio. O import em `FilmeCliente.tsx` não conta como editar highlights (R9)

**Checkpoint**: a página do filme é página de filme. US1 não regressou.

---

## Phase 5: User Story 3 — Escolher lugares com o resumo à vista (Priority: P1)

**Goal**: Em tela larga, sala e resumo lado a lado; os quatro estados do assento intactos.

**Independent Test**: Selecionar dois lugares e conferir que o resumo ao lado lista os dois, o
total e o CTA, e que os quatro estados continuam distinguíveis em escala de cinza.

**Pode começar em paralelo com a US1** (arquivos distintos). Não toca `Seat.tsx`.

### Tests for User Story 3 ⚠️

- [X] T038 [P] [US3] Acrescentar em `frontend/tests/seats.test.tsx` asserções **aditivas**: com viewport larga simulada (ou classe de layout), o resumo e o mapa coexistem no mesmo arranjo; seleção de dois lugares atualiza o resumo; confirmar sem lugar continua avisando em português. **Nenhuma** asserção existente de estado de assento, limite ou 409 pode ser removida ou afrouxada (FR-015, FR-023)

### Implementation for User Story 3

- [X] T039 [US3] Recompor o layout em `frontend/components/seats/SeatSelection.tsx`: wrapper de duas colunas — `SeatMap` à esquerda, `SelectionSummary` / `ReservationPanel` à direita. A lógica de seleção, chave de idempotência e `confirmar` **não muda**
- [X] T040 [US3] Em `frontend/components/seats/seats.module.css`, layout ≥ 1000px (`SC-004`): coluna do resumo com `width: var(--largura-coluna-resumo)`; resumo `position: sticky` no topo abaixo do cabeçalho, superfície `--cor-superficie` (não o véu `--desfoque-resumo-assentos`, que nasceu para a barra inferior — R6)
- [X] T041 [US3] Em viewport estreita, o resumo empilha abaixo da sala; o sticky inferior atual de `.resumo` pode permanecer **só** nesse ramo. Sem rolagem lateral em 320px (FR-025)
- [X] T042 [US3] **Proibido** alterar regras de `.selecionado`, `.tomado`, `.acessibilidade` e o componente `frontend/components/seats/Seat.tsx`. Diff nessas regras é falha de FR-014 / SC-005, não "ajuste fino"
- [X] T043 [US3] Se `SelectionSummary.tsx` precisar de hierarquia (filme, horário, lugares, total, ação), mudar só marcação/CSS de resumo — o total estimado continua preço da sessão × quantidade, como hoje (data-model.md)
- [X] T044 [US3] `ReservationPanel.tsx` ocupa a mesma coluna do resumo após confirmar; prazo visível (FR-016). Conteúdo da 007 intacto
- [X] T045 [US3] Rodar `npm run test -- seats` em `frontend/` e conferir T038 + a suíte anterior verde
- [X] T046 [P] [US3] Aplicar escala de cinza (DevTools → Achromatopsia) ao mapa e conferir livre / selecionado / tomado / acessibilidade distinguíveis **sem cor só** (SC-005)
- [X] T047 [P] [US3] Conferir 320px: empilha, sem overflow horizontal da página

**Checkpoint**: o mapa continua sendo sala; o resumo deixou de ser só barra embaixo.

---

## Phase 6: User Story 4 — Pagar vendo o que se leva, receber ingresso-objeto (Priority: P1)

**Goal**: Resumo visível ao pagar; após aprovação, ingresso como objeto nesta tela — QR branco.

**Independent Test**: Reservar dois lugares, pagar, conferir resumo durante o formulário e dois
ingressos com lugar, QR branco e código digitável.

**Pode começar em paralelo com US1/US3.** Não alterar `app/meus-ingressos/` nem `app/ingresso/`.

### Tests for User Story 4 ⚠️

- [X] T048 [P] [US4] Acrescentar em `frontend/tests/ingresso.test.tsx` casos **aditivos**: variante padrão (sem prop) continua cartão da 009 — código visível, QR presente, sem comprador; variante `objeto` mostra lugar em evidência, QR e código **inteiro**. Nenhuma asserção existente removida (R7, FR-023)
- [X] T049 [P] [US4] Acrescentar em `frontend/tests/pagamento.test.tsx` casos aditivos: após aprovação os ingressos usam a variante `objeto`; recusa e erro de preenchimento **continuam** distinguíveis. Asserções da 008 intactas

### Implementation for User Story 4

- [X] T050 [US4] Acrescentar prop opcional `variante?: "cartao" | "objeto"` em `frontend/components/tickets/Ingresso.tsx`, padrão `"cartao"`. Meus ingressos e a página pública **não passam** a prop — não mudam (R7)
- [X] T051 [US4] Estilizar `.objeto` (ou equivalente) em `frontend/components/tickets/tickets.module.css`: lugar maior, picote com `--cor-fundo` recortando `--cor-superficie` e borda existente — **nenhuma cor nova**. QR continua usando `--cor-fundo-qr` (branco) nas duas variantes (R10, FR-021)
- [X] T052 [US4] Em `frontend/app/pagamento/[id]/PagamentoCliente.tsx`, passar `variante="objeto"` só na lista pós-aprovação. Não encolher `width`/`height` do QR nem esconder o `<code>`
- [X] T053 [US4] Conferir `frontend/app/pagamento/[id]/pagamento.module.css`: `.colunas` permanece; **não** refazer o grid (R8). Em ≥ 1000px resumo e formulário lado a lado (SC-004). Prazo visível sem tapar o resumo (FR-018)
- [X] T054 [US4] Confirmar que `.recusa` e `.erroForma` em `pagamento.module.css` continuam distintos — unificá-los é violação de FR-019
- [X] T055 [US4] Rodar `npm run test -- ingresso pagamento` em `frontend/` e conferir T048, T049 e a suíte anterior
- [X] T056 [US4] Quebrar de propósito: em `frontend/styles/tokens.css` pôr `--cor-fundo-qr` numa cor da marca, rodar `npm run test -- tokens` e conferir que a asserção de fundo branco falha; restaurar `#ffffff` (quickstart.md, percurso 5; FR-021)
- [X] T057 [P] [US4] `git diff -- frontend/app/meus-ingressos frontend/app/ingresso` deve ser vazio
- [X] T058 [P] [US4] Conferir 320px em pagamento e ingressos emitidos: empilha, sem rolagem lateral (FR-025)

**Checkpoint**: pagar lê como compra; o objeto de ingresso não vazou para a 009.

---

## Phase 7: User Story 5 — O catálogo e as regras continuam os mesmos (Priority: P1)

**Goal**: Home, carrossel, trilhas, busca, reserva, pagamento, QR e portaria iguais em regra.

**Independent Test**: Home visualmente a da 011; suíte 001–011 sem asserção de negócio alterada.

**Depende de US1–US4** — é a prova de recorte, não uma tela nova.

- [X] T059 [US5] Rodar `docker compose exec backend pytest` e conferir a linha de base de T001 **mais** `test_filme_detalhe.py`. Nenhuma asserção de `test_highlights_api.py`, `test_home_rows_api.py`, `test_search_api.py`, seed, reserva, pagamento ou portaria removida ou afrouxada
- [X] T060 [US5] Rodar `docker compose exec frontend npm run test` e conferir os testes anteriores + filme / grade / aditivos de seats, ingresso e pagamento
- [X] T061 [US5] Rodar, de `frontend/`, `npx playwright test --workers=2`. `reserva.spec.ts` continua usando `/^Escolher lugares —/`. Ajuste de seletor só se inevitável e **nunca** para um regex mais frouxo (R11)
- [X] T062 [US5] Para cada teste que precisou mudar, registrar qual e por quê, e confirmar que foi seletor ou estilo das **três** telas — nunca regra, contrato de catálogo, seed ou limite de carrossel (FR-023)
- [X] T063 [US5] `git diff -- frontend/components/highlights frontend/components/rows frontend/components/header frontend/app/page.tsx frontend/app/api/busca backend/apps/catalog/services/tmdb_sync.py backend/apps/catalog/management` deve ser vazio (FR-002, SC-007)
- [X] T064 [US5] Percorrer a home em 1440×900 contra `contracts/composicao.md` (prova de recorte): carrossel, trilhas e busca iguais aos da 011
- [X] T065 [P] [US5] Conferir estados de erro e vazio das três telas em português, com próxima ação: filme que não carrega, filme sem sessão, sem trailer, confirmar sem lugar, recusa de cartão, reserva vencida (FR-026)
- [X] T066 [P] [US5] Conferir que `services/ingressos.py`, `TICKET_SIGNING_KEY` e os testes de concorrência da 007/008/010 **não** foram tocados

**Checkpoint**: a composição mudou; o fluxo não.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Julgamento humano das três telas, rastro no README, disciplina de tokens.

- [X] T067 Percorrer `contracts/composicao.md` na página do filme em 1440×900 e responder a pergunta final: em três segundos, dá para apontar como se escolhe o horário? (SC-010). Registrar o veredito no próprio contrato, seção de resultado se ainda não houver
- [X] T068 [P] Percorrer o mesmo contrato no mapa (resumo ao lado, quatro estados) e no pagamento (colunas + ingresso-objeto + QR branco)
- [X] T069 Percorrer `specs/012-telas-de-compra/quickstart.md` inteiro contra a aplicação em `localhost:5003`
- [X] T070 Atualizar `README.md` com a nota da 012: as três telas de compra foram recompostas; a **home não** — o achado da 011 sobre a primeira dobra permanece achado, não entregável desta feature (Princípio VI)
- [X] T071 Registrar no `README.md` as duas quebras de propósito desta feature: omitir `trailers` no detalhe; harmonizar `--cor-fundo-qr` no ingresso-objeto
- [X] T072 Atualizar a seção de **uso de IA** do `README.md` com o que foi feito com e sem auxílio nesta feature
- [X] T073 [P] Varrer os arquivos tocados: nenhum valor de cor, espaçamento, tipografia, raio ou duração fora de tokens (FR-024). Exceção nenhuma para "só um `20rem` no mapa"
- [X] T074 [P] Conferir ausência de placeholder, "N/A", alvo desabilitado no lugar de vazio, e "em breve" nas três telas (FR-027)
- [X] T075 [P] Conferir `prefers-reduced-motion`: nada que a feature introduziu ignora a preferência (edge case da spec)
- [X] T076 Comparar a suíte com T001 e confirmar SC-009: nenhuma asserção de regra de negócio das 001–011 removida ou enfraquecida
- [X] T077 Proibições anti-slop da 011 nas três telas: sem laranja residual, sem roxo/índigo, sem halo, sem pílula fina genérica, sem ícone de biblioteca de cinema (FR-028)

---

## Dependencies & Execution Order

**Fases 1 → 2 são bloqueantes.** Sem o token e sem os tipos, a US2 não compila o front e a US3
espalha literal.

```text
Fase 1–2 ── token + tipos
     │
     ├── Fase 3 (US1) ── grade na página do filme          🎯 MVP
     │        │
     │        └── Fase 4 (US2) ── abas Sobre/Trailers + trailers[]
     │                 │
     ├── Fase 5 (US3) ── resumo ao lado do mapa            (paralelo à US1)
     ├── Fase 6 (US4) ── ingresso-objeto no pagamento      (paralelo à US1/US3)
     │
     └── Fase 7 (US5) ── recorte e suíte                   (depois de US1–US4)
              │
              └── Fase 8 ── composição, README, tokens
```

**Ordens que não podem inverter:**

- **T008–T009 antes de T010–T017.** Teste da grade escrito depois copia o DOM que já está lá.
- **T022–T023 antes de T025–T026.** O contrato tem de falhar por ausência de `trailers`. Se T023
  passar, o campo vazou.
- **T014 preserva o nome acessível; T019/T061 são a guarda.** Afrouxar `/^Escolher lugares —/` é
  a falha silenciosa desta feature — análoga ao contraste na 011.
- **T025 não edita `TrailerSerializer`.** Enriquecer o serializer da home é reabrir a 001.
- **T042 não toca `Seat.tsx` nem as classes de estado.** Layout ≠ forma do assento.
- **T050 padrão `cartao`.** Sem padrão, meus ingressos herdariam `objeto` por acidente.
- **US2 depois da US1** — compartilham `page.tsx` e `filme.module.css`.
- **US5 depois de US1–US4** — prova de recorte, não história de tela.

### User Story Dependencies

- **US1 (P1)**: depois da Fase 2 — MVP
- **US2 (P1)**: depois da US1 (mesmos arquivos da página do filme) + tipos da Fase 2
- **US3 (P1)**: depois da Fase 2 — independente da página do filme
- **US4 (P1)**: depois da Fase 2 — independente da US1/US3
- **US5 (P1)**: depois de US1–US4

### Parallel Opportunities

- Fase 1: T002, T003, T004
- Depois da Fase 2, em paralelo: **US1**, **US3**, **US4**
- US2 só depois da US1
- Dentro da US1: T008 ∥ T009; T020 ∥ T021
- Dentro da US2: T022 ∥ T024; T037 sozinho no diff de highlights
- Dentro da US3: T046 ∥ T047
- Dentro da US4: T048 ∥ T049; T057 ∥ T058
- US5: T065 ∥ T066
- Polish: T068, T073, T074, T075

---

## Parallel Example: User Story 1

```bash
# Testes da grade, juntos, antes da implementação:
Task: "Escrever frontend/tests/grade-sessoes.test.ts (agrupamento, fuso, dia único)"
Task: "Escrever frontend/tests/filme.test.tsx (seletor, esgotada, Escolher lugares —)"

# Depois de T018, conferências independentes:
Task: "Confirmar reserva.spec.ts ainda acha /^Escolher lugares —/"
Task: "Conferir 320px sem rolagem lateral em filme.module.css"
```

## Parallel Example: depois da fundação

```bash
# Três frentes, arquivos distintos:
Task: "US1 — GradeDoDia.tsx + grade-sessoes.ts"
Task: "US3 — SeatSelection.tsx + seats.module.css (sem Seat.tsx)"
Task: "US4 — Ingresso.tsx variante objeto + PagamentoCliente.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1–2 (token, tipos, linha de base)
2. Fase 3 (US1) — a grade
3. **STOP**: filme com dia → horário → mapa numa interação, nome acessível intacto
4. Demo possível: a página já não parece lista de configuração

### Incremental Delivery

1. Setup + Foundational
2. **US1** → MVP (grade)
3. **US2** → página de filme (Sobre/Trailers + `trailers[]`)
4. **US3** → mapa com resumo ao lado
5. **US4** → ingresso-objeto no pagamento
6. **US5 + Polish** → recorte, suíte, README, SC-010

US3 e US4 podem entrar antes da US2 se a equipe quiser o mapa/pagamento primeiro; a US2 não
pode entrar antes da US1.

### Parallel Team Strategy

1. Juntos: Fases 1–2
2. Depois: A = US1→US2, B = US3, C = US4
3. Juntos: US5 e Polish

---

## Notes

- [P] = arquivo diferente, sem dependência pendente
- `prototipo/` não é tarefa de implementação
- Nenhuma migração, nenhum sync, nenhuma lib nova
- Verificar que os testes de T008/T009/T022 **falham** antes de implementar
- Commit por tarefa ou por grupo lógico (US1, contrato+serializer, mapa, ingresso)
- Parar no checkpoint e validar a história sozinha
- Evitar: afrouxar o e2e da 007, editar `TrailerSerializer` da home, "harmonizar" o QR,
  reduzir a marca de conferido do assento, inventar direção no Sobre
