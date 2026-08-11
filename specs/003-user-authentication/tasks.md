---
description: "Task list for feature implementation"
---

# Tasks: Autenticação e Acesso à Conta

**Input**: Design documents from `/specs/003-user-authentication/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/auth-api.md](./contracts/auth-api.md)

**Tests**: Incluídos. A Constitution v1.0.0 obriga prova no gate do Princípio IV, e R9 do
`research.md` concentra os demais onde o erro tem consequência de segurança — mensagem uniforme,
limite de tentativas e validação do destino de retorno.

**Organization**: Tarefas agrupadas por user story. Ordem das fases pela prioridade do spec:
US1 (P1) → US2 (P1) → US3 (P2).

**Nenhuma migração nova.** O modelo de usuário e a tabela de sessões já existem.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (entrar), US2 (sair), US3 (permanecer reconhecido)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Back-end**: `backend/apps/accounts/` — Django + DRF
- **Front-end**: `frontend/app/`, `frontend/components/header/`, `frontend/lib/`
- Portas: interface **5003**, API **8000**, banco **5438**

---

## Phase 1: Setup

**Purpose**: Configuração de sessão e de autenticação, sem ainda expor endpoint

- [X] T001 Configurar a sessão em `backend/config/settings/base.py`: `SESSION_COOKIE_AGE = 1209600` (duas semanas, padrão do Django), `SESSION_EXPIRE_AT_BROWSER_CLOSE = False` e `SESSION_ENGINE` no banco (R5)
- [X] T002 Adicionar `rest_framework.authentication.SessionAuthentication` a `DEFAULT_AUTHENTICATION_CLASSES` em `backend/config/settings/base.py`, mantendo `IsAuthenticated` como permissão padrão
- [X] T003 [P] Definir as constantes do limite de tentativas em `backend/config/settings/base.py`: 5 falhas, janela de 15 minutos (R4)
- [X] T004 Registrar `apps.accounts.urls` sob `api/v1/auth/` em `backend/config/urls.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Descrição da sessão e sua resolução no servidor — consumidas pelas três stories

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar

- [X] T005 Criar `SessionSerializer` em `backend/apps/accounts/serializers.py` expondo **apenas** `nome` (nome de exibição montado no servidor) e `papel`, conforme `contracts/auth-api.md`
- [X] T006 Implementar `SessionView` (`GET /api/v1/auth/me/`) em `backend/apps/accounts/views.py`, devolvendo 200 com a sessão ou 401 quando não houver — o 401 é estado normal, não falha
- [X] T007 Criar `backend/apps/accounts/urls.py` com as três rotas de `contracts/auth-api.md`
- [X] T008 [P] Escrever o teste do gate do Princípio IV em `backend/tests/test_auth_api.py`: a resposta de sessão não contém `password`, hash, `id`, `email`, `last_login`, `is_staff` nem `is_superuser` (FR-023, SC-006)
- [X] T009 [P] Adicionar o tipo `Sessao` em `frontend/lib/types.ts` com `nome` e `papel`, derivado de `contracts/auth-api.md`
- [X] T010 Criar `frontend/lib/session.ts` com `getSessao()`: lê o cookie via `cookies()`, chama `/api/v1/auth/me/` no Django e devolve a sessão ou `null` (R6)
- [X] T011 Adicionar `fetchSession`, `postLogin` e `postLogout` em `frontend/lib/api.ts`, repassando o cookie de sessão na chamada servidor-a-servidor
- [X] T012 [P] Definir os estilos da tela de entrada em `frontend/app/entrar/entrar.module.css` usando exclusivamente os tokens de `frontend/styles/tokens.css` (Princípio V)

**Checkpoint**: a sessão é descritível e resolvível no servidor; nada ainda a cria

---

## Phase 3: User Story 1 — Entrar na conta (Priority: P1) 🎯 MVP

**Goal**: O visitante entra pelo cabeçalho e volta à página de onde partiu, já identificado

**Independent Test**: A partir da home, acionar o ícone de conta, entrar com `cliente1` /
`desafio2026`, e confirmar o retorno à home com o cabeçalho exibindo o nome

### Testes da User Story 1

- [X] T013 [P] [US1] Escrever em `backend/tests/test_auth_api.py` o teste da mensagem uniforme: usuário inexistente, senha errada e conta inativa produzem **a mesma** resposta 401 e a mesma frase (FR-004, SC-005)
- [X] T014 [P] [US1] Escrever em `backend/tests/test_auth_api.py` o teste de entrada bem-sucedida para os quatro usuários semeados, verificando que cada um recebe o próprio papel (SC-002)
- [X] T015 [P] [US1] Escrever em `backend/tests/test_auth_api.py` os testes de campo faltando (400) e de corpo malformado
- [X] T016 [P] [US1] Escrever `backend/tests/test_auth_throttle.py`: cinco falhas seguidas passam a responder 429 com o tempo de espera, uma entrada bem-sucedida zera o contador, e o bloqueio é por par origem+identificador (FR-007)
- [X] T017 [P] [US1] Escrever em `frontend/tests/auth.test.tsx` o teste de validação do destino de retorno: `//exemplo.com`, `/\exemplo.com` e `https://exemplo.com` são descartados em favor de `/` (FR-011)

### Implementação da User Story 1

- [X] T018 [US1] Implementar o contador de tentativas em `backend/apps/accounts/services/throttle.py`, chaveado por origem e identificador, com janela deslizante no cache (R4)
- [X] T019 [US1] Criar `LoginSerializer` em `backend/apps/accounts/serializers.py` validando presença de `username` e `password` antes de qualquer tentativa de autenticação (FR-006)
- [X] T020 [US1] Implementar `LoginView` (`POST /api/v1/auth/login/`) em `backend/apps/accounts/views.py`, usando `authenticate()` e devolvendo **uma única** mensagem quando ele retornar `None` (FR-004, R3)
- [X] T021 [US1] Integrar o contador de tentativas em `backend/apps/accounts/views.py`: consultar antes de autenticar, incrementar na falha, zerar no sucesso, responder 429 com `retry_after_seconds` (FR-007)
- [X] T022 [US1] Implementar a validação do destino de retorno em `frontend/lib/session.ts`: aceitar apenas caminho começando por `/` e não por `//` nem `/\` (FR-011, R7)
- [X] T023 [US1] Implementar o Route Handler `frontend/app/api/entrar/route.ts`: repassa ao Django e, no sucesso, emite o cookie `httpOnly`, `sameSite=lax`, `path=/`, `maxAge=1209600`, com `secure` fora de desenvolvimento (R1)
- [X] T024 [US1] Implementar a tela de entrada em `frontend/app/entrar/page.tsx` com campos rotulados, `autoComplete` reconhecível por gerenciadores de senha (FR-030) e envio funcional sem JavaScript
- [X] T025 [US1] Implementar o estado de erro da tela em `frontend/app/entrar/page.tsx`: mensagem em pt-BR anunciada a tecnologias assistivas, identificador preservado e senha **nunca** preservada (FR-005, FR-028)
- [X] T026 [US1] Implementar o redirecionamento de usuário já autenticado que acesse `/entrar`, em `frontend/app/entrar/page.tsx` (FR-008)
- [X] T027 [US1] Montar `<AccountButton />` no espaço de conta de `frontend/components/header/SiteHeader.tsx`, passando a sessão resolvida — **desbloqueia a T037 de `002-site-header-navigation`** (FR-024)
- [X] T028 [US1] Passar a sessão do `frontend/app/layout.tsx` ao cabeçalho, resolvendo-a com `getSessao()` (R6)

**Checkpoint**: US1 completa — o visitante entra e o cabeçalho o identifica

---

## Phase 4: User Story 2 — Sair da conta (Priority: P1)

**Goal**: O usuário encerra a sessão pelo cabeçalho e volta ao estado de visitante

**Independent Test**: Autenticado como `cliente1`, encerrar pelo cabeçalho e confirmar que o
ponto de conta volta a convidar a entrar, e que recarregar não restaura a sessão

### Testes da User Story 2

- [X] T029 [P] [US2] Escrever em `backend/tests/test_auth_api.py` o teste de saída: a chave de sessão deixa de resolver depois do logout, e sair sem sessão responde 204 sem erro (FR-014)
- [X] T030 [P] [US2] Escrever em `frontend/tests/auth.test.tsx` os testes do menu de conta: abre com o nome, oferece sair, e fecha por Escape e por clique fora

### Implementação da User Story 2

- [X] T031 [US2] Implementar `LogoutView` (`POST /api/v1/auth/logout/`) em `backend/apps/accounts/views.py`, respondendo 204 inclusive quando não houver sessão
- [X] T032 [US2] Implementar o Route Handler `frontend/app/api/sair/route.ts`: chama o Django e apaga o cookie com `maxAge=0`. Aceita **apenas** `POST` (R8)
- [X] T033 [US2] Criar `frontend/components/header/AccountMenu.tsx` como ilha cliente que envolve o `AccountButton`, controlando abertura e disparando a saída (Complexity Tracking do plan.md)
- [X] T034 [US2] Ligar `AccountMenu` ao `onAbrirConta` do `AccountButton` em `frontend/components/header/SiteHeader.tsx`, mantendo o cabeçalho como server component
- [X] T035 [US2] Estilizar o menu de conta em `frontend/components/header/header.module.css`, reaproveitando as classes `.conta*` já existentes
- [X] T036 [US2] Garantir que o menu seja operável por teclado, com foco visível e sem armadilha de foco, em `frontend/components/header/AccountMenu.tsx` (FR-029, SC-007)
- [X] T037 [US2] Revalidar a rota após a saída em `frontend/components/header/AccountMenu.tsx`, para que o cabeçalho volte ao estado de visitante em todas as páginas (FR-015)

**Checkpoint**: US1 + US2 formam o MVP — entrar e sair funcionam de ponta a ponta

---

## Phase 5: User Story 3 — Permanecer reconhecido durante a navegação (Priority: P2)

**Goal**: A sessão acompanha a navegação e expira sem quebrar nada

**Independent Test**: Entrar, navegar por três páginas confirmando a identificação, invalidar a
sessão e confirmar o retorno ao estado de visitante sem erro visível

### Testes da User Story 3

- [X] T038 [P] [US3] Escrever em `backend/tests/test_auth_api.py` o teste de sessão expirada: `/api/v1/auth/me/` responde 401 e nenhuma exceção é levantada (FR-017)
- [X] T039 [P] [US3] Escrever em `frontend/tests/header.test.tsx` o teste do cabeçalho nos dois estados, agora que o ponto de conta está montado — visitante convida a entrar, autenticado exibe o nome (FR-024, FR-025)
- [X] T040 [P] [US3] Escrever em `frontend/tests/header.test.tsx` o teste de que a diferença entre os dois estados não é comunicada apenas por cor (FR-026)

### Implementação da User Story 3

- [X] T041 [US3] Tratar o 401 como estado de visitante em `frontend/lib/session.ts`, nunca como erro — a página continua utilizável (FR-017)
- [X] T042 [US3] Garantir que o cabeçalho reflita a sessão em todas as rotas, verificando `frontend/app/layout.tsx` e a página do filme
- [X] T043 [US3] Implementar a condução à tela de entrada com explicação em pt-BR quando uma ação exigir conta e a sessão tiver expirado, em `frontend/lib/session.ts` (FR-018 da spec — cenário 4 da US3)
- [X] T044 [US3] Confirmar que o cookie carrega `secure` fora de desenvolvimento, amarrado ao `DEBUG`, em `frontend/app/api/entrar/route.ts`

**Checkpoint**: as três user stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechar o desbloqueio da feature 002 e as obrigações da constitution

- [ ] T045 Estender `frontend/tests/e2e/header.spec.ts` com o percurso visitante → entrada → autenticado → saída, e com a volta ao estado de visitante quando a sessão expira — **fecha a T038 de `002-site-header-navigation`** (SC-009)
- [ ] T046 Marcar T037 e T038 como concluídas em `specs/002-site-header-navigation/tasks.md`, removendo os avisos `🚧 NÃO EXECUTAR AINDA`
- [ ] T047 [P] Atualizar `README.md`: remover "Não há autenticação" das limitações conhecidas, registrar as credenciais como utilizáveis de fato e descrever o fluxo de entrada
- [ ] T048 [P] Registrar em `README.md` a limitação do contador de tentativas viver em cache local — reiniciar o back-end zera os bloqueios (R4)
- [ ] T049 [P] Adicionar à seção de decisões do `README.md` por que o cookie é emitido pelo Next e não repassado do Django (R1)
- [ ] T050 [P] Verificar SC-007 percorrendo entrada e saída apenas pelo teclado, corrigindo foco visível e ordem em `frontend/app/entrar/page.tsx` e `frontend/components/header/AccountMenu.tsx`
- [ ] T051 Executar as verificações de segurança de `specs/003-user-authentication/quickstart.md`: cookie ausente em `document.cookie`, destino de retorno externo descartado, e nenhuma credencial na resposta
- [ ] T052 Percorrer os sete princípios da constitution contra a aplicação rodando e registrar desvios remanescentes nas limitações conhecidas do `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende da Phase 1 — **BLOQUEIA todas as user stories**
- **User Stories (Phases 3–5)**: todas dependem da Phase 2
- **Polish (Phase 6)**: depende das três stories

### User Story Dependencies

- **US1 (P1)**: depende apenas da Foundational. É a base — cria a sessão que as outras duas leem.
- **US2 (P1)**: depende da US1 na prática (só faz sentido sair de uma sessão que existe) e toca
  `SiteHeader.tsx`, alterado em T027.
- **US3 (P2)**: depende da US1. O back-end (T038) é independente e pode ser adiantado.

### Dependências pontuais

- T006 depende de T005
- T010 e T011 dependem de T006 e T009
- T020 depende de T019; T021 depende de T018 e T020
- T023 depende de T020; T024 depende de T012 e T023
- T027 depende de T010 e T028
- T033 e T034 dependem de T027 e T032
- T045 depende de T037 (a US2 inteira precisa estar de pé)
- T047 depende de T045

### Parallel Opportunities

- **Phase 1**: T003 em paralelo com T001 e T002
- **Phase 2**: T008, T009 e T012 em paralelo
- **US1**: T013 a T017 em paralelo (arquivos distintos)
- **US2**: T029 e T030 em paralelo
- **US3**: T038, T039 e T040 em paralelo
- **Cruzada**: T038 (back-end da US3) em paralelo com toda a US2
- **Phase 6**: T047, T048, T049 e T050 em paralelo

---

## Parallel Example: User Story 1

```bash
# Testes de arquivos distintos, todos antes da implementação:
Task: "Mensagem uniforme em backend/tests/test_auth_api.py"
Task: "Entrada dos quatro papéis em backend/tests/test_auth_api.py"
Task: "Limite de tentativas em backend/tests/test_auth_throttle.py"
Task: "Validação do destino de retorno em frontend/tests/auth.test.tsx"
```

---

## Implementation Strategy

### MVP (US1 + US2)

O spec dá P1 às duas, e o Princípio I proíbe entregar entrada sem saída — seria o beco sem saída.
Além disso o avaliador precisa alternar entre as quatro contas do seed.

1. Phase 1: Setup
2. Phase 2: Foundational — **bloqueia tudo**
3. Phase 3: US1 — entrar, com o cabeçalho já identificando
4. Phase 4: US2 — sair
5. **PARAR E VALIDAR**: entrar como cliente1, navegar, sair, entrar como organizador
6. Demonstrável neste ponto

### Entrega incremental

1. Setup + Foundational → a sessão é descritível
2. + US1 → entrar funciona e o ícone aparece no cabeçalho
3. + US2 → sair funciona (**MVP**)
4. + US3 → sessão acompanha a navegação e expira sem quebrar
5. + Phase 6 → e2e, README e o fechamento das tarefas da 002

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- **Nenhuma migração nova** — o modelo de usuário e a tabela de sessões já existem
- **Nenhuma dependência nova** — `django.contrib.auth` já traz hash, comparação em tempo
  constante e recusa de conta inativa (R2)
- T027 e T045 são o desbloqueio de `002-site-header-navigation`; T046 fecha o registro lá
- O papel devolvido à interface escolhe **o que apresentar**, nunca concede acesso — toda
  autorização continua no servidor (FR-022, Princípio IV)
- Commitar por contexto, com mensagem descritiva (Princípio VI)
