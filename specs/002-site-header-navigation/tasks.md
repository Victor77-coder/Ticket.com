---

description: "Task list — Cabeçalho Global do Site"
---

# Tasks: Cabeçalho Global do Site

**Input**: Design documents from `/specs/002-site-header-navigation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: incluídos. A Constitution exige prova onde um princípio NÃO NEGOCIÁVEL está em jogo —
aqui é o **Princípio IV**: `GET /api/v1/busca/` é público e não pode vazar campo de gestão. Os
demais testes cobrem as duas garantias que mais quebram na prática (corrida de respostas e
navegação por teclado) e são o diferencial que o desafio avalia.

**Organization**: tarefas agrupadas por user story, para que cada uma seja implementável e
testável de forma independente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: a qual user story a tarefa pertence (US1, US2, US3)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

Web app com `backend/` (Django) e `frontend/` (Next.js) separados, conforme a **Structure
Decision** do `plan.md`. O cabeçalho vive em `frontend/components/header/`, em paralelo a
`frontend/components/highlights/` da feature 001.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: preparar o terreno sem introduzir comportamento. Nenhuma dependência nova é
instalada nesta feature — nem no back-end, nem no front-end.

- [X] T001 [P] Adicionar os tokens do cabeçalho em `frontend/styles/tokens.css`: `--altura-cabecalho`, `--z-cabecalho`, `--largura-max-sugestoes` e `--altura-item-sugestao`. Nenhum valor de cor ou espaçamento novo pode nascer fora deste arquivo (Princípio V, FR-030)
- [X] T002 [P] Criar `frontend/components/header/header.module.css` com as classes vazias da estrutura do cabeçalho (faixa, conteúdo, marca, busca, conta), consumindo apenas variáveis de `tokens.css`
- [X] T003 Registrar a linha de base verde rodando `backend/tests/` (`pytest`) e `frontend/tests/` (`npm run test`) antes de qualquer alteração — regressão introduzida por esta feature precisa ser distinguível de falha preexistente

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: o invólucro onde as três user stories se encaixam. Todas renderizam dentro dele.

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase terminar.

- [X] T004 Criar `frontend/components/header/SiteHeader.tsx` como server component, com os três espaços nomeados (identidade, busca, conta) e a semântica de região de navegação do site exigida pelo FR-027. Os espaços ficam vazios nesta fase
- [X] T005 Montar `<SiteHeader />` acima de `{children}` em `frontend/app/layout.tsx`, garantindo que ele apareça em todas as páginas (FR-001)
- [X] T006 Ajustar `--altura-painel` em `frontend/styles/tokens.css` descontando `--altura-cabecalho`, para que o carrossel da feature 001 não fique espremido pela nova faixa (R7)

**Checkpoint**: o cabeçalho existe, está em todas as páginas e não quebrou o carrossel — ainda sem conteúdo.

---

## Phase 3: User Story 1 - Reconhecer onde se está e voltar ao início (Priority: P1) 🎯 MVP

**Goal**: entregar a faixa persistente com a identidade **ticket.com**, que leva à home de
qualquer página e sobrevive à rolagem, à impressão e à tela de 360 px.

**Independent Test**: navegar da home para `/filmes/{slug}` e confirmar que o cabeçalho está nas
duas com a mesma composição; acionar **ticket.com** na página do filme e confirmar o retorno à
home.

### Tests for User Story 1

> Escrever primeiro e confirmar que falham antes da implementação.

- [X] T007 [P] [US1] Escrever `frontend/tests/header.test.tsx`: o cabeçalho renderiza o texto "ticket.com", o wordmark é um link para `/`, e o elemento é exposto como região de navegação do site
- [X] T008 [P] [US1] Escrever `frontend/tests/e2e/header.spec.ts`: o cabeçalho está presente na home **e** em `/filmes/{slug}` com os mesmos elementos na mesma ordem; acionar o wordmark na página do filme retorna à home

### Implementation for User Story 1

- [X] T009 [US1] Criar `frontend/components/header/BrandMark.tsx` — wordmark textual "ticket.com" (não imagem) com tratamento tipográfico autoral e `Link` para `/`, conforme R8
- [X] T010 [US1] Aplicar `position: sticky; top: 0` e `--z-cabecalho` na faixa em `frontend/components/header/header.module.css`, sem tirar o cabeçalho do fluxo (R7, FR-006)
- [X] T011 [US1] Implementar o layout responsivo de 360 px a 1920 px em `frontend/components/header/header.module.css`, mantendo os três espaços alcançáveis e sem rolagem horizontal (FR-005, SC-007)
- [X] T012 [US1] Atualizar `metadata.title` em `frontend/app/layout.tsx` para `"ticket.com — ingressos de cinema"` (FR-004)
- [X] T013 [US1] Adicionar a regra de impressão em `frontend/components/header/header.module.css` para o cabeçalho não sobrepor conteúdo impresso (caso de borda do spec)

**Checkpoint**: US1 completa e demonstrável sozinha — o site tem identidade e caminho de volta. É o MVP desta feature.

---

## Phase 4: User Story 2 - Encontrar um filme pelo nome sem sair da página (Priority: P2)

**Goal**: busca de filmes por título com sugestões ancoradas ao campo, cobrindo os quatro
estados (buscando, com resultados, sem resultados, erro) e operável só pelo teclado.

**Independent Test**: digitar parte do título de um filme do catálogo e confirmar que ele aparece
nas sugestões; acioná-lo e chegar à página do filme; digitar um termo inexistente e receber a
mensagem em português.

### Tests for User Story 2

> Escrever primeiro e confirmar que falham antes da implementação.

- [X] T014 [P] [US2] Escrever `backend/tests/test_search_api.py` cobrindo os 13 casos tabelados em `specs/002-site-header-navigation/contracts/search-api.md`, incluindo o **gate do Princípio IV**: comparar o conjunto de chaves da resposta com o conjunto permitido, em vez de inspecionar campo a campo
- [X] T015 [P] [US2] Escrever `frontend/tests/search.test.tsx` cobrindo os 11 casos tabelados em `specs/002-site-header-navigation/contracts/search-proxy.md`. O caso 2 (resposta antiga resolvendo depois da nova) é o teste central da feature — ele é quem prova SC-005

### Implementation for User Story 2 — back-end

- [X] T016 [US2] Adicionar `"django.contrib.postgres"` a `INSTALLED_APPS` em `backend/config/settings/base.py`. Sem isso o lookup `__unaccent` não é registrado e a consulta falha com `FieldError`, não com erro de banco (R2)
- [X] T017 [US2] Criar `backend/apps/catalog/migrations/0002_unaccent_extension.py` usando `UnaccentExtension()` de `django.contrib.postgres.operations`
- [X] T018 [US2] Implementar `search_movies(termo, limite=6)` em `backend/apps/catalog/selectors.py`: `strip()`, truncamento em 80 caracteres, retorno curto para termo vazio sem tocar o banco, filtro `is_active=True` + `title__unaccent__icontains`, ordenação prefixo-antes-de-conteúdo com desempate por título, e busca de `limite + 1` linhas para derivar `truncated` sem um `COUNT(*)` separado
- [X] T019 [US2] Adicionar `SearchResultSerializer` em `backend/apps/catalog/serializers.py` com exatamente `slug`, `title`, `poster_url`, `year` e `movie_path`. Não reaproveitar `MovieDetailSerializer` — ele arrasta sessões para uma resposta pública
- [X] T020 [US2] Adicionar `SearchView` em `backend/apps/catalog/views.py` declarando `permission_classes = [AllowAny]` e `authentication_classes = []` **explicitamente**, no mesmo padrão das views públicas existentes
- [X] T021 [US2] Registrar `path("busca/", SearchView.as_view(), name="busca")` em `backend/apps/catalog/urls.py`
- [X] T022 [US2] Rodar `backend/tests/test_search_api.py` até verde e conferir a extensão com `\dx unaccent`, conforme o passo 2 de `specs/002-site-header-navigation/quickstart.md`

### Implementation for User Story 2 — front-end

- [X] T023 [P] [US2] Adicionar os tipos `SearchSuggestion` e `SearchResponse` em `frontend/lib/types.ts`, derivados de `contracts/search-api.md`
- [X] T024 [US2] Adicionar `fetchSearch(termo, limite)` em `frontend/lib/api.ts`, reutilizando o `getJson` existente e o timeout de 8 s já estabelecido
- [X] T025 [US2] Criar `frontend/app/api/busca/route.ts` — Route Handler `GET` com `export const dynamic = "force-dynamic"`, repassando o payload sem reformatar e traduzindo falha do Django em mensagem pt-BR. Nenhum corpo de erro do Django, nome de host interno ou valor de `API_BASE_URL` pode atravessar (R1, `contracts/search-proxy.md`)
- [X] T026 [US2] Criar `frontend/lib/search-client.ts` com os três mecanismos de R3: debounce de 250 ms, `AbortController` e guarda por número de sequência. `AbortError` é tratado como não-erro e não pinta o estado de erro na tela
- [X] T027 [US2] Criar `frontend/components/header/SearchSuggestions.tsx` com os quatro estados **visualmente distintos** — `buscando`, `com-resultados`, `sem-resultados` e `erro` — mais o aviso de `truncated`. `sem-resultados` nunca pode ser derivado de "lista vazia": `buscando` também produz lista vazia (FR-012, FR-013, SC-008)
- [X] T028 [US2] Criar `frontend/components/header/SearchBox.tsx` implementando o combobox WAI-ARIA de R4: `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-autocomplete="list"` e **foco virtual** via `aria-activedescendant` — o foco do DOM nunca sai do input. Setas movem o destaque, Enter aciona, Esc fecha, `maxLength` de 80 caracteres
- [X] T029 [US2] Adicionar a região `aria-live="polite"` de contagem de resultados em `frontend/components/header/SearchBox.tsx`, anunciando só quando a busca conclui — não a cada tecla (FR-027)
- [X] T030 [US2] Tratar o fechamento por perda de foco em `frontend/components/header/SearchBox.tsx` ignorando o caso em que o novo alvo do foco está dentro da própria lista, senão o clique na sugestão nunca registra (problema comum listado no quickstart)
- [X] T031 [US2] Montar `<SearchBox />` no espaço de busca de `frontend/components/header/SiteHeader.tsx`
- [X] T032 [US2] Escrever os estilos da busca e do painel de sugestões em `frontend/components/header/header.module.css`, consumindo apenas tokens — inclusive o estado de destaque da opção ativa, que não pode ser comunicado só por cor (FR-028)
- [X] T033 [US2] Estender `frontend/tests/e2e/header.spec.ts` com o percurso completo: digitar três letras → sugestão aparece → acionar → página do filme; e o percurso do termo sem resultado
- [X] T034 [US2] Rodar `frontend/tests/search.test.tsx` e a suíte e2e até verde

**Checkpoint**: US1 e US2 completas e independentes. O cabeçalho está entregue com dois dos três elementos e pode ir ao ar.

---

## Phase 5: User Story 3 - Ver o estado da própria conta (Priority: P3) 🚧 PARCIALMENTE BLOQUEADA

**Goal**: o ponto de acesso à conta com seus dois estados — visitante e autenticado.

**Independent Test**: como visitante, o ícone está presente, é anunciado por sua função e conduz
ao caminho de entrada; com sessão ativa, o cabeçalho identifica de quem é.

> **⚠️ Bloqueio registrado em [plan.md → Complexity Tracking](./plan.md#complexity-tracking)**
>
> O FR-022 (decisão do usuário) coloca login/logout na feature de autenticação, e o FR-023 proíbe
> que o ponto de acesso conduza a um destino inexistente. Hoje não existe `/entrar`, não existe
> sessão e não existe estado autenticado para ler.
>
> **T035 e T036 podem ser feitas agora** — o componente e seus testes são escritos neste branch.
> **T037 e T038 NÃO PODEM ser executadas** até a feature de autenticação entregar o caminho de
> entrada. Montar o ícone antes disso entrega um link para o nada, o que o Princípio I e o
> Princípio V proíbem.

### Implementation for User Story 3 — liberado

- [X] T035 [P] [US3] Criar `frontend/components/header/AccountButton.tsx` com ícone de pessoa em SVG inline autoral (não ícone genérico de biblioteca), nome acessível em português descrevendo a função, e os dois estados diferenciáveis por forma e texto — nunca só por cor (FR-020, FR-021, FR-028)
- [X] T036 [P] [US3] Estender `frontend/tests/header.test.tsx` com o bloco do `AccountButton`: nome acessível presente, estado de visitante convida a entrar, estado autenticado identifica a sessão, e o elemento é anunciado por função e não como imagem sem descrição

### Implementation for User Story 3 — 🚧 bloqueado pela feature de autenticação

- [ ] T037 [US3] 🚧 **NÃO EXECUTAR AINDA** — Montar `<AccountButton />` no espaço de conta de `frontend/components/header/SiteHeader.tsx`, apontando para o caminho de entrada. Desbloqueia quando a feature de autenticação entregar a rota (FR-023)
- [ ] T038 [US3] 🚧 **NÃO EXECUTAR AINDA** — Estender `frontend/tests/e2e/header.spec.ts` com o percurso visitante → caminho de entrada → estado autenticado no cabeçalho, e com a volta ao estado de visitante quando a sessão expira (FR-024)

**Checkpoint**: com T035 e T036 feitas, o componente existe e está testado, mas não montado. A US3 só fecha depois da autenticação.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: fechar as dívidas de processo e verificar as garantias transversais.

- [X] T039 Criar `README.md` na raiz do repositório — **dívida herdada da feature 001** e exigida pelo Princípio VI. Deve conter: passo a passo de setup com PostgreSQL, as portas 5438/5003/8000, as credenciais dos quatro usuários de seed, a migração da extensão `unaccent` que esta feature introduz, as variáveis de ambiente, a declaração de uso de IA e uma seção honesta de limitações conhecidas — incluindo o bloqueio da US3
- [X] T040 [P] Registrar em `.env.example` que o Route Handler `/api/busca` reutiliza `API_BASE_URL` e que **nenhuma variável nova** é necessária, para não parecer omissão
- [X] T041 [P] Percorrer `specs/002-site-header-navigation/quickstart.md` ponta a ponta em ambiente limpo e corrigir toda divergência encontrada
- [X] T042 Verificar `prefers-reduced-motion` no cabeçalho e na abertura da lista em `frontend/components/header/header.module.css` — a supressão global já existe em `tokens.css`, o que falta é confirmar que nenhuma animação nova escapou (FR-032)
- [X] T043 Verificar 360 px a 1920 px sem rolagem horizontal e confirmar que o carrossel da home continua com a primeira dobra utilizável depois do ajuste de T006; ajustar `frontend/styles/tokens.css` e `frontend/components/header/header.module.css` se necessário (SC-007, R7)
- [X] T044 Percorrer o cabeçalho inteiro só pelo teclado, do wordmark ao último item de sugestão, e fixar o percurso como asserção em `frontend/tests/e2e/header.spec.ts`: foco visível em cada parada, sem armadilha de foco (SC-006)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Fase 2)**: depende da Fase 1 — **bloqueia todas as user stories**
- **US1 (Fase 3)**: depende da Fase 2
- **US2 (Fase 4)**: depende da Fase 2. Independente da US1 — a busca não precisa do wordmark
- **US3 (Fase 5)**: depende da Fase 2 para T035/T036; **T037 e T038 dependem da feature de autenticação**, externa a este plano
- **Polish (Fase 6)**: depende das user stories que se pretende entregar

### User Story Dependencies

- **US1 (P1)**: nenhuma dependência de outra story
- **US2 (P2)**: nenhuma dependência da US1. Compartilha apenas o invólucro da Fase 2
- **US3 (P3)**: nenhuma dependência da US1/US2. Bloqueada por uma feature externa, não por outra story

### Within Each User Story

- Testes escritos e falhando antes da implementação
- Back-end antes do front-end na US2 — o proxy não tem o que repassar sem o endpoint
- `search-client.ts` antes de `SearchBox.tsx`; `SearchSuggestions.tsx` pode andar em paralelo
- Montagem no `SiteHeader` por último, quando o componente já passa nos próprios testes

### Parallel Opportunities

- **Fase 1**: T001 e T002 em paralelo
- **US1**: T007 e T008 em paralelo (arquivos de teste distintos)
- **US2**: T014 (teste de back-end) e T015 (teste de front-end) em paralelo; T023 em paralelo com o bloco de back-end
- **US2 com equipe**: o bloco de back-end (T016–T022) e o de front-end (T023–T034) só se encontram em T024 — duas pessoas podem tocá-los em paralelo até lá, desde que o contrato em `contracts/search-api.md` seja respeitado dos dois lados
- **US3**: T035 e T036 em paralelo
- **Fase 6**: T040 e T041 em paralelo

---

## Parallel Example: User Story 2

```bash
# Os dois testes que definem o contrato, escritos antes da implementação:
Task: "Escrever backend/tests/test_search_api.py cobrindo os 13 casos de contracts/search-api.md"
Task: "Escrever frontend/tests/search.test.tsx cobrindo os 11 casos de contracts/search-proxy.md"

# Depois, os dois lados do contrato em paralelo:
Task: "Back-end: selectors → serializer → view → url (T016–T022)"
Task: "Front-end: tipos → api → route handler → search-client (T023–T026)"
```

---

## Implementation Strategy

### MVP First (US1)

1. Fase 1 (Setup) → Fase 2 (Foundational)
2. Fase 3 (US1)
3. **PARAR E VALIDAR**: cabeçalho presente em todas as páginas, wordmark voltando à home, 360 px sem rolagem horizontal
4. Já é entregável: o site ganha identidade e caminho de volta

### Entrega Incremental

1. Setup + Foundational → invólucro pronto
2. **+ US1** → identidade e navegação → validar → entregar (MVP)
3. **+ US2** → busca com sugestões → validar → entregar
4. **+ T039 (README)** → fecha a dívida do Princípio VI, que já vem de duas features
5. **+ US3** → só depois que a feature de autenticação existir

### A decisão de sequenciamento que sobra

Se o ícone de conta for prioridade, o caminho não é forçá-lo aqui — é rodar `/speckit-specify`
da autenticação antes de implementar esta feature. As tarefas T037 e T038 já estão escritas e
esperam apenas o destino existir.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- Nenhuma dependência nova é instalada nesta feature, nem no back-end nem no front-end
- Nenhum valor de cor ou espaçamento pode nascer dentro de `header.module.css` — se falta, define-se antes em `tokens.css`
- Commit a cada tarefa ou grupo lógico, com mensagem descritiva (Princípio VI)
- Parar em qualquer checkpoint para validar a story isoladamente
- **Restrição do Princípio II reafirmada**: nenhuma tarefa desta lista escreve ocupação de assento nem antecipa a constraint `UNIQUE(sessão, assento)` — a feature é somente leitura
