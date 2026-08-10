---
description: "Task list for feature implementation"
---

# Tasks: Carrossel de Highlights de Filmes

**Input**: Design documents from `/specs/001-movie-highlights-carousel/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/highlights-api.md](./contracts/highlights-api.md)

**Tests**: Incluídos. Não por padrão do template, mas porque a Constitution v1.0.0 obriga prova
no gate do Princípio IV (endpoint público sem vazamento de dado de gestão) e porque R10 do
`research.md` define onde o erro é caro. Testes fora dessa lista permanecem opcionais.

**Organization**: Tarefas agrupadas por user story. A ordem das fases segue a prioridade do
spec: US1 (P1) → US3 (P1) → US2 (P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (carrossel), US2 (trailer), US3 (ver ingressos)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Back-end**: `backend/` — Django + DRF
- **Front-end**: `frontend/` — Next.js App Router
- Portas: banco **5438**, interface web **5000**, API **8000**

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esqueleto do repositório e ambiente reproduzível nas portas fixadas

- [ ] T001 Criar a estrutura de diretórios `backend/` e `frontend/` conforme a seção Project Structure de `specs/001-movie-highlights-carousel/plan.md`
- [ ] T002 [P] Inicializar o projeto Python em `backend/pyproject.toml` com Django 5.x, djangorestframework, psycopg[binary], django-environ, httpx, django-cors-headers, pytest, pytest-django
- [ ] T003 [P] Inicializar o projeto Next.js 15 (App Router, TypeScript) em `frontend/package.json`, com o script `dev` fixando a porta 5000 (`next dev -p 5000`)
- [ ] T004 Criar `docker-compose.yml` na raiz com os serviços `db` (postgres:16, porta host **5438** mapeada para 5432), `backend` (porta 8000) e `frontend` (porta **5000**)
- [ ] T005 Criar `.env.example` na raiz com `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT=5438`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `TMDB_API_KEY`, `NEXT_PUBLIC_SITE_PORT=5000`, `API_BASE_URL` — todos sem valor real
- [ ] T006 Criar `.gitignore` na raiz cobrindo `.env`, `__pycache__/`, `node_modules/`, `.next/`, `*.sqlite3` e artefatos de teste
- [ ] T007 [P] Configurar lint e formatação do back-end (`ruff`) em `backend/pyproject.toml`
- [ ] T008 [P] Configurar lint e formatação do front-end (ESLint + Prettier) em `frontend/eslint.config.mjs`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Dados, sincronização com o TMDb e o endpoint público que as três user stories consomem

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar

### Projeto Django e banco

- [ ] T009 Criar o projeto Django em `backend/config/` com `settings/base.py` e `settings/dev.py`, lendo variáveis via django-environ
- [ ] T010 Configurar o PostgreSQL em `backend/config/settings/base.py` apontando para a porta **5438**, e `CORS_ALLOWED_ORIGINS` incluindo `http://localhost:5000`
- [ ] T011 Configurar DRF em `backend/config/settings/base.py` com `DEFAULT_AUTHENTICATION_CLASSES` vazio por padrão e permissão padrão `AllowAny` apenas para as rotas públicas declaradas
- [ ] T012 Criar os apps `catalog` e `screening` em `backend/apps/` e registrá-los em `INSTALLED_APPS`

### Modelos

- [ ] T013 [P] Criar os modelos `Genre` e `Movie` em `backend/apps/catalog/models.py` conforme `data-model.md`, incluindo `tmdb_id` único, `slug` único, `certification_br` nulável e as propriedades derivadas `backdrop_url`, `poster_url` e `synopsis_short`
- [ ] T014 [P] Criar o modelo `Trailer` em `backend/apps/catalog/models.py` com `UNIQUE(movie, provider, external_key)` e a constraint condicional de um único `is_primary=True` por filme
- [ ] T015 [P] Criar os modelos `Room` e `Screening` em `backend/apps/screening/models.py` com `UNIQUE(room, starts_at)`, índice composto `(status, starts_at)` e `on_delete=PROTECT` no filme
- [ ] T016 Gerar e aplicar as migrações `catalog.0001` e `screening.0001` em `backend/apps/*/migrations/`

### Integração com o TMDb (Princípio VII)

- [ ] T017 Implementar o cliente TMDb em `backend/apps/catalog/services/tmdb_client.py` com timeout explícito de 10s, chave lida do ambiente e `append_to_response=videos,release_dates` na chamada de detalhe
- [ ] T018 Implementar o mapeamento TMDb → modelos em `backend/apps/catalog/services/tmdb_sync.py`, incluindo a extração da classificação `iso_3166_1="BR"` com preferência por `type=3` (R3) e a escolha do trailer primário na ordem oficial-pt → oficial-en → trailer → teaser (R4)
- [ ] T019 Implementar o comando `backend/apps/catalog/management/commands/sync_tmdb.py` com a flag `--limit`, idempotente por `tmdb_id`
- [ ] T020 [P] Escrever os testes de mapeamento em `backend/tests/test_tmdb_sync.py`: classificação BR ausente vira `null`, filme sem vídeo do YouTube fica sem trailer primário, e uma segunda execução não duplica registros

### Endpoint público de highlights

- [ ] T021 Implementar a regra de elegibilidade em `backend/apps/catalog/selectors.py`: filmes ativos com sessão `published` e `starts_at > agora`, anotados com `next_screening_at`, ordenados ascendente com desempate por título, limitados a 5 (R6/FR-002)
- [ ] T022 Implementar o serializer público em `backend/apps/catalog/serializers.py` seguindo exatamente `contracts/highlights-api.md`, expondo `trailer` como objeto nulável e `has_available_seats` como booleano derivado
- [ ] T023 Implementar `HighlightsView` em `backend/apps/catalog/views.py` como somente leitura e pública, com cache de 60s, e registrar a rota `GET /api/v1/highlights/` em `backend/apps/catalog/urls.py` e `backend/config/urls.py`
- [ ] T024 [P] Escrever os testes de elegibilidade em `backend/tests/test_selectors.py`: sessão passada e sessão em rascunho são excluídas, ordenação pela sessão mais próxima, corte em 5, e catálogo vazio retorna lista vazia
- [ ] T025 [P] Escrever o teste do gate do Princípio IV em `backend/tests/test_highlights_api.py`: a requisição sem autenticação retorna 200 **e** a resposta não contém `status`, preço de custo, capacidade da sala, contagem de assentos vendidos nem identificação de usuário

### Seed do desafio

- [ ] T026 Implementar `backend/apps/catalog/management/commands/seed_demo.py` criando 1 organizador, 2 clientes, 1 usuário de portaria, 2 salas e ao menos 5 filmes com sessões publicadas e futuras, de forma idempotente, imprimindo as credenciais ao final

### Fundação do front-end

- [ ] T027 Criar `frontend/styles/tokens.css` com os tokens de cor, tipografia e espaçamento — fonte única exigida pelo Princípio V — e importá-lo em `frontend/app/layout.tsx`
- [ ] T028 [P] Criar `frontend/lib/types.ts` com os tipos derivados de `contracts/highlights-api.md` e `frontend/lib/api.ts` com o fetch server-side de `/api/v1/highlights/`, tratando timeout e resposta não-200
- [ ] T029 Configurar `frontend/next.config.ts` com `remotePatterns` para `image.tmdb.org`

**Checkpoint**: API de highlights respondendo com dados semeados; front-end pronto para consumir

---

## Phase 3: User Story 1 — Descobrir os filmes em cartaz (Priority: P1) 🎯 MVP

**Goal**: A home exibe um carrossel navegável com os 5 filmes em destaque e todos os seus estados

**Independent Test**: Abrir `http://localhost:5000` sem autenticação e confirmar que os 5 filmes
aparecem com arte, título, classificação, duração, gênero e sinopse; que avançar, retroceder,
saltar por indicador e o ciclo funcionam; e que a rotação automática pausa ao passar o ponteiro

### Testes da User Story 1

- [ ] T030 [P] [US1] Escrever os testes de navegação em `frontend/tests/carousel.test.tsx`: avançar do último volta ao primeiro, retroceder do primeiro vai ao último, e o indicador reflete "n de N" (FR-005, FR-008)
- [ ] T031 [P] [US1] Escrever os testes de pausa em `frontend/tests/carousel.test.tsx`: a rotação automática pausa com o ponteiro sobre a área e com foco de teclado em controle interno, e retoma ao sair (FR-010)
- [ ] T032 [P] [US1] Escrever o teste de movimento reduzido em `frontend/tests/carousel.test.tsx`: com `prefers-reduced-motion: reduce`, a rotação automática não ocorre e a navegação manual continua funcionando (FR-011)

### Implementação da User Story 1

- [ ] T033 [US1] Implementar `frontend/components/highlights/HighlightPanel.tsx` exibindo arte, título, classificação, duração, gênero e sinopse curta, omitindo o selo quando `certification_br` for nulo e a duração quando `runtime_minutes` for nulo (FR-003)
- [ ] T034 [US1] Implementar o fallback de arte em `frontend/components/highlights/HighlightPanel.tsx` para `backdrop_url` nulo ou com falha de carregamento, preservando o contraste do texto (FR-027)
- [ ] T035 [US1] Implementar `frontend/components/highlights/CarouselControls.tsx` com botões reais de avançar, retroceder e indicadores de posição usando `aria-current` no ativo (FR-006, FR-007)
- [ ] T036 [US1] Implementar `frontend/components/highlights/HighlightsCarousel.tsx` com track em `translateX`, índice modular para o ciclo, e transição curta no wrap em vez de rebobinar todos os painéis (R1, FR-008)
- [ ] T037 [US1] Implementar a rotação automática em `frontend/components/highlights/HighlightsCarousel.tsx` com pausa por ponteiro, por foco interno e por `matchMedia('prefers-reduced-motion')` (FR-009, FR-010, FR-011)
- [ ] T038 [US1] Implementar o gesto de deslize por pointer events com limiar de ~50px em `frontend/components/highlights/HighlightsCarousel.tsx` (FR-006)
- [ ] T039 [US1] Implementar a navegação por setas do teclado e aplicar `inert` aos painéis fora de vista em `frontend/components/highlights/HighlightsCarousel.tsx` (FR-025, SC-005)
- [ ] T040 [US1] Aplicar a semântica ARIA de carrossel em `frontend/components/highlights/HighlightsCarousel.tsx`: `role="region"`, `aria-roledescription="carousel"`, painéis como `role="group"` rotulados "n de N", e `aria-live` alternando entre `off` na rotação automática e `polite` na troca iniciada pelo usuário (R9, FR-026)
- [ ] T041 [P] [US1] Implementar `frontend/components/highlights/HighlightsSkeleton.tsx` com a mesma altura do painel final, evitando deslocamento de conteúdo (FR-021)
- [ ] T042 [P] [US1] Implementar `frontend/components/highlights/HighlightsEmpty.tsx` com texto explicativo em pt-BR para catálogo sem destaque (FR-022)
- [ ] T043 [US1] Implementar o estado de erro do carrossel em `frontend/app/page.tsx` com mensagem em pt-BR dizendo o que houve e oferecendo recarregar (FR-024, SC-008)
- [ ] T044 [US1] Montar a home em `frontend/app/page.tsx` como Server Component que busca os highlights e passa os dados por props ao carrossel (R5)
- [ ] T045 [US1] Ajustar o layout responsivo do painel em `frontend/components/highlights/HighlightPanel.tsx` para 360px a 1920px sem rolagem horizontal (SC-007)

**Checkpoint**: US1 completa — o carrossel é navegável e todos os seus estados existem

---

## Phase 4: User Story 3 — Ir do highlight direto para a compra (Priority: P1)

**Goal**: "Ver ingressos" leva à página do filme com as sessões futuras listadas

**Independent Test**: Acionar "Ver ingressos" em cada um dos 5 painéis e confirmar que cada um
leva a `/filmes/{slug}` do filme correto, com ao menos uma sessão listada, sem exigir login

### Testes da User Story 3

- [ ] T046 [P] [US3] Escrever o teste do endpoint de detalhe em `backend/tests/test_movie_detail_api.py`: acesso público retorna 200, lista apenas sessões `published` e futuras, e slug inexistente retorna 404

### Implementação da User Story 3

- [ ] T047 [US3] Implementar o serializer de detalhe do filme com suas sessões futuras em `backend/apps/catalog/serializers.py`, sem expor `status`, preço de custo ou capacidade (Princípio IV)
- [ ] T048 [US3] Implementar `MovieDetailView` em `backend/apps/catalog/views.py` e registrar `GET /api/v1/filmes/<slug>/` em `backend/apps/catalog/urls.py`
- [ ] T049 [US3] Adicionar o botão "Ver ingressos" como ação primária em `frontend/components/highlights/HighlightPanel.tsx`, apontando para `movie_path` (FR-004, FR-018)
- [ ] T050 [US3] Implementar o estado esgotado do botão em `frontend/components/highlights/HighlightPanel.tsx` quando `has_available_seats` for `false`, sem quebrar o layout (FR-020)
- [ ] T051 [US3] Implementar a página mínima do filme em `frontend/app/filmes/[slug]/page.tsx` com cartaz, título, sinopse e lista de sessões futuras, acessível sem autenticação (FR-019, Complexity Tracking do plan.md)
- [ ] T052 [US3] Implementar o estado de filme não encontrado em `frontend/app/filmes/[slug]/not-found.tsx` com mensagem em pt-BR (FR-024)

**Checkpoint**: US1 + US3 formam o MVP — descobrir um filme e chegar às suas sessões

---

## Phase 5: User Story 2 — Assistir ao trailer sem sair da página (Priority: P2)

**Goal**: O trailer reproduz dentro do próprio painel, sem modal e sem sair da plataforma

**Independent Test**: Acionar "Trailer" em um filme com trailer e confirmar a reprodução dentro
do painel; fechar e confirmar o retorno à arte; trocar de painel e confirmar que o vídeo parou

### Testes da User Story 2

- [ ] T053 [P] [US2] Escrever o teste de visibilidade do botão em `frontend/tests/trailer.test.tsx`: com `trailer` nulo o botão "Trailer" não é renderizado e o painel não deixa lacuna (FR-015)
- [ ] T054 [P] [US2] Escrever o teste de desmontagem em `frontend/tests/trailer.test.tsx`: trocar de painel ou fechar remove o iframe da árvore, e nunca há dois iframes simultâneos (FR-014, FR-016)

### Implementação da User Story 2

- [ ] T055 [US2] Implementar `frontend/components/highlights/TrailerFrame.tsx` montando o iframe de `youtube-nocookie.com` com `autoplay=1&rel=0&modestbranding=1` apenas após o clique, e desmontando ao fechar (R2, FR-012, FR-017)
- [ ] T056 [US2] Adicionar o botão "Trailer" em `frontend/components/highlights/HighlightPanel.tsx`, renderizado somente quando `trailer` não for nulo (FR-004, FR-015)
- [ ] T057 [US2] Posicionar o `TrailerFrame` sobre a área da arte dentro do contêiner do painel, sem modal e sem navegação externa, em `frontend/components/highlights/HighlightPanel.tsx` (FR-012)
- [ ] T058 [US2] Implementar o controle de fechar o trailer com retorno ao estado de arte em `frontend/components/highlights/TrailerFrame.tsx` (FR-013)
- [ ] T059 [US2] Suspender a rotação automática enquanto o trailer estiver ativo e retomá-la ao fechar, em `frontend/components/highlights/HighlightsCarousel.tsx` (FR-010, cenários 2 e 3 da US2)
- [ ] T060 [US2] Desmontar o trailer ao navegar para outro painel e ao acionar "Ver ingressos", em `frontend/components/highlights/HighlightsCarousel.tsx` (FR-014, FR-016)
- [ ] T061 [US2] Implementar o estado de falha do trailer em `frontend/components/highlights/TrailerFrame.tsx` com mensagem em pt-BR e retorno à arte, mantendo "Ver ingressos" acessível (FR-024, cenário 6 da US2)
- [ ] T062 [US2] Garantir que o botão de fechar e o iframe sejam alcançáveis por teclado sem armadilha de foco em `frontend/components/highlights/TrailerFrame.tsx` (FR-025, SC-005)

**Checkpoint**: as três user stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechar as obrigações da constitution e validar o fluxo inteiro

- [ ] T063 Criar o `README.md` na raiz com passo a passo de setup, as portas 5438/5000/8000, as credenciais do seed, a configuração do TMDb e uma seção honesta de limitações conhecidas (Princípio VI)
- [ ] T064 [P] Criar a seção de uso de IA no `README.md` declarando ferramentas, em que partes do projeto foram usadas e o que foi feito sem IA (Princípio VI)
- [ ] T065 [P] Escrever o teste ponta a ponta em `frontend/tests/e2e/highlights.spec.ts` cobrindo home → abrir trailer → fechar → "Ver ingressos" → sessões listadas (Princípio I)
- [ ] T066 [P] Escrever o teste de resiliência em `backend/tests/test_highlights_api.py` provando que o endpoint responde normalmente sem `TMDB_API_KEY` configurada (Princípio VII, SC-006)
- [ ] T067 Verificar SC-002 e SC-003 medindo o tempo até o primeiro painel legível e até o início do trailer, e registrar os números no `README.md`
- [ ] T068 [P] Percorrer o carrossel apenas por teclado e com leitor de tela, corrigindo foco visível, rótulos e anúncios em `frontend/components/highlights/` (SC-005, FR-026)
- [ ] T069 [P] Revisar todas as mensagens de erro e estados vazios em `frontend/components/highlights/` garantindo que nenhuma seja genérica do tipo "algo deu errado" (SC-008, Princípio V)
- [ ] T070 Executar o `quickstart.md` do zero em ambiente limpo e corrigir qualquer divergência encontrada
- [ ] T071 Percorrer os sete princípios da constitution contra a aplicação rodando e registrar desvios remanescentes na seção de limitações do `README.md` (cláusula de Revisão Final da Governance)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende da Phase 1 — **BLOQUEIA todas as user stories**
- **User Stories (Phases 3–5)**: todas dependem da Phase 2
- **Polish (Phase 6)**: depende das user stories desejadas estarem completas

### User Story Dependencies

- **US1 (P1)**: depende apenas da Foundational. É a base visual que US2 e US3 estendem.
- **US3 (P1)**: depende da Foundational. O back-end (T046–T048) é independente de US1 e pode ser
  feito em paralelo; o front-end (T049–T052) toca `HighlightPanel.tsx`, criado em T033.
- **US2 (P2)**: depende da Foundational. Toca `HighlightPanel.tsx` (T033) e
  `HighlightsCarousel.tsx` (T036), então segue US1 na prática.

### Dependências pontuais

- T016 (migrações) depende de T013, T014 e T015
- T021 (elegibilidade) depende de T013 e T015
- T022 e T023 dependem de T021
- T026 (seed) depende de T016 e T019
- T044 (home) depende de T028, T036 e T041–T043
- T059 e T060 dependem de T036 e T055
- T063 (README) depende de T026, para ter as credenciais reais

### Parallel Opportunities

- **Phase 1**: T002, T003, T007, T008 em paralelo
- **Phase 2**: T013, T014, T015 em paralelo; depois T020, T024, T025, T028 em paralelo
- **US1**: T030, T031, T032 em paralelo; T041 e T042 em paralelo com o restante
- **Cruzada**: T046–T048 (back-end de US3) em paralelo com toda a US1
- **Phase 6**: T064, T065, T066, T068, T069 em paralelo

---

## Parallel Example: Foundational

```bash
# Modelos, arquivos independentes:
Task: "Criar Genre e Movie em backend/apps/catalog/models.py"
Task: "Criar Trailer em backend/apps/catalog/models.py"
Task: "Criar Room e Screening em backend/apps/screening/models.py"

# Depois das migrações, testes e fundação do front em paralelo:
Task: "Testes de mapeamento em backend/tests/test_tmdb_sync.py"
Task: "Testes de elegibilidade em backend/tests/test_selectors.py"
Task: "Teste do gate do Princípio IV em backend/tests/test_highlights_api.py"
Task: "Tipos e cliente de API em frontend/lib/"
```

---

## Implementation Strategy

### MVP (US1 + US3)

O spec dá P1 tanto ao carrossel quanto ao caminho para a compra, e o Princípio I proíbe entregar
um destaque que não leva a lugar nenhum. O MVP é, portanto, as duas juntas:

1. Phase 1: Setup
2. Phase 2: Foundational — **bloqueia tudo**
3. Phase 3: US1 — carrossel navegável com todos os estados
4. Phase 4: US3 — "Ver ingressos" chegando às sessões
5. **PARAR E VALIDAR**: percorrer home → filme → sessões de ponta a ponta
6. Demonstrável neste ponto

### Entrega incremental

1. Setup + Foundational → API respondendo com dados semeados
2. + US1 → home com carrossel navegável
3. + US3 → fluxo de descoberta até as sessões (**MVP**)
4. + US2 → trailer dentro do painel
5. + Phase 6 → README, e2e, acessibilidade e a revisão final da constitution

### Ordem recomendada com uma pessoa

Sequencial, na ordem das fases. A única paralelização que vale a pena sozinho é adiantar
T046–T048 (back-end de US3) enquanto se espera qualquer validação de US1, porque não há conflito
de arquivo.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- Nenhuma tarefa cria escrita de ocupação de assento — isso pertence à feature de reserva, e
  antecipá-la violaria o Princípio II (ver a fronteira em `data-model.md`)
- A porta 8000 do Django é escolha do plano, não exigência do usuário; se mudar, ajustar T004,
  T005 e T063
- Commitar a cada tarefa ou grupo lógico, com mensagem descritiva (Princípio VI)
