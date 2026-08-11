---
description: "Task list for feature implementation"
---

# Tasks: Trilhas de Filmes na Home

**Input**: Design documents from `/specs/004-home-movie-rows/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/home-api.md](./contracts/home-api.md)

**Tests**: Incluídos. A Constitution v1.0.0 obriga prova no gate do Princípio IV, e R10 do
`research.md` concentra os demais onde R1 e R3 identificaram armadilha — o transbordo que vaza
para a página e as duas regras de expiração da classificação.

**Organization**: Tarefas agrupadas por user story. Ordem das fases pela prioridade do spec:
US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (Em cartaz), US2 (Em alta e Em breve), US3 (navegação), US4 (filme sem sessão)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Back-end**: `backend/apps/catalog/`
- **Front-end**: `frontend/components/rows/`, `frontend/app/`
- Portas: interface **5003**, API **8000**, banco **5438**

---

## Phase 1: Setup

**Purpose**: Os campos de classificação no banco, antes de qualquer consulta

- [X] T001 Acrescentar `is_trending`, `is_upcoming` e `catalog_synced_at` ao modelo em `backend/apps/catalog/models.py`, com default `False` nos booleanos e índice em cada um (data-model.md)
- [X] T002 Gerar e aplicar a migração `catalog.0003_movie_catalog_classification` em `backend/apps/catalog/migrations/`, sem backfill
- [X] T003 [P] Criar `frontend/components/rows/rows.module.css` com as medidas da trilha e do cartão, usando exclusivamente os tokens de `frontend/styles/tokens.css` (Princípio V)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Importar e marcar a classificação, e expor as trilhas — consumidos por todas as stories

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar

### Importação do catálogo

- [X] T004 Adicionar `trending()` e `upcoming()` ao cliente em `backend/apps/catalog/services/tmdb_client.py`, usando `/trending/movie/week` e `/movie/upcoming?region=BR` (R6)
- [X] T005 Implementar a marcação da classificação em `backend/apps/catalog/services/tmdb_sync.py`, gravando `is_trending`, `is_upcoming` e `catalog_synced_at`
- [X] T006 Reescrever `backend/apps/catalog/management/commands/sync_tmdb.py` para importar as três listas, desduplicar por `tmdb_id` antes de detalhar, e aplicar `--limit` por lista (R6)
- [X] T007 Zerar `is_trending` em todos os filmes no início da sincronização em `backend/apps/catalog/management/commands/sync_tmdb.py` — sem isso quem entrou uma vez fica em alta para sempre (R3)
- [X] T008 [P] Escrever em `backend/tests/test_tmdb_sync.py` os testes de expiração: `is_trending` é zerado antes de remarcar, e um filme que sai da lista deixa de estar em alta (R3)
- [X] T009 [P] Escrever em `backend/tests/test_tmdb_sync.py` o teste de desduplicação: um filme presente em duas listas é detalhado uma única vez e recebe as duas marcas

### Endpoint das trilhas

- [X] T010 Extrair a regra de elegibilidade sem limite em `backend/apps/catalog/selectors.py`, e fazer `get_highlighted_movies` passar a usá-la com limite 5 — uma regra só, dois consumidores (R5)
- [X] T011 Implementar `get_trending_movies` e `get_upcoming_movies` em `backend/apps/catalog/selectors.py`, com o limite de 9 em Em alta e a exigência de `release_date > hoje` em Em breve (R3)
- [X] T012 Criar `MovieCardSerializer` em `backend/apps/catalog/serializers.py` seguindo `contracts/home-api.md`, sem `backdrop_url`, sem `trailer` e sem os campos de classificação
- [X] T013 Implementar `HomeRowsView` em `backend/apps/catalog/views.py` como público e somente leitura, com cache de 60s, **omitindo do array as trilhas vazias** (FR-006)
- [X] T014 Registrar `GET /api/v1/home/` em `backend/apps/catalog/urls.py`
- [X] T015 [P] Adicionar os tipos `MovieCard`, `MovieRowData` e `HomeRowsResponse` em `frontend/lib/types.ts`, derivados de `contracts/home-api.md`
- [X] T016 Adicionar `fetchHomeRows` em `frontend/lib/api.ts` para `/api/v1/home/`

**Checkpoint**: as três trilhas são consultáveis; nada ainda as exibe

---

## Phase 3: User Story 1 — Percorrer o que dá para comprar (Priority: P1) 🎯 MVP

**Goal**: A trilha **Em cartaz** aparece na home e conduz às sessões

**Independent Test**: Abrir a home e confirmar que a trilha Em cartaz lista os filmes com sessão
publicada e futura, e que acionar qualquer cartaz leva à página daquele filme com sessões listadas

### Testes da User Story 1

- [X] T017 [P] [US1] Escrever em `backend/tests/test_home_rows_api.py` o teste de SC-003: todo filme da trilha Em cartaz tem sessão publicada e futura, e sessão em rascunho ou passada não o qualifica
- [X] T018 [P] [US1] Escrever em `backend/tests/test_home_rows_api.py` o teste do gate do Princípio IV: a resposta pública não contém `status`, custo, capacidade, contagem de vendidos, identificação de usuário nem os campos de classificação
- [X] T019 [P] [US1] Escrever em `backend/tests/test_home_rows_api.py` o teste de trilha vazia: sem filmes compráveis, a trilha some do array em vez de vir vazia (FR-006)

### Implementação da User Story 1

- [X] T020 [US1] Implementar `frontend/components/rows/MovieCard.tsx` com cartaz, título em texto e link para a página do filme (FR-008 a FR-010)
- [X] T021 [US1] Implementar o substituto de cartaz ausente em `frontend/components/rows/MovieCard.tsx`, preservando a proporção dos demais cartões (FR-011)
- [X] T022 [US1] Dar ao cartão nome acessível que identifique o filme sem depender do texto alternativo da imagem, em `frontend/components/rows/MovieCard.tsx` (FR-012)
- [X] T023 [US1] Implementar `frontend/components/rows/MovieRow.tsx` com `overflow-x: auto` e `scroll-snap-type: x mandatory`, e o rótulo anunciado com a quantidade de filmes (R1, FR-019)
- [X] T024 [US1] Renderizar as trilhas na home em `frontend/app/page.tsx`, abaixo do painel de destaques, na ordem que o servidor devolveu (FR-001)
- [X] T025 [US1] Implementar o estado explicativo em `frontend/app/page.tsx` para quando nenhuma trilha tiver conteúdo (FR-007)
- [X] T026 [US1] Implementar o estado de erro das trilhas em `frontend/app/page.tsx` com mensagem em pt-BR, sem derrubar o painel de destaques (FR-029, FR-030)

**Checkpoint**: US1 completa — a home tem a trilha que sustenta a compra

---

## Phase 4: User Story 2 — Descobrir em alta e em breve (Priority: P2)

**Goal**: As trilhas **Em alta** e **Em breve** aparecem com filmes do catálogo externo

**Independent Test**: Abrir a home e confirmar que Em alta traz no máximo 9 cartazes, que Em breve
lista estreias futuras da mais próxima para a mais distante, e que ambas conduzem à página do filme

### Testes da User Story 2

- [X] T027 [P] [US2] Escrever em `backend/tests/test_home_rows_api.py` o teste do limite de 9 em Em alta (FR-003, SC-002)
- [X] T028 [P] [US2] Escrever em `backend/tests/test_home_rows_api.py` o teste de que Em breve exclui filme já estreado mesmo com `is_upcoming=True` (R3)
- [X] T029 [P] [US2] Escrever em `backend/tests/test_home_rows_api.py` o teste de ordenação: Em breve ascendente por estreia, com desempate por título
- [X] T030 [P] [US2] Escrever em `backend/tests/test_home_rows_api.py` o teste de que um filme em duas trilhas aparece nas duas (FR-005)

### Implementação da User Story 2

- [X] T031 [US2] Incluir as trilhas Em alta e Em breve na resposta de `backend/apps/catalog/views.py`, respeitando a ordem em-cartaz → em-alta → em-breve (FR-001)
- [X] T032 [US2] Renderizar as três trilhas em `frontend/app/page.tsx`, cada uma com posição de rolagem independente (FR-016)
- [X] T033 [US2] Ajustar `backend/apps/catalog/management/commands/seed_demo.py` para preferir filmes em cartaz com arte e duração acima de 60 minutos antes de cair para o critério de data (R9, Complexity Tracking)

**Checkpoint**: US1 + US2 formam o MVP — a home está povoada

---

## Phase 5: User Story 3 — Navegar as trilhas em qualquer dispositivo (Priority: P2)

**Goal**: Gesto, controles e teclado funcionam, e a página nunca rola para o lado

**Independent Test**: Percorrer as trilhas por gesto, por controle e só pelo teclado, em 360px e
1920px, confirmando que a página não rola horizontalmente

### Testes da User Story 3

- [X] T034 [P] [US3] Escrever em `frontend/tests/rows.test.tsx` o teste de que os controles de seta só são renderizados quando há transbordo (FR-014)
- [X] T035 [P] [US3] Escrever em `frontend/tests/rows.test.tsx` o teste de alcance por teclado: todos os cartões são focáveis na ordem visual (FR-017, SC-006)
- [X] T036 [P] [US3] Escrever em `frontend/tests/e2e/home-rows.spec.ts` o teste de SC-005: sem rolagem horizontal da página em 360px e 1920px — a armadilha de R1

### Implementação da User Story 3

- [X] T037 [US3] Implementar a detecção de transbordo com `ResizeObserver` em `frontend/components/rows/MovieRow.tsx`, renderizando as setas apenas quando há conteúdo além da borda (R7, FR-014)
- [X] T038 [US3] Implementar avançar e retroceder por `scrollBy()` em `frontend/components/rows/MovieRow.tsx`, desabilitando nas extremidades (FR-014)
- [X] T039 [US3] Aplicar `min-width: 0` no contêiner pai da trilha em `frontend/components/rows/rows.module.css` — sem isso o transbordo vaza para a página e quebra SC-005 (R1)
- [X] T040 [US3] Desligar o deslocamento animado sob `prefers-reduced-motion` em `frontend/components/rows/rows.module.css` (FR-018)
- [X] T041 [US3] Ajustar o layout responsivo da trilha e do cartão em `frontend/components/rows/rows.module.css` para 360px a 1920px (SC-005)
- [X] T042 [P] [US3] Implementar `frontend/components/rows/MovieRowSkeleton.tsx` com a mesma altura da trilha final, evitando deslocamento do conteúdo (FR-028)

**Checkpoint**: as trilhas são navegáveis em qualquer entrada e em qualquer largura

---

## Phase 6: User Story 4 — Entender por que um filme não tem sessão (Priority: P3)

**Goal**: A página do filme sem sessão explica o motivo e informa a estreia

**Independent Test**: Acionar um cartaz da trilha Em breve e confirmar a composição completa, a
data de estreia e a explicação

### Testes da User Story 4

- [X] T043 [P] [US4] Escrever em `backend/tests/test_home_rows_api.py` o teste de que o detalhe do filme passou a devolver `release_date`
- [X] T044 [P] [US4] Escrever em `frontend/tests/rows.test.tsx` os três casos da mensagem: com estreia futura, sem data conhecida, e com data no passado (FR-025 a FR-027)

### Implementação da User Story 4

- [X] T045 [US4] Acrescentar `release_date` ao serializer de detalhe em `backend/apps/catalog/serializers.py`, sem remover nem alterar campo algum (contracts/home-api.md)
- [X] T046 [US4] Exibir "Estreia em DD/MM/AAAA" na página em `frontend/app/filmes/[slug]/page.tsx` quando houver data futura conhecida (FR-025)
- [X] T047 [US4] Ajustar a mensagem de ausência de sessões em `frontend/app/filmes/[slug]/page.tsx` para "No momento, este filme não possui sessões programadas." (FR-026)
- [X] T048 [US4] Omitir a linha de estreia quando a data for desconhecida ou estiver no passado, em `frontend/app/filmes/[slug]/page.tsx` — nunca inventar nem estimar (FR-027, SC-009)

**Checkpoint**: nenhum cartaz das trilhas leva a uma página que só diz "não tem nada"

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T049 [P] Escrever em `frontend/tests/e2e/home-rows.spec.ts` o percurso trilha → página do filme → sessões (Princípio I)
- [X] T050 [P] Escrever em `backend/tests/test_home_rows_api.py` o teste de resiliência: a resposta é idêntica sem `TMDB_API_KEY` configurada (FR-022, SC-004)
- [X] T051 [P] Registrar a nova superfície em `README.md`, na seção do que está pronto
- [X] T052 [P] Adicionar à seção de decisões do `README.md` por que a trilha usa `scroll-snap` e o carrossel não (R1)
- [X] T053 Verificar SC-007 medindo o tempo até a primeira trilha visível e navegável, e registrar o número no `README.md`
- [X] T054 Executar as verificações de `specs/004-home-movie-rows/quickstart.md`: trilha vazia omitida, setas só com transbordo, sem rolagem horizontal, e resiliência ao TMDb
- [X] T055 Percorrer os sete princípios da constitution contra a aplicação rodando e registrar desvios remanescentes nas limitações conhecidas do `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende da Phase 1 — **BLOQUEIA todas as user stories**
- **User Stories (Phases 3–6)**: todas dependem da Phase 2
- **Polish (Phase 7)**: depende das stories desejadas

### User Story Dependencies

- **US1 (P1)**: depende apenas da Foundational. Cria `MovieRow` e `MovieCard`, que as outras usam.
- **US2 (P2)**: depende da US1 — reusa os mesmos componentes, só muda a origem dos dados.
- **US3 (P2)**: depende da US1, porque refina o `MovieRow` criado lá.
- **US4 (P3)**: independente das outras três. Toca só a página do filme e pode ser adiantada.

### Dependências pontuais

- T002 depende de T001
- T005, T006 e T007 dependem de T004
- T011 depende de T001 e T002
- T012 e T013 dependem de T010 e T011
- T023 depende de T003 e T020
- T024 depende de T016 e T023
- T031 depende de T013
- T037 e T038 dependem de T023
- T039 depende de T024 — só dá para verificar o vazamento com a home montada
- T046 a T048 dependem de T045
- T051 depende de T024 e T032

### Parallel Opportunities

- **Phase 1**: T003 em paralelo com T001 e T002
- **Phase 2**: T008 e T009 em paralelo; T015 em paralelo com todo o back-end
- **US1**: T017, T018 e T019 em paralelo
- **US2**: T027 a T030 em paralelo
- **US3**: T034, T035, T036 e T042 em paralelo
- **US4**: independente — T043 a T048 podem correr junto com US2 e US3
- **Phase 7**: T049 a T052 em paralelo

---

## Parallel Example: Foundational

```bash
# Testes de expiração e desduplicação, arquivo distinto do código:
Task: "Expiração de is_trending em backend/tests/test_tmdb_sync.py"
Task: "Desduplicação entre listas em backend/tests/test_tmdb_sync.py"

# Fundação do front-end, em paralelo com todo o back-end:
Task: "Tipos das trilhas em frontend/lib/types.ts"
Task: "Estilos da trilha em frontend/components/rows/rows.module.css"
```

---

## Implementation Strategy

### MVP (US1 + US2)

A US1 sozinha entrega a trilha que sustenta a compra, mas deixa a home com uma faixa só abaixo do
carrossel — o pedido era povoar a tela. As duas juntas são o menor incremento que cumpre isso.

1. Phase 1: Setup
2. Phase 2: Foundational — **bloqueia tudo**
3. Phase 3: US1 — Em cartaz na home
4. Phase 4: US2 — Em alta e Em breve
5. **PARAR E VALIDAR**: home povoada, todos os cartazes conduzindo à página certa
6. Demonstrável neste ponto

### Entrega incremental

1. Setup + Foundational → as três trilhas são consultáveis pela API
2. + US1 → Em cartaz na home
3. + US2 → home povoada (**MVP**)
4. + US3 → navegação sólida em qualquer dispositivo
5. + US4 → o filme sem sessão explica o motivo
6. + Phase 7 → e2e, README e a revisão da constitution

### Ordem recomendada com uma pessoa

Sequencial, na ordem das fases. A US4 é a única genuinamente independente: se travar em qualquer
ponto das trilhas, dá para avançar nela sem esperar.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- **Nenhuma dependência nova**; uma migração, sem backfill
- **T039 é a tarefa que mais parece supérflua e menos é**: sem `min-width: 0` no contêiner pai, o
  transbordo da trilha vaza e a página inteira rola para o lado (R1, SC-005)
- **T007 idem**: sem zerar `is_trending` antes de remarcar, a trilha Em alta nunca esvazia
- T033 altera arquivo da feature 001 — justificado em Complexity Tracking do plan.md
- O endpoint de highlights permanece separado e intocado (R4)
- Commitar por contexto, com mensagem descritiva (Princípio VI)
