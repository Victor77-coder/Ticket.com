---
description: "Task list for feature implementation"
---

# Tasks: Validação de Ingressos na Portaria

**Input**: Design documents from `/specs/010-gate-validation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/gate-api.md](./contracts/gate-api.md),
[quickstart.md](./quickstart.md)

**Tests**: **Sim, e um deles é a única defesa que a feature tem.** Nas três features anteriores a
garantia de unicidade era um índice, e o banco recusava a segunda escrita — o teste via a recusa.
**Aqui não há constraint para recusar.** Se a marcação virar leitura seguida de escrita, o banco
aceita as duas em silêncio e duas pessoas entram com o mesmo ingresso. O teste de concorrência é o
que está entre o projeto e uma portaria furada, e por isso é escrito **antes** do serviço.

**Organization**: Sete user stories, seis delas P1 — os quatro desfechos exigidos pelo Princípio III
não são opcionais. A fase Foundational entrega o **pipeline inteiro** (os quatro desfechos já
respondem na API); as fases de história entregam o tratamento na tela e as provas de cada desfecho.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (sessão da porta), US2 (válido pela câmera), US3 (digitação), US4 (já utilizado),
  US5 (inválido), US6 (sessão errada), US7 (papéis)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Domínio**: `backend/apps/screening/` — o uso é uma coluna de `Ticket`
- **A garantia**: `backend/apps/screening/services/portaria.py` — **não** uma migração
- **A assinatura**: `backend/apps/screening/services/ingressos.py` — **INTOCADO**, puro, sem banco
- **As consultas**: `backend/apps/screening/selectors.py` — e a de sessões **não usa `sellable()`**
- **Front**: `frontend/app/portaria/` e `frontend/components/gate/`

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte e declarar a dependência nova

- [X] T001 Rodar `docker compose exec backend pytest`, `docker compose exec frontend npm run test` e, de `frontend/`, `npx playwright test --workers=2`, conferindo a linha de base: **328** back-end, **159** front-end em 12 arquivos, **35** e2e (mais 1 skip pré-existente dependente do catálogo)
- [X] T002 Acrescentar `jsQR` às dependências em `frontend/package.json`, com **versão fixada** — JavaScript puro, sem dependências transitivas (R6). Reconstruir o container do front: `docker compose up -d --build frontend`
- [X] T003 Confirmar que **nenhuma variável de ambiente nova** é necessária e que `.env.example` não muda — a assinatura reusa a `TICKET_SIGNING_KEY` que a 008 já declarou

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: A coluna de uso, o pipeline dos quatro desfechos, e — antes de tudo — a prova de que a
marcação é única.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar. Ao fim dela os quatro
desfechos já respondem na API; as histórias entregam a tela e as provas de cada um.

**⚠️ T007 VEM ANTES DE T010–T012, e não é preferência de método.** É a única feature da série em que
o teste de concorrência não tem uma constraint atrás dele. Escrever o serviço primeiro produz um
teste escrito para o que o serviço faz — e o serviço errado (o `if` natural) passa nesse teste.

- [X] T004 Acrescentar `used_at = models.DateTimeField(null=True, blank=True, default=None)` a `Ticket` em `backend/apps/screening/models.py`, substituindo o comentário da 008 que dizia "NENHUM campo `used`/`used_at` aqui" por nota registrando que o campo chegou **com** a garantia — e que a garantia **não é uma constraint**, com o motivo: o invariante é de transição, não de coexistência, e nenhum índice expressa "esta coluna só sai de nulo uma vez" (R1, data-model.md)
- [X] T005 Gerar `backend/apps/screening/migrations/0005_ticket_used_at.py` com `makemigrations` e **conferir lendo o arquivo** que ela acrescenta só a coluna — é a **primeira migração da série sem constraint junto**, e alguém vai procurar o índice que as três anteriores tinham
- [X] T006 Aplicar a migração e verificar no banco que a coluna é nulável e que **todos os ingressos já emitidos estão com `used_at` nulo** — nenhum ingresso antigo pode nascer marcado (quickstart.md, pré-requisito 2)
- [X] T007 Escrever `backend/tests/test_gate_concurrency.py` com **`transaction=True`** e threads reais, provando que N validações simultâneas do mesmo ingresso produzem **exatamente um** `valido` e N−1 `ja_utilizado` (FR-036, SC-007) — deve falhar enquanto o serviço não existir, e precisa **falhar também** quando a escrita condicional for trocada pelo `if` natural
- [X] T008 [P] Escrever `backend/tests/test_gate_signature.py` cobrindo, com `django_assert_num_queries(0)` em volta do **serviço**: código adulterado, código inventado, código assinado com outra chave e código assinado com a `DJANGO_SECRET_KEY` — todos **inválido**, sem nenhuma consulta ao registro de ingressos (FR-027, SC-008, R12)
- [X] T009 [P] Acrescentar a `backend/tests/conftest.py` uma fixture que produz o **código assinado** de um ingresso emitido, para que os testes da portaria não reimplementem a assinatura
- [X] T010 Escrever `backend/apps/screening/services/portaria.py` com o pipeline na ordem de R4: assinatura → ingresso existe → `s` do payload bate com a sessão do banco → sessão da porta → marcação. Registrar no docstring por que o módulo é separado de `services/ingressos.py`: aquele é **puro** por decisão da 008, e a ausência de banco é o que torna `num_queries == 0` estrutural
- [X] T011 Implementar a marcação em `services/portaria.py` como **um** `UPDATE` condicional (`.filter(pk=..., used_at__isnull=True).update(used_at=Now())`), derivando o desfecho do **número de linhas afetadas** — 1 é válido, 0 é já utilizado (FR-035, R1)
- [X] T012 Escrever ao lado da marcação, em `services/portaria.py`, o comentário que registra a armadilha por extenso: o `if used_at is not None` antes do `save()` passa em todo teste de uma thread, **lê como a regra da spec**, e o banco **não reclama** porque não há constraint — o desfecho vem do `rowcount`, nunca de um `if` sobre o objeto lido (R2, R3)
- [X] T013 Garantir em `services/portaria.py` que **sessão errada e inválido não escrevem nada** (FR-031, FR-032), e que a leitura do ingresso serve só para conferir a sessão e montar a resposta — o `used_at` daquela leitura não decide nada
- [X] T014 [P] Escrever `IsGate` em `backend/apps/screening/permissions.py`, subclasse de `BasePermission` com a mensagem "Apenas a portaria valida ingressos." — quarta permissão da série, pelo mesmo motivo das outras três: a frase descreve a tela em que a pessoa está (R12 da 009)

**Checkpoint**: a coluna existe, o pipeline responde os quatro desfechos, e T007 passa. Nada visível.

---

## Phase 3: US1 — Abrir o posto e dizer qual sessão está recebendo (P1)

**Goal**: O operador escolhe a sessão da porta antes de qualquer leitura, e ela fica visível.

**Independent Test**: Autenticado como `portaria`, abrir a tela e conferir que ela pede a escolha da
sessão antes de qualquer leitura, e que a escolhida fica visível.

**⚠️ T015–T016 guardam a armadilha herdada.** É a segunda aparição de `sellable()` como erro natural
— a 009 registrou a primeira. Os testes vêm antes do selector.

- [X] T015 [P] [US1] Cobrir em `backend/tests/test_gate_api.py` que a lista de sessões da portaria **inclui sessões que já começaram** (US1-1) — deve **falhar** enquanto o selector não existir, e falha de novo se alguém usar `sellable()`
- [X] T016 [P] [US1] Cobrir em `backend/tests/test_gate_api.py` que sessões **canceladas** ficam fora da lista, e que a lista traz filme, horário e sala
- [X] T017 [US1] Escrever `selectors.sessoes_da_portaria()` em `backend/apps/screening/selectors.py`, devolvendo as sessões **publicadas do dia** ordenadas por horário, com `select_related("movie", "room")`, e docstring registrando que **não pode usar `sellable()`**: a porta precisa exatamente da sessão em andamento, que aquele filtro exclui. Escrever a regra que emerge das duas aparições — **`sellable()` responde "dá para comprar?", e nenhuma outra pergunta** (R11)
- [X] T018 [US1] Escrever `GateScreeningsView` em `backend/apps/screening/views.py` para `GET /api/v1/portaria/sessoes/`, com `handle_exception` traduzindo `NotAuthenticated` em `401` com "Entre para usar a portaria." (contracts/gate-api.md)
- [X] T019 [US1] Registrar `portaria/sessoes/` em `backend/apps/screening/urls.py`
- [X] T020 [P] [US1] Cobrir em `backend/tests/test_gate_api.py` que "hoje não tem sessão" devolve `200` com lista vazia — **não** `404`: é um estado da portaria, não a ausência de um recurso
- [X] T021 [P] [US1] Acrescentar os tipos `SessaoDaPorta` e `Desfecho` em `frontend/lib/types.ts`
- [X] T022 [US1] Acrescentar `fetchSessoesDaPortaria` em `frontend/lib/api.ts`, seguindo o padrão de `fetchMeusIngressos`
- [X] T023 [US1] Escrever `frontend/app/portaria/page.tsx` como Server Component com `dynamic = "force-dynamic"`, conduzindo visitante a `/entrar?next=/portaria` e tratando `403` com explicação **sem** redirecionar (FR-041)
- [X] T024 [US1] Escrever o estado "nenhuma sessão escolhida" em `frontend/app/portaria/PortariaCliente.tsx`, com explicação em português e a lista de sessões do dia (FR-003)
- [X] T025 [US1] Guardar a sessão escolhida no armazenamento local do navegador e reidratá-la ao montar, com comentário registrando por que é **por posto e não por conta**: dois operadores podem usar a mesma conta do seed em portas diferentes (FR-006, R9)
- [X] T026 [US1] Manter a sessão escolhida visível durante todo o uso da tela e oferecer a troca de porta sem sair dela (FR-004, FR-005)
- [X] T027 [US1] Escrever o estado "nenhuma sessão hoje" em `PortariaCliente.tsx`, com frase própria — nunca lista vazia sem contexto (FR-007)
- [X] T028 [US1] Escrever `frontend/app/portaria/portaria.module.css` usando exclusivamente tokens da 006 (FR-049)
- [X] T029 [P] [US1] Cobrir em `frontend/tests/portaria.test.tsx` os três estados iniciais: sem sessão escolhida, com sessão escolhida, e sem sessões no dia

**Checkpoint**: o posto abre e sabe qual sessão está recebendo.

---

## Phase 4: US2 — Ler o QR e liberar a entrada (P1)

**Goal**: O código é lido pela câmera e a tela diz **válido**, com o lugar.

**Independent Test**: Com a sessão escolhida e um ingresso daquela sessão, apontar a câmera para o QR
e conferir o desfecho **válido** com o lugar exibido.

- [X] T030 [P] [US2] Cobrir em `backend/tests/test_gate_api.py` que a primeira validação de um ingresso da sessão da porta devolve `situacao: "valido"` com o **lugar** (FR-020) e `200` (R5)
- [X] T031 [P] [US2] Cobrir em `backend/tests/test_gate_api.py` que `codigo` vazio devolve `400` com frase própria, **distinta** de `invalido` (FR-014), e que `sessao` ausente ou inexistente devolve `400` com a frase da escolha de sessão
- [X] T032 [P] [US2] Cobrir em `backend/tests/test_gate_api.py` que espaços e quebras de linha nas pontas do código são tolerados (FR-013)
- [X] T033 [US2] Escrever os serializers de entrada e saída da validação em `backend/apps/screening/serializers.py`, **sem tocar** `TicketSerializer` nem `MeuIngressoSerializer` (FR-048, R14)
- [X] T034 [US2] Escrever `GateValidateView` em `backend/apps/screening/views.py` para `POST /api/v1/portaria/validar/`, respondendo `200` nos **quatro** desfechos com o campo `situacao` fixo, e registrando em comentário por que nenhum deles é `4xx`: a portaria perguntou e recebeu resposta; "não" é uma resposta (R5)
- [X] T035 [US2] Registrar `portaria/validar/` em `backend/apps/screening/urls.py`
- [X] T036 [US2] Acrescentar `postValidacao` em `frontend/lib/api.ts` e escrever `frontend/app/api/validar/route.ts` como proxy, no padrão de `app/api/pagar/route.ts`
- [X] T037 [US2] Escrever `frontend/components/gate/Desfecho.tsx`, escolhendo símbolo, título e destaque pelo campo `situacao` — **nunca** interpretando a frase, que é apresentação e muda numa revisão de redação (R10)
- [X] T038 [US2] Escrever `frontend/components/gate/gate.module.css` com o título do desfecho no maior degrau tipográfico da tela (FR-019) e a cor como **quarto** sinal, depois de símbolo, título e disposição (FR-017, R13)
- [X] T039 [US2] Escrever `frontend/components/gate/LeitorDeCodigo.tsx` com a leitura por câmera: `getUserMedia`, quadros para um `<canvas>` e `jsQR` sobre os pixels
- [X] T040 [US2] Implementar em `LeitorDeCodigo.tsx` as três regras de R8: não disparar validação enquanto outra está em andamento; ignorar o **mesmo** conteúdo decodificado por alguns segundos; e não apagar o desfecho sozinho. Registrar em comentário que idempotência no servidor **não** resolve isto — é defeito de interface causado por característica do hardware (FR-015, FR-026)
- [X] T041 [US2] Anunciar o desfecho a tecnologias assistivas em `Desfecho.tsx` (FR-025)
- [X] T042 [P] [US2] Cobrir em `frontend/tests/desfecho.test.tsx` que os quatro desfechos têm **símbolo e título próprios** e são distinguíveis sem depender de cor (FR-017)

**Checkpoint**: a portaria valida e libera a entrada.

---

## Phase 5: US3 — Digitar o código quando a câmera não serve (P1)

**Goal**: A digitação manual está sempre visível e produz o mesmo desfecho.

**Independent Test**: Sem autorizar a câmera, colar o código em texto de um ingresso e conferir que o
desfecho é o mesmo que a câmera produziria.

- [X] T043 [US3] Escrever o campo de digitação em `PortariaCliente.tsx`, **sempre visível**, ao lado da câmera — não um caminho que só aparece depois de uma falha (FR-010). É exigência literal da constitution: "sempre disponível"
- [X] T044 [US3] Tratar em `LeitorDeCodigo.tsx` os três casos de câmera indisponível — negada, inexistente e revogada depois de autorizada —, com frase em português apontando a digitação e **sem área em branco** (FR-011)
- [X] T045 [US3] Aparar espaços e quebras de linha do código digitado antes de enviar (FR-013)
- [X] T046 [US3] Exibir aviso de **preenchimento** para o campo vazio, visualmente distinto do desfecho **inválido** (FR-014)
- [X] T047 [P] [US3] Cobrir em `frontend/tests/portaria.test.tsx` que o campo de digitação está presente **mesmo com a câmera disponível**, que o campo vazio produz aviso de preenchimento, e que o formulário é operável só pelo teclado (FR-055 equivalente, US3-7)
- [X] T048 [P] [US3] Cobrir em `frontend/tests/portaria.test.tsx` que a câmera negada exibe explicação e mantém a digitação funcionando

**Checkpoint**: **MVP fechado** — a portaria funciona mesmo sem câmera, que é o cenário mais provável de demonstração (R7).

---

## Phase 6: US4 — A segunda apresentação não entra (P1)

**Goal**: O mesmo ingresso apresentado de novo responde **já utilizado**, com o instante do uso.

**Independent Test**: Validar um ingresso, validá-lo de novo, e conferir **já utilizado** e que o
instante do primeiro uso não muda.

- [X] T049 [P] [US4] Cobrir em `backend/tests/test_gate_api.py` que a segunda validação devolve `situacao: "ja_utilizado"` com `utilizado_em` (FR-021)
- [X] T050 [P] [US4] Cobrir em `backend/tests/test_gate_api.py` que apresentações repetidas **nunca** alteram o instante do primeiro uso (FR-033, SC-006)
- [X] T051 [P] [US4] Cobrir em `backend/tests/test_gate_api.py` que a validação é **idempotente**: repetir não muda nada além de repetir o desfecho (FR-037)
- [X] T052 [US4] Exibir o instante do uso em `Desfecho.tsx`, formatado para leitura rápida — é o que permite ao operador julgar se é a mesma pessoa voltando (FR-021)
- [X] T053 [P] [US4] Cobrir em `frontend/tests/desfecho.test.tsx` que **já utilizado** e **inválido** são distinguíveis sem ler o texto inteiro (US4-5) — são situações diferentes e exigem reações diferentes

**Checkpoint**: a captura de tela do QR deixa de valer uma segunda entrada.

---

## Phase 7: US5 — O código forjado não entra (P1)

**Goal**: Código inventado, adulterado ou assinado com outro segredo responde **inválido**.

**Independent Test**: Alterar um caractere de um código legítimo, apresentá-lo, e conferir
**inválido** — e que a rejeição aconteceu sem consultar o registro de ingressos.

- [X] T054 [P] [US5] Cobrir em `backend/tests/test_gate_signature.py` que um código bem assinado **sem ingresso correspondente** produz o **mesmo** `invalido` da assinatura ruim (FR-029) — quem apresenta não recebe pista de onde o palpite chegou perto
- [X] T055 [P] [US5] Cobrir em `backend/tests/test_gate_signature.py` que a resposta `invalido` **não traz nenhum campo extra** — nem do ingresso, nem da sessão (contracts/gate-api.md)
- [X] T056 [US5] Cobrir em `backend/tests/test_gate_signature.py` que o `s` do payload divergindo da sessão do ingresso no banco produz `invalido`, e não uma exceção (R4, passo 3)
- [X] T057 [P] [US5] Cobrir em `frontend/tests/desfecho.test.tsx` que **inválido** deixa claro que **não é para deixar entrar**, sem jargão (US5-6)

**Checkpoint**: a propriedade que a 008 criou vira consequência prática na porta.

---

## Phase 8: US6 — O ingresso da outra sessão não entra por esta porta (P1)

**Goal**: Ingresso legítimo de outra sessão responde **sessão errada**, sem ser consumido.

**Independent Test**: Com a portaria recebendo a sessão A, apresentar um ingresso da sessão B e
conferir **sessão errada** — e que o ingresso da sessão B **continua não utilizado**.

- [X] T058 [P] [US6] Cobrir em `backend/tests/test_gate_api.py` que um ingresso de outra sessão devolve `situacao: "sessao_errada"` com `sessao_do_ingresso` — filme, horário e sala (FR-022)
- [X] T059 [US6] Cobrir em `backend/tests/test_gate_api.py` que o ingresso recusado por sessão errada **continua com `used_at` nulo** (FR-031) e que, apresentado na porta certa em seguida, é **válido** (US6-4) — é o teste que pega o dia em que a checagem de sessão passar a escrever
- [X] T060 [P] [US6] Cobrir em `backend/tests/test_gate_api.py` que um ingresso **já utilizado e de outra sessão** responde **sessão errada**, não "já utilizado" — a ordem de FR-030, porque é essa a informação que muda a ação do operador
- [X] T061 [P] [US6] Cobrir em `backend/tests/test_gate_api.py` que um ingresso de sessão **cancelada** responde **sessão errada** com `cancelada: true` — e que **nenhum quinto desfecho** foi criado (FR-023, FR-024)
- [X] T062 [US6] Exibir em `Desfecho.tsx` a sessão a que o ingresso pertence, e a frase específica quando ela foi cancelada (FR-022, FR-023)
- [X] T063 [P] [US6] Cobrir em `frontend/tests/desfecho.test.tsx` que **sessão errada** informa a sessão do ingresso e que o caso cancelado tem frase própria dentro do mesmo desfecho

**Checkpoint**: os **quatro** desfechos existem, e o Princípio III fecha.

---

## Phase 9: US7 — Só a portaria valida (P2)

**Goal**: Cliente, organizador e visitante são recusados pelo servidor.

**Independent Test**: Tentar listar sessões e validar como `cliente1`, como organizador e sem sessão,
conferindo as recusas.

- [X] T064 [P] [US7] Cobrir em `backend/tests/test_gate_api.py` que cliente e organizador recebem `403` com "Apenas a portaria valida ingressos." nos **dois** endereços (FR-040)
- [X] T065 [US7] Cobrir em `backend/tests/test_gate_api.py` que um cliente validando um ingresso **dele mesmo** recebe `403` e que o `used_at` daquele ingresso **continua nulo** — um cliente marcando o próprio ingresso como usado é a falha que esta recusa previne
- [X] T066 [P] [US7] Cobrir em `backend/tests/test_gate_api.py` que visitante sem sessão recebe `401` com "Entre para usar a portaria." nos dois endereços (FR-042)
- [X] T067 [P] [US7] Cobrir em `backend/tests/test_gate_api.py` que o papel de portaria **continua sem** poder reservar e pagar — nenhuma asserção de 007 e 008 enfraquecida (FR-044)
- [X] T068 [US7] Tratar `403` em `frontend/app/portaria/page.tsx` com explicação de que a área é da portaria, **sem** redirecionar à entrada — entrar de novo não muda o papel (FR-041)
- [X] T069 [P] [US7] Cobrir em `frontend/tests/portaria.test.tsx` que o papel errado lê a explicação e **não** é redirecionado

**Checkpoint**: as recusas do servidor cobrem os dois endereços e os três atores.

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Verificar que a prova prova, fechar o ponta a ponta, e escrever o que o avaliador
precisa ler.

**⚠️ T070 É A TAREFA MAIS IMPORTANTE DESTA FASE**, e a única da série que não tem constraint para
remover. Aqui a verificação é substituir a escrita condicional pelo código errado.

- [X] T070 Substituir temporariamente o `UPDATE` condicional em `services/portaria.py` pelo `if used_at is not None` seguido de `save()`, rodar `test_gate_concurrency.py` e conferir que ele **falha** com mais de um `valido`; restaurar. Se ele **passar**, o teste não prova nada — provavelmente falta `transaction=True`, e as threads compartilham conexão (quickstart.md)
- [X] T071 Trocar `sessoes_da_portaria` para usar `sellable()`, rodar `test_gate_api.py` e conferir que T015 **falha**; restaurar. É a verificação de que a armadilha herdada está guardada (R11)
- [X] T072 Acrescentar o campo de uso ao `TicketSerializer`, rodar `test_share_link_leakage.py` e conferir que ele **falha**; remover. É a verificação de que o estado de uso não vaza para a página compartilhada **pública** (R14)
- [X] T073 Acrescentar o campo de uso à lista de **proibidos** em `backend/tests/test_share_link_leakage.py`, para que a proteção seja explícita em vez de consequência (FR-048)
- [X] T074 [P] Escrever `frontend/tests/e2e/portaria.spec.ts`: entrar como portaria, escolher a sessão, validar um ingresso pela **digitação**, conferir **válido**, validar de novo e conferir **já utilizado**, e apresentar um código adulterado e conferir **inválido**
- [X] T075 [P] Acrescentar ao e2e o percurso de **sessão errada**: trocar a sessão da porta, validar, conferir o desfecho e conferir que o ingresso **continua valendo** ao voltar à porta certa
- [X] T076 [P] Conferir a 320px que a tela de portaria permanece completa, sem rolagem horizontal, e que o desfecho continua legível à distância (FR-019, SC-004)
- [X] T077 [P] Conferir com o TMDb indisponível que a lista de sessões e a validação funcionam idênticas (FR-008, SC-014)
- [X] T078 Conferir que nenhum valor de cor, espaçamento, tipografia, raio ou duração ficou fora dos tokens nos dois CSS novos (FR-049)
- [ ] T079 **PENDENTE — exige câmera física e um QR real.** Executar a verificação **manual** do quickstart (Percurso 5): apontar a câmera para um QR real, conferir o desfecho, e **deixar o QR parado dez segundos** conferindo que aquela apresentação produz **um único** desfecho (FR-015, SC-012)
- [X] T080 Atualizar `README.md` com a tela de portaria, o modelo de **sessão da porta** e o motivo dele — inferir a sessão só pelo código torna "sessão errada" impossível —, e a dependência nova
- [X] T081 Registrar no `README.md`, em Limitações conhecidas, que **a câmera exige contexto seguro**: `localhost` serve, **IP de rede local não**, e nenhuma configuração muda isso. Quem abrir a portaria pelo celular via IP não terá câmera, e a digitação manual é o caminho — a exigência da constitution que parecia redundante é o que mantém a portaria funcionando no cenário mais provável de demonstração (R7)
- [X] T082 Registrar no `README.md` que a leitura por câmera é verificada **à mão** e o que o automatizado cobre no lugar — o Princípio VI pede honestidade sobre o buraco
- [X] T083 Atualizar no `README.md` a seção "O que está pronto" e **remover** a limitação "não há tela de portaria", que passa a ser falsa; registrar que o **fluxo ponta a ponta fecha** com esta feature
- [X] T084 Registrar no `README.md` que o cliente **continua sem ver** o estado de uso em "Meus ingressos" e na página compartilhada, e que a ausência é deliberada
- [X] T085 Rodar a suíte inteira e comparar com a linha de base de T001, confirmando que **nenhuma** asserção das features 001–009 foi removida ou enfraquecida (FR-045, SC-016)
- [X] T086 Confirmar que `.env.example` continua sem alteração e que a única dependência nova é `jsQR` — se algo mais mudou, uma decisão foi tomada sem passar pelo research
- [ ] T087 **PARCIAL** — percursos 1, 2, 3, 4, 6 e 7 verificados (por teste automatizado, `curl` e consulta ao banco); o **percurso 5** depende de T079. Percorrer o `quickstart.md` inteiro contra a aplicação rodando

---

## Dependencies & Execution Order

**Fases 1 → 2 são bloqueantes.** Nenhuma user story começa antes de a coluna existir e o pipeline
responder.

**Depois da Fase 2:**

```text
Fase 3 (US1) ──┬── Fase 4 (US2) ── Fase 5 (US3)   ← MVP
               │
               ├── Fase 6 (US4)   ┐
               ├── Fase 7 (US5)   ├─ os outros três desfechos
               └── Fase 8 (US6)   ┘

Fase 9 (US7) — depende dos dois endereços existirem
Fase 10 — depois de tudo
```

**Ordens que não podem inverter:**

- **T007 antes de T010–T012.** É a regra mais importante do arquivo. Sem constraint atrás dele, o
  teste de concorrência escrito depois do serviço é escrito para o serviço — e o serviço errado
  passa.
- **T015–T016 antes de T017.** Segunda aparição de `sellable()` como erro natural; o selector escrito
  antes do teste produz um teste escrito para o selector.
- **T008 antes de T010.** A prova de que a assinatura é conferida sem tocar o banco precisa existir
  antes do pipeline, senão ela é escrita já sabendo por onde ele passa.
- **T059 é o teste que guarda FR-031.** Precisa existir junto com o desfecho de sessão errada, não
  depois: consumir um ingresso legítimo na porta errada é irreversível.
- **T070, T071 e T072 só fazem sentido depois de as fases correspondentes estarem verdes.** São a
  verificação de que as provas provam.
- **T073 depois de T072.** Primeiro se demonstra que o vazamento é possível, depois se fecha.
- **T080–T084 são pré-requisito da avaliação, não polimento.** O modelo de sessão da porta e a
  limitação do contexto seguro são exatamente o tipo de coisa que "pareceria estranha numa leitura
  rápida", e o Princípio VI exige que estejam escritas.

## Parallel Execution Examples

**Fase 2** — depois de T006: `T008` e `T009` juntas. `T007` é sequencial em relação a elas por tocar
o mesmo cenário. `T014` é independente de tudo na fase.

**Fase 3** — `T015`, `T016` e `T020` no mesmo arquivo (casos independentes: escrever de uma vez).
`T021` e `T029` tocam arquivos distintos.

**Fase 4** — `T030`, `T031` e `T032` juntas. No front, `T037`, `T038` e `T042` são sequenciais entre
si (mesmo par de arquivos); `T039` e `T040` também.

**Fases 6, 7 e 8** podem correr **em paralelo entre si**, inteiras: os três desfechos já respondem
na API desde a Fase 2, e cada fase acrescenta testes e apresentação em arquivos que não colidem.

**Fase 9** — todas menos `T065` e `T068` são independentes.

**Fase 10** — `T074`, `T075`, `T076` e `T077` em paralelo. `T070`, `T071` e `T072` são sequenciais
entre si: cada uma quebra o código de propósito e restaura.

## Implementation Strategy

**MVP = Fases 1, 2, 3, 4 e 5.** Ao fim da Fase 5 a portaria valida de verdade: escolhe a sessão, lê
o código pelos dois caminhos e libera a entrada — e funciona sem câmera, que é o cenário mais
provável de demonstração.

**Mas a feature não fecha no MVP.** O Princípio III exige os **quatro** desfechos; Fases 6, 7 e 8 não
são refinamento. Elas são baratas — o pipeline já as produz desde a Fase 2 — e são o que faz a tela
de portaria existir de fato.

**Ordem sugerida de entrega incremental**:

1. **Fases 1–2** — a coluna, o pipeline e a prova de concorrência. Nada visível, e é onde mora o
   risco inteiro da feature.
2. **Fases 3–5** — a tela, a escolha da sessão e os dois caminhos de entrada. MVP fecha.
3. **Fases 6–8** — os outros três desfechos. Podem sair juntas.
4. **Fase 9** — as recusas por papel.
5. **Fase 10** — a verificação de que as provas provam, e o README que fecha o fluxo ponta a ponta.

**Três pontos de não avançar**:

- **Se T070 passar em vez de falhar, parar.** É a verificação mais importante do projeto até aqui:
  sem constraint, um teste de concorrência que fica verde com o código errado significa que a
  garantia não está sendo testada por ninguém.
- **Se T059 falhar, parar e não seguir para a Fase 9.** Significa que "sessão errada" está
  consumindo o ingresso, e cada teste rodado a partir dali queima ingressos legítimos.
- **Se T072 passar em vez de falhar, parar.** O estado de uso estaria alcançável pela página
  compartilhada **pública** da 009, e o teste que deveria pegar isso não pega.
