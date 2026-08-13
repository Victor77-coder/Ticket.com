---
description: "Lista de tarefas — Painel do Organizador"
---

# Tasks: Painel do Organizador — Programar Filmes, Salas e Sessões

**Input**: documentos de design em `/specs/013-painel-do-organizador/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md` (R1–R11), `data-model.md`,
`contracts/programacao-api.md`, `contracts/casa-do-papel.md`, `quickstart.md`

**Tests**: incluídos — o `plan.md` §Technical Context nomeia as suítes por arquivo (pytest, Vitest,
Playwright) e três testes são a **prova de recorte** da feature (concorrência, negação por papel,
paridade do mapa de sala). Não são opcionais aqui.

**Zero migração**: nenhuma tarefa cria tabela, coluna ou constraint. `makemigrations --check`
continua limpo (T002, T066). Coluna nova é escopo escorregando (data-model.md).

## Format: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US5, conforme `spec.md`

---

## Phase 1: Setup

**Purpose**: linha base e os arquivos que ainda não existem, sem lógica dentro.

- [X] T001 Rodar a linha base e registrar que está verde antes de tocar em qualquer coisa: `pytest` em `backend/`, `npm test` em `frontend/` e `python manage.py makemigrations --check --dry-run` em `backend/`
- [X] T002 [P] Criar `backend/apps/screening/services/salas.py` com apenas o docstring que declara o dono único da geometria da sala (R1, FR-017) — sem implementação ainda
- [X] T003 [P] Criar `backend/apps/screening/services/programacao.py` com apenas o docstring que declara que o conflito `(sala, horário)` vem do `IntegrityError` da constraint, nunca de `exists()` (R4, FR-025)
- [X] T004 [P] Criar `backend/apps/catalog/services/programacao_filmes.py` com apenas o docstring que declara que a importação reusa `sync_movie`, sem segundo mapeamento (R2, FR-011a)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: papel, prefixo e fixtures. Nenhuma história pode começar sem isto.

**⚠️ CRÍTICO**: T005 e T006 bloqueiam todos os endpoints das fases seguintes.

- [X] T005 Implementar `IsOrganizer` em `backend/apps/accounts/permissions.py` com `message = "Apenas organizadores programam sessões."`, seguindo o padrão de `backend/apps/screening/permissions.py` (R7, FR-034) — `403` para papel errado, nunca `401`
- [X] T006 Criar o prefixo `programacao/` em `backend/apps/screening/urls.py` e `backend/apps/catalog/urls.py` (as duas listas já entram por `api/v1/` em `backend/config/urls.py`), com o comentário de que todo endpoint sob o prefixo exige `IsOrganizer` (R8, contracts/programacao-api.md §prefixo)
- [X] T007 [P] Acrescentar fixtures de organizador e de clientes de API autenticados por papel em `backend/tests/conftest.py`, reusando `make_user(role=...)`
- [X] T008 [P] Escrever `backend/tests/test_programacao_permissoes.py` cobrindo, para **cada** endpoint de `contracts/programacao-api.md`: anônimo → `401`, cliente → `403`, portaria → `403`, com a frase de `IsOrganizer` (FR-035, FR-036, SC-005). Falha até os endpoints existirem — é o alvo das fases seguintes
- [X] T009 [P] Declarar os tipos da programação (`FilmeDoPainel`, `ResultadoTmdb`, `SalaDoPainel`, `SessaoDaGrade`, com `pode_editar`/`pode_publicar`/`pode_cancelar`) em `frontend/lib/types.ts`
- [X] T010 Acrescentar as chamadas de programação em `frontend/lib/api.ts`, distinguindo `401` (conduzir à entrada) de `403` (renderizar recusa), conforme R11 — depende de T009

**Checkpoint**: papel definido, prefixo reservado, testes de autorização escritos e vermelhos.

---

## Phase 3: User Story 1 — O organizador pousa onde trabalha (P1) 🎯 MVP

**Goal**: o organizador entra e cai na área de programação, vê a grade (mesmo vazia), e **continua**
alcançando o catálogo público.

**Independent Test**: entrar com `organizador` → primeira tela é `/programacao`; abrir o menu da
conta → item "Programação"; abrir a home → **não** redireciona; entrar como cliente e abrir
`/programacao` → recusa por papel escrita em português, sem ir para a entrada.

### Testes da US1

- [X] T011 [P] [US1] Atualizar (não remover) os dois testes que hoje afirmam o contrário em `frontend/tests/auth.test.tsx`: o de `devolverParaCasa("organizer", …) === null` muda só de **nome**; o do menu da conta passa a incluir `["organizer", "Programação", "/programacao"]` na lista parametrizada, e o comentário cuja premissa caiu sai (FR-005, contracts/casa-do-papel.md §testes que mudam)
- [X] T012 [P] [US1] Acrescentar em `frontend/tests/auth.test.tsx` os cinco testes novos exigidos por `contracts/casa-do-papel.md` §testes novos — com destaque para `destinoAposEntrada("customer", "/") === "/"`, que é a regressão mais provável do campo `pousa`
- [X] T013 [P] [US1] Escrever `frontend/tests/programacao.test.tsx` com os estados da área: grade vazia, erro do servidor e recusa por papel (`403` renderizado, não redirecionado) — FR-007, R11
- [X] T014 [P] [US1] Escrever `backend/tests/test_programacao_sessoes.py::test_grade_lista_os_tres_estados`, provando que `GET /api/v1/programacao/sessoes/` devolve rascunho, publicada e cancelada com `estado`, `estado_rotulo`, `ocupacao` e `a_venda` (FR-029, contrato §GET sessoes)

### Implementação da US1

- [X] T015 [US1] Acrescentar `grade_do_organizador()` em `backend/apps/screening/selectors.py` com `select_related("movie", "room")` e a ocupação anotada por `Count` filtrado pelo `Q` de `Reservation.OCUPANDO` — uma consulta, nunca `seats_taken` por linha (R6)
- [X] T016 [US1] Acrescentar os serializers de grade em `backend/apps/screening/serializers.py` (`SessaoDaGradeSerializer`, com filme e sala aninhados, `pode_editar`/`pode_publicar`/`pode_cancelar` derivados) e repetir no topo o aviso de fronteira: estes campos **não** vazam para os serializers públicos (data-model.md §fronteira)
- [X] T017 [US1] Implementar `GradeView` (`GET`) em `backend/apps/screening/views.py` sob `IsOrganizer` e registrá-la como `programacao/sessoes/` em `backend/apps/screening/urls.py`
- [X] T018 [US1] Dividir `telaUnica` em `pousa` + `telaUnica` em `frontend/lib/papeis.ts`: registrar `organizer: { href: "/programacao", rotulo: "Programação", pousa: true, telaUnica: false }`, fazer `destinoAposEntrada` consultar `pousa`, manter `temTelaUnica` e `devolverParaCasa` lendo `telaUnica`, e reescrever o docstring que hoje diz que os três fatos andam juntos (R10, FR-001, FR-002)
- [X] T019 [US1] Conferir que `frontend/middleware.ts` **não** precisa de alteração — nenhuma lista de páginas permitidas, nenhum bloqueio de `/programacao` por papel (contracts/casa-do-papel.md §proibições). Se alguma linha for necessária, ela contraria o contrato
- [X] T020 [US1] Criar `frontend/app/programacao/page.tsx` como servidor: sem cookie ou `401` → `redirect("/entrar?next=/programacao")`; `403` → painel de recusa com frase própria e link de volta ao catálogo (R11, FR-008)
- [X] T021 [US1] ~~Criar `frontend/app/api/programacao/sessoes/route.ts`~~ — **adiado para a US2/US5, onde ele é consumido**. A grade da US1 é lida pelo componente de servidor, que fala com o Django direto; um proxy criado aqui ficaria sem chamador. Os proxies nascem em T036, T046, T056 e T065, junto das ações do navegador que os usam
- [X] T022 [US1] Criar `frontend/components/programacao/Grade.tsx` agrupando por dia e distinguindo os três estados por **rótulo + forma**, não só por cor (FR-029), e `frontend/components/programacao/programacao.module.css` usando exclusivamente tokens da 006/011 (FR-039)
- [X] T023 [US1] Criar `frontend/components/programacao/EstadoVazio.tsx` — grade vazia diz que nenhuma sessão foi programada e aponta o caminho para programar a primeira (FR-007, US5 cenário 11)

**Checkpoint**: o organizador pousa, vê a área com estados de sucesso, erro e vazio, e o cliente que
tentar entrar recebe recusa por papel. A grade ainda é só leitura.

---

## Phase 4: User Story 2 — Publicar sessão de filme do catálogo local (P1) 🎯 MVP

**Goal**: a grade ganha origem diferente do `seed_demo` — criar e publicar uma sessão, e vê-la no
caminho de compra do cliente.

**Independent Test**: com o catálogo sincronizado, criar sessão publicada para filme existente e
comprá-la até o ingresso pelo fluxo do cliente, sem rodar comando nenhum.

### Testes da US2

- [X] T024 [P] [US2] Escrever `backend/tests/test_programacao_concorrencia.py`: duas criações simultâneas da mesma `(sala, horário)` — exatamente uma grava, a outra recebe `409` com a frase que nomeia sala e horário (SC-004, R4), no mesmo formato dos testes de concorrência das 007/008/010
- [X] T025 [P] [US2] Completar `backend/tests/test_programacao_sessoes.py` com criação em rascunho e publicada, preço ausente/zero/negativo → `400`, `publicar: true` com horário passado → `400`, `publicar: true` em sala sem lugares → `400`, e rascunho com horário passado → **aceito** (contrato §POST sessoes)
- [X] T026 [P] [US2] Escrever `backend/tests/test_programacao_filmes.py::test_catalogo_local_lista_com_contagem_de_sessoes`, provando que `GET /api/v1/programacao/filmes/` agrega `sessoes` (não canceladas) sem N+1
- [X] T027 [P] [US2] Escrever `frontend/tests/e2e/programacao.spec.ts`: organizador entra, publica sessão de filme local, e um cliente encontra o horário na página do filme e chega ao mapa de assentos (SC-001, SC-002)

### Implementação da US2

- [X] T028 [US2] Implementar `criar_sessao(...)` em `backend/apps/screening/services/programacao.py`: `transaction.atomic()` **interno**, `Screening.objects.create(...)`, e `except IntegrityError` reconhecendo `uma_sessao_por_sala_e_horario` pelo **nome** para levantar `ConflitoDeHorario(sala, inicio)` (R4). Nenhum `exists()` prévio
- [X] T029 [US2] Acrescentar em `backend/apps/screening/serializers.py` o serializer de escrita de sessão (filme, sala, início, preço, `publicar`) com as recusas de campo do contrato — preço > 0, horário futuro só quando `publicar`, sala com ≥ 1 lugar quando `publicar` (FR-026, FR-027, FR-028)
- [X] T030 [US2] Acrescentar em `backend/apps/screening/serializers.py` e `selectors.py` a lista de salas para escolha (`nome`, `capacidade`, `lugares`, `acessiveis`, `ocupacao_viva`, `pode_trocar_capacidade`), com `ocupacao_viva` agregada por `Reservation.OCUPANDO` (contrato §GET salas, FR-021)
- [X] T031 [US2] Acrescentar em `backend/apps/catalog/serializers.py` o serializer do catálogo local para o painel (`id`, `tmdb_id`, `titulo`, `ano`, `poster_url`, `duracao_min`, `sessoes`) — sem tocar nos serializers públicos
- [X] T032 [US2] Implementar `CatalogoDoPainelView` (`GET programacao/filmes/`) em `backend/apps/catalog/views.py` e `SalasView` (`GET programacao/salas/`) em `backend/apps/screening/views.py`, ambas sob `IsOrganizer`, e registrá-las nas urls dos respectivos apps
- [X] T033 [US2] Implementar `SessoesView` (`POST`) em `backend/apps/screening/views.py`, mapeando `ConflitoDeHorario` para `409` com a frase do contrato e reusando a `GradeView` já registrada em `programacao/sessoes/`
- [X] T034 [US2] Criar `frontend/app/programacao/sessoes/nova/page.tsx` — escolher filme do catálogo local, sala, horário e preço, com "salvar rascunho" e "publicar" como duas ações explícitas (FR-022)
- [X] T035 [US2] Criar `frontend/components/programacao/FormularioDeSessao.tsx` exibindo as recusas do servidor campo a campo, e o `409` de conflito como frase que nomeia sala e horário
- [X] T036 [US2] Criar `frontend/app/api/programacao/sessoes/route.ts` repassando status e corpo sem alteração. **Os proxies de `filmes/` e `salas/` não foram criados**: as duas listas são lidas pelo componente de servidor, e um proxy sem chamador é código morto — o de `filmes/busca/` nasce na US3, onde o navegador digita

**Checkpoint**: o painel entrega valor inteiro em versão mínima — programar e vender sem terminal.

---

## Phase 5: User Story 3 — Trazer um filme novo do TMDb (P2)

**Goal**: buscar no TMDb pelo back-end, escolher um resultado e persistir localmente pelo mesmo
mapeamento da sincronização.

**Independent Test**: buscar título fora do catálogo, escolher, conferir que o filme passou a existir
com pôster, Sobre e Trailers, e criar uma sessão para ele.

### Testes da US3

- [X] T037 [P] [US3] Completar `backend/tests/test_programacao_filmes.py` com: busca devolvendo `ja_no_catalogo` resolvido em **uma** consulta `__in`, `q` vazio → `200` com `count: 0`, TMDb fora do ar/timeout → `502` com a frase do `TMDBError`, importação de filme novo → `201`, importação de filme existente → `200` **sem duplicar** (FR-012), e `is_trending`/`is_upcoming` não rebaixados na reimportação (R2, FR-046)
- [X] T038 [P] [US3] Acrescentar em `backend/tests/test_programacao_filmes.py` a prova de FR-010: nenhuma resposta da busca ou da importação contém `TMDB_API_KEY`, URL com chave ou cabeçalho da chamada externa (SC-008)
- [X] T039 [P] [US3] Acrescentar em `backend/tests/test_filme_detalhe.py` (ou arquivo irmão) a prova de FR-011a: um filme importado pelo painel expõe gêneros, classificação e trailers idênticos aos de um filme vindo do `sync_tmdb` — Sobre e Trailers da 012 não ficam vazias

### Implementação da US3

- [X] T040 [US3] Acrescentar `search_movies(query, page=1)` em `backend/apps/catalog/services/tmdb_client.py` chamando `/search/movie` com `include_adult=False` pelo `_get` existente — sem tocar em `_get`, herdando timeout, idioma e `TMDBError` em pt-BR (R3)
- [X] T041 [US3] Implementar `importar_filme(tmdb_id)` em `backend/apps/catalog/services/programacao_filmes.py`: `movie_detail(tmdb_id)` → `sync_movie(detalhe, is_trending=False, is_upcoming=False)`, devolvendo também se o filme já existia (para o `200` vs `201`) — nenhum mapeamento paralelo (R2, FR-011a)
- [X] T042 [US3] Acrescentar em `backend/apps/catalog/serializers.py` o serializer do resultado de busca (`tmdb_id`, `titulo`, `ano`, `poster_url`, `ja_no_catalogo`) e o de entrada da importação (`tmdb_id`)
- [X] T043 [US3] Implementar `BuscaTmdbView` (`GET programacao/filmes/busca/`) e o `POST` de `programacao/filmes/` em `backend/apps/catalog/views.py` sob `IsOrganizer`, traduzindo `TMDBError` para `502` com a frase que ele já escreve — sem redigir uma segunda versão da mensagem
- [X] T044 [US3] Criar `frontend/components/programacao/BuscaDeFilme.tsx` com os três estados: resultados (marcando "já no catálogo"), nada encontrado para o termo, e TMDb indisponível com a frase do servidor e o convite a seguir com o catálogo local (FR-014, US3 cenários 6 e 7)
- [X] T045 [US3] Ligar a busca ao formulário de sessão em `frontend/app/programacao/sessoes/nova/page.tsx` — escolher um resultado importa o filme e segue para a sessão com ele já selecionado
- [X] T046 [US3] Criar `frontend/app/api/programacao/filmes/busca/route.ts` repassando status e corpo sem alteração, inclusive o `502`

**Checkpoint**: o catálogo deixa de depender de rodar `sync_tmdb` na mão, e o TMDb fora do ar degrada
só a busca.

---

## Phase 6: User Story 4 — Criar sala e ganhar o mapa de lugares (P2)

**Goal**: sala nova com lugares gerados pela **mesma** regra do cenário de demonstração.

**Independent Test**: criar sala de capacidade conhecida, abrir uma sessão nela pelo fluxo do cliente
e conferir fileiras, última fileira incompleta e acessibilidade na última fileira.

### Testes da US4

- [X] T047 [P] [US4] Escrever `backend/tests/test_sala_paridade_seed.py`: uma sala criada pelo serviço e outra pelo caminho do seed com a mesma capacidade produzem fileira, número e tipo idênticos, lugar a lugar (SC-006, FR-017)
- [X] T048 [P] [US4] Escrever `backend/tests/test_programacao_salas.py` com: capacidade ausente/não numérica/≤ 0 → `400`; acima do teto → `400` com o teto **calculado** de `26 × SEATS_PER_ROW`; capacidade exatamente no teto → aceita; capacidade que não fecha a fileira deixa a última incompleta; sala menor que a cota → todos os lugares da última fileira acessíveis, sem falhar
- [X] T049 [P] [US4] Acrescentar em `backend/tests/test_programacao_salas.py` a troca de capacidade: sem ocupação viva → lugares refeitos (`200`); com reserva paga ou reserva viva não vencida → `409` e **nenhum** lugar apagado; com reserva vencida e não paga → permitido (FR-019, FR-020, FR-021)

### Implementação da US4

- [X] T050 [US4] Implementar em `backend/apps/screening/services/salas.py` as funções `posicoes_da_sala(capacity, por_fileira=None)`, `lugares_acessiveis(posicoes, cota=None)` e `gerar_assentos(room)`, movendo a regra que hoje vive em `_seed_seats`/`_posicoes_da_sala`. `posicoes_da_sala` continua **truncando** no teto — a recusa é validação de entrada e mora no serializer (R1, nota da fronteira)
- [X] T051 [US4] Fazer `backend/apps/catalog/management/commands/seed_demo.py` chamar `gerar_assentos`, deixando `_seed_seats` sem regra própria — o comando continua dono do reset, não da geometria (FR-017)
- [X] T052 [US4] Implementar `alterar_capacidade(room, nova)` em `backend/apps/screening/services/salas.py`: dentro de uma transação, ler ocupação viva de todas as sessões da sala por `selectors.ocupacoes_vivas()` filtrado por `screening__room`, recusar com exceção que carrega a contagem, e só então apagar e recriar os `Seat` (R5)
- [X] T053 [US4] Acrescentar em `backend/apps/screening/serializers.py` a validação de capacidade (ausente, não numérica, ≤ 0, acima do teto) com as frases do contrato e o teto derivado de `settings.SEATS_PER_ROW`, nunca literal na string (FR-018)
- [X] T054 [US4] Implementar `POST programacao/salas/` e `PATCH programacao/salas/<id>/` em `backend/apps/screening/views.py` sob `IsOrganizer`, mapeando a recusa de ocupação para `409` com a frase que diz quantos lugares estão ocupados e o que fazer
- [X] T055 [US4] Criar `frontend/app/programacao/salas/page.tsx` com a lista (nome, capacidade, lugares, acessíveis), o estado vazio que convida a criar a primeira sala, e o controle de capacidade **desabilitado com explicação** quando `pode_trocar_capacidade` é falso — nunca escondido (FR-037)
- [X] T056 [US4] Criar `frontend/components/programacao/FormularioDeSala.tsx` e `frontend/app/api/programacao/salas/[id]/route.ts` repassando status e corpo sem alteração

**Checkpoint**: o organizador deixa de estar preso às duas salas do seed, e a regra da geometria tem
dono único.

---

## Phase 7: User Story 5 — Conduzir a grade: corrigir, publicar e cancelar (P3)

**Goal**: editar rascunho, publicar e cancelar — com a fronteira da correção na publicação.

**Independent Test**: criar rascunho errado, corrigir, confirmar que nenhum cliente o viu, publicar,
cancelar, e confirmar que um ingresso já emitido daquela sessão continua na lista do cliente.

### Testes da US5

- [ ] T057 [P] [US5] Acrescentar em `backend/tests/test_programacao_sessoes.py` as transições: editar rascunho mantém rascunho; editar publicada ou cancelada → `409` com a frase que manda cancelar e programar outra; mover rascunho para `(sala, horário)` ocupado → mesmo `409` da criação; publicar rascunho futuro → `200`; publicar com horário passado ou sala sem lugares → `400`; publicar sessão já publicada → `409`; cancelada é terminal (FR-023, FR-024, FR-030)
- [ ] T058 [P] [US5] Acrescentar em `backend/tests/test_programacao_sessoes.py` a prova de FR-031/SC-009: cancelar sessão com ingresso emitido muda **uma** coluna — `status` — e não estorna `Payment`, não apaga `Ticket` nem `ReservedSeat`, não mexe em `used_at`; o ingresso continua em "Meus ingressos" e o desfecho da portaria não muda
- [ ] T059 [P] [US5] Acrescentar em `backend/tests/test_programacao_sessoes.py` a prova de FR-032: sessão em rascunho e sessão cancelada não aparecem em nenhuma superfície de compra — `get_sellable_screening` e `sellable()` continuam as excluindo, sem filtro novo
- [ ] T060 [P] [US5] Acrescentar em `frontend/tests/programacao.test.tsx` a distinção dos três estados por rótulo + forma, e a checagem de contraste/acromatopsia no mesmo formato de `frontend/tests/e2e/acromatopsia.mjs` (FR-029)

### Implementação da US5

- [ ] T061 [US5] Implementar `editar_rascunho`, `publicar` e `cancelar` em `backend/apps/screening/services/programacao.py`, com as pré-condições da tabela de `data-model.md` §ciclo de vida e a mesma captura de `IntegrityError` na edição (R4)
- [ ] T062 [US5] Implementar `PATCH programacao/sessoes/<id>/`, `POST programacao/sessoes/<id>/publicar/` e `POST programacao/sessoes/<id>/cancelar/` em `backend/apps/screening/views.py`, como **ações** e não `PATCH status` (R8), e registrá-las em `backend/apps/screening/urls.py`
- [ ] T063 [US5] Criar `frontend/app/programacao/sessoes/[id]/page.tsx` para editar rascunho, reusando `FormularioDeSessao.tsx` e recusando a edição de publicada/cancelada com a frase do servidor
- [ ] T064 [US5] Acrescentar as ações de publicar e cancelar em `frontend/components/programacao/Grade.tsx`, desabilitadas com explicação quando `pode_publicar`/`pode_cancelar` são falsos, e com confirmação antes de cancelar
- [ ] T065 [US5] Criar `frontend/app/api/programacao/sessoes/[id]/route.ts`, `.../publicar/route.ts` e `.../cancelar/route.ts` repassando status e corpo sem alteração

**Checkpoint**: a grade tem resposta para "programei errado", e cancelar para de vender sem tocar em
histórico de venda.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T066 Acrescentar `--force` em `backend/apps/catalog/management/commands/seed_demo.py`: sem a flag, se `Screening.objects.exists()`, recusar e escrever o que seria apagado (sessões, reservas, ingressos) e como prosseguir; com a flag, comportamento idêntico ao de hoje. `_reset_demo_state` **não muda por dentro** (R9, FR-041 a FR-044)
- [ ] T067 Atualizar `backend/tests/test_seed_demo.py`: base vazia roda direto sem passo extra; com grade existente recusa e nada é apagado; com `--force` apaga e recria como sempre (FR-044)
- [ ] T068 [P] Acrescentar em `backend/tests/test_selectors.py` (ou arquivo irmão) a proibição 1 do contrato: nenhum serializer público ganhou `status`, `capacity`, contagem de vendidos ou `tmdb_id` — highlights, home, busca, detalhe do filme, mapa e portaria
- [ ] T069 [P] Atualizar o `README.md` da raiz com a seção do painel, o pouso do organizador em `/programacao` e o aviso de que recriar o cenário passou a exigir `--force` (FR-040)
- [ ] T070 [P] Conferir `frontend/tests/tokens.test.ts` contra `frontend/components/programacao/programacao.module.css` — nenhum valor de cor, espaçamento, tipografia, raio ou duração fora dos tokens; espaço novo nasce token (FR-039)
- [ ] T071 Rodar `python manage.py makemigrations --check --dry-run` em `backend/` e confirmar que nada mudou de esquema (data-model.md, proibição 6 do contrato)
- [ ] T072 Rodar a suíte inteira — `pytest` em `backend/`, `npm test` e `npm run test:e2e` em `frontend/` — conferindo em especial os pontos de não-regressão listados em `quickstart.md` §o que NÃO pode ter mudado (FR-038)
- [ ] T073 Percorrer `specs/013-painel-do-organizador/quickstart.md` inteiro, incluindo as três provas de recorte e o caminho com `TMDB_API_KEY` inválida (SC-001, SC-003, SC-007)
- [ ] T074 Revisão de código dirigida às cinco proibições do contrato: nenhum `exists()` como garantia de unicidade, nenhuma segunda geometria de sala, nenhum segundo mapeamento de TMDb, nenhuma chave no corpo, nenhum endpoint de programação fora do prefixo (contracts/programacao-api.md §proibições)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências
- **Foundational (Fase 2)**: depende da Fase 1 — **bloqueia todas as histórias**
- **US1 (Fase 3)**: depende da Fase 2. É o MVP com US2
- **US2 (Fase 4)**: depende da Fase 2. Usa a `GradeView` da US1 para exibir o que criou, mas a API de criação é testável sozinha
- **US3 (Fase 5)**: depende da Fase 2. Independente da US2 no back-end; o front costura as duas em `sessoes/nova`
- **US4 (Fase 6)**: depende da Fase 2. Independente das demais
- **US5 (Fase 7)**: depende da US2 (precisa de sessão criada para conduzir)
- **Polish (Fase 8)**: T066/T067 dependem da US4 (o seed passa a consumir `salas.py`); o resto depende de tudo

### Ordem dentro de cada história

Testes → serviço → serializer → view/urls → tela → proxy.

### Parallel Opportunities

- Fase 1: T002, T003, T004 juntos
- Fase 2: T007, T008, T009 juntos (T010 depois de T009)
- US1: T011, T012, T013, T014 juntos
- US2: T024, T025, T026, T027 juntos
- US3: T037, T038, T039 juntos
- US4: T047, T048, T049 juntos
- US5: T057, T058, T059, T060 juntos
- Depois da Fase 2, US1+US2 (front e back), US3 e US4 podem correr em trilhas separadas

---

## Parallel Example: User Story 2

```bash
Task: "Escrever backend/tests/test_programacao_concorrencia.py"
Task: "Completar backend/tests/test_programacao_sessoes.py com as recusas de campo"
Task: "Escrever o teste do catálogo local em backend/tests/test_programacao_filmes.py"
Task: "Escrever frontend/tests/e2e/programacao.spec.ts"
```

---

## Implementation Strategy

### MVP (US1 + US2)

1. Fases 1 e 2
2. US1 — o organizador pousa e vê a área
3. US2 — programar e publicar; o cliente compra
4. **PARAR e VALIDAR**: `quickstart.md` §caminho principal em menos de 2 minutos, sem terminal

US1 sozinha entrega uma área que só lê; US2 sozinha entrega uma API que ninguém alcança pela tela.
As duas são P1 porque o MVP são as duas.

### Entrega incremental

1. MVP (US1 + US2) → demonstrável
2. + US3 → o catálogo cresce sem `sync_tmdb` na mão
3. + US4 → salas novas
4. + US5 → grade conduzida
5. + Fase 8 → seed protegido, README, provas de recorte

---

## Notes

- **Zero migração** é invariante, não meta: se aparecer necessidade de coluna, o escopo escorregou
- Os três testes que separam esta feature de ter reaberto o que estava fechado: T024 (concorrência),
  T008 (negação por papel), T047 (paridade do mapa de sala)
- `devolverParaCasa("organizer", …)` devolve `null` — se um dia consultar `pousa`, o organizador
  perde a home e o sintoma aparece longe da causa
- Commits incrementais por contexto, na `main`, como nas features 003–012
