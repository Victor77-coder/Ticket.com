# Implementation Plan: Painel do Organizador — Programar Filmes, Salas e Sessões

**Branch**: `main` — sem branch própria, como nas 003–012 | **Date**: 2026-08-12 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-painel-do-organizador/spec.md`

## Summary

Dar ao terceiro papel a tela que ele nunca teve. O organizador entra, **pousa** numa área de
programação, escolhe filme (do catálogo local ou trazendo do TMDb pelo back-end), define
sala/horário/preço e publica — e a sessão aparece no caminho de compra que o cliente já percorre.

**Isto é etapa 6 da constitution, não uma feature nova de negócio.** O fluxo ponta a ponta fechou na
010. Nada aqui reabre reserva, pagamento, ingresso ou portaria. O que muda é a **origem da grade**:
até hoje só o `seed_demo` a produzia.

**O trabalho é 80% expor por API o que o seed já faz em Python.** Salas, assentos, sessões e
sincronização de filme existem inteiros dentro de comandos de management. A feature os move para
onde um usuário autenticado alcança — e **essa mudança de lugar é a armadilha**, não a lógica.

**Três regras já escritas não podem ganhar uma segunda cópia**, e cada uma tem um dono claro:

| Regra | Onde vive hoje | Depois desta feature |
|---|---|---|
| Mapa físico da sala a partir da capacidade | `seed_demo._seed_seats` / `_posicoes_da_sala` | `apps/screening/services/salas.py`, consumido pelos dois |
| Mapeamento TMDb → `Movie` (+ gêneros, classificação, trailers) | `catalog/services/tmdb_sync.sync_movie` | O mesmo, chamado também pelo painel (R2) |
| "Ocupação viva" (reserva paga OU não vencida) | `Reservation.OCUPANDO` via `selectors.ocupacoes_vivas` | O mesmo, consumido para recusar troca de capacidade (R5) |

**A armadilha de front-end é a tabela de papéis.** `CASA_DO_PAPEL` une hoje num campo só
(`telaUnica`) dois fatos que o organizador separa: ele **pousa** no painel, mas **não** fica preso
nele. O middleware nega por padrão — registrar o organizador com `telaUnica: true` o trancaria fora
do catálogo público, que é exatamente onde ele confere o próprio trabalho (FR-002, FR-004).

**A armadilha de back-end é a pré-consulta.** `UNIQUE(room, starts_at)` é a garantia do conflito de
horário. Um `if Screening.objects.filter(...).exists()` antes do INSERT é o padrão que a
concorrência quebra e que este projeto já rejeitou três vezes. A frase bonita vem de capturar o
`IntegrityError` da constraint nomeada (R4, SC-004).

## Technical Context

**Language/Version**: Python 3.12 · TypeScript 5.x / Node 20 · CSS (módulos + tokens da 006/011)

**Primary Dependencies**: Django REST Framework · Next.js 15 · httpx (já presente, no `TMDBClient`) —
**nenhuma biblioteca nova**

**Storage**: PostgreSQL — **nenhuma migração, nenhuma tabela, nenhuma coluna**. `Movie`, `Room`,
`Seat`, `Screening` já têm tudo. A ausência de coluna de origem em `Screening` é decisão registrada
(FR-042), não omissão.

**Testing**: pytest (contratos de programação, negação por papel para cliente e portaria,
concorrência de `(sala, horário)`, paridade do mapa de sala entre seed e painel, recusa do seed
destrutivo) · Vitest + Testing Library (`CASA_DO_PAPEL` com dois fatos, menu da conta, estados da
área) · Playwright (programar → publicar → comprar, ponta a ponta)

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Project Type**: Web application (Django + Next.js), já existente

**Performance Goals**: nenhuma meta nova. A grade do painel é uma consulta com `select_related`
sobre dezenas de linhas no cenário do desafio; a contagem de ocupação por sessão é agregada em
**uma** consulta, não N+1 (R6)

**Constraints**: nenhuma regra de compra reaberta (FR-038) · chave do TMDb nunca no navegador
(FR-010) · autorização no servidor, esconder botão não conta (FR-034, FR-037) · uma única regra de
mapa de sala (FR-017) · um único mapeamento TMDb (FR-011a) · nenhum valor visual fora dos tokens
(FR-039) · sem migração

**Scale/Scope**: 4 rotas de front · 11 endpoints · 0 tabelas · 0 migrações · 1 módulo de serviço
extraído · 1 flag em comando de management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | É literalmente a **etapa 6** da ordem obrigatória — "só então: … painel do organizador". As etapas 1–5 fecharam na 010. Cada superfície nova nasce com sucesso, erro e vazio (FR-007): grade vazia, sala vazia, busca sem resultado, TMDb fora do ar, recusa por papel. Nenhuma seção "em breve". |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | Nenhuma escrita em `Reservation`, `ReservedSeat`, `Payment` ou `Ticket`. `UNIQUE(sessão, assento)`, `SELECT FOR UPDATE` e os testes de concorrência existentes **não são tocados**. O único ponto de contato é de **leitura**: recusar troca de capacidade quando há ocupação viva (FR-020/FR-021), consumindo `Reservation.OCUPANDO` — a regra não é reescrita. Refazer assentos só ocorre com zero ocupação, dentro de transação, e `Seat` é PROTECT: se a leitura errar, o banco recusa. |
| **III. Ingresso Inforjável e Validação Única (NÃO NEGOCIÁVEL)** | ✅ PASS | `services/ingressos.py`, `TICKET_SIGNING_KEY` e `services/portaria.py` intactos. Cancelar sessão **não** apaga ingresso, não estorna e não muda `used_at` (FR-031). O desfecho "sessão errada" da 010 continua vindo da mesma comparação de sessão. |
| **IV. Papéis Explícitos e Autorização no Servidor** | ✅ PASS — **é a feature inteira** | Nasce `IsOrganizer`, e **toda** escrita de programação a exige (FR-034). Cliente e portaria autenticados recebem `403`, nunca `401` — entrar de novo não muda papel (FR-035). Teste de acesso cruzado para os dois papéis (FR-036). O `redirect` do front é produto; a recusa é do servidor. O seed continua com a composição exigida: 1 organizador, 2 clientes, 1 portaria. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | A área é composta, não gerada: a grade agrupa por dia, o estado da sessão se distingue por **rótulo + forma**, não só cor (FR-029) — mesma disciplina do mapa de assentos. Todo erro tem frase em português com próxima ação, incluindo os quatro do TMDb que o `TMDBClient` já escreve. Tokens da 006/011 reusados; espaço novo, se preciso, nasce token. |
| **VI. Rastro de Decisão Versionado** | ✅ PASS | 11 decisões em `research.md`. README ganha a seção do painel e o aviso de que recriar a demonstração passou a exigir confirmação (FR-040). Contratos versionados em `contracts/`. Commits incrementais por contexto. |
| **VII. Isolamento da API Externa** | ✅ PASS | A busca no TMDb é **nova rota do Django**, não do navegador (FR-009, FR-010). Reusa `TMDBClient` — mesmo timeout, mesmo `TMDBError` em pt-BR. Escolher um resultado **persiste localmente** pelo mesmo `sync_movie` (FR-011a): é a frase do Princípio VII, "no momento em que o organizador cria a sessão", virando código. TMDb fora do ar degrada só a busca (FR-014). |

### O ponto que exige julgamento: o seed que passa a recusar

FR-041 a FR-044 mudam um comando que hoje sempre roda. É a única alteração do plano que **piora** a
ergonomia de alguém — quem recria a demonstração pela segunda vez passa a precisar de `--force`.

**Por que assim mesmo.** Sem marcador de origem — que FR-042 proíbe criar — não existe como
distinguir a sessão do seed da sessão do painel. As saídas eram: apagar tudo em silêncio (perde
trabalho sem avisar) ou acrescentar coluna (contraria "nenhum modelo novo é necessário" e obriga a
migração numa feature que não tem nenhuma). Recusar e explicar não perde nada e não custa esquema.

**A primeira execução, em base vazia, continua sem passo extra** (FR-044) — é o caminho do
avaliador, e ele nunca vê o aviso.

**Nenhuma violação de gate.** O custo de ergonomia e o acoplamento novo entre `seed_demo` e o módulo
de salas entram em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-painel-do-organizador/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 11 decisões; R1 (extração da regra de sala) e R4 (conflito no banco)
├── data-model.md        # Fase 1 — zero migração; ciclo de vida da sessão e da sala
├── quickstart.md        # Fase 1 — percorrer o painel e provar o recorte
├── contracts/
│   ├── programacao-api.md   # os 11 endpoints, campos, erros e proibições
│   └── casa-do-papel.md     # a tabela com dois fatos; o que o middleware passa a fazer
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/apps/accounts/
└── permissions.py                    # NOVO — IsOrganizer (papel, não domínio: serve catalog e screening)

backend/apps/screening/
├── services/salas.py                 # NOVO — posicoes_da_sala() e gerar_assentos(); a ÚNICA regra
├── services/programacao.py           # NOVO — criar/editar/publicar/cancelar sessão; captura o IntegrityError
├── selectors.py                      # ALTERADO — grade do organizador + ocupação agregada (sem N+1)
├── serializers.py                    # ALTERADO — Sala*, Sessao* de programação (papel ≠ público)
├── views.py                          # ALTERADO — views de salas e sessões sob IsOrganizer
└── urls.py                           # ALTERADO — prefixo /programacao/

backend/apps/catalog/
├── services/tmdb_client.py           # ALTERADO — search_movies(): /search/movie, mesmo timeout e erro
├── services/programacao_filmes.py    # NOVO — importar_filme(tmdb_id): movie_detail + sync_movie
├── serializers.py                    # ALTERADO — resultado de busca TMDb + filme do catálogo p/ painel
├── views.py                          # ALTERADO — busca e importação sob IsOrganizer
├── urls.py                           # ALTERADO — prefixo /programacao/
└── management/commands/seed_demo.py  # ALTERADO — consome salas.py; --force; recusa destrutiva

backend/tests/
├── test_programacao_permissoes.py    # NOVO — cliente e portaria negados (403, não 401)
├── test_programacao_sessoes.py       # NOVO — criar, editar rascunho, publicar, cancelar
├── test_programacao_concorrencia.py  # NOVO — duas criações simultâneas na mesma (sala, horário)
├── test_programacao_salas.py         # NOVO — capacidade, teto, recusa com ocupação
├── test_programacao_filmes.py        # NOVO — busca TMDb, importação, sem duplicar, TMDb fora do ar
├── test_sala_paridade_seed.py        # NOVO — painel e seed produzem o mesmo mapa
└── test_seed_demo.py                 # ALTERADO — recusa sem --force; base vazia roda direto

frontend/
├── lib/papeis.ts                     # ALTERADO — organizer entra; telaUnica vira dois fatos
├── lib/api.ts                        # ALTERADO — chamadas de programação
├── lib/types.ts                      # ALTERADO — tipos da programação
├── middleware.ts                     # ALTERADO — devolverParaCasa continua só p/ tela única
├── app/programacao/page.tsx          # NOVO — a grade (casa do papel)
├── app/programacao/salas/page.tsx    # NOVO — listar e criar salas
├── app/programacao/sessoes/nova/     # NOVO — escolher filme, sala, horário, preço
├── app/programacao/sessoes/[id]/     # NOVO — editar rascunho
├── app/api/programacao/…/route.ts    # NOVO — proxies; o navegador nunca fala com o Django
├── components/programacao/           # NOVO — grade, formulários, busca de filme, estados
└── tests/                            # ALTERADO — auth.test.tsx; NOVO — programacao.test.tsx, e2e

frontend/components/highlights/, components/rows/, components/seats/,
components/payment/, components/tickets/, components/gate/, app/page.tsx   # CONGELADOS
```

**Structure Decision**: sem app Django novo. Cada endpoint mora no app que **possui** o modelo —
filme em `catalog`, sala e sessão em `screening` —, e o que os une é a permissão, que por ser de
**papel** e não de domínio vive em `accounts`. Um app `programacao` separado duplicaria imports e
criaria a dúvida de onde `Screening` "realmente" mora. O front espelha isso com uma rota-raiz
`/programacao` e três irmãs.

## Constitution Re-check (pós-Fase 1)

Rodado depois de `research.md`, `data-model.md` e os dois contratos. **Nenhum gate mudou de status.**
O que o design acrescentou, e que não estava visível antes:

- **II** ficou mais forte, não mais fraco: o desenho de `alterar_capacidade` (R5) lê a ocupação por
  `Reservation.OCUPANDO` e ainda assim se apoia no PROTECT de `Seat` como rede — a recusa explícita
  existe para dar **frase**, não para dar garantia. A garantia continua no banco.
- **IV** ganhou uma verificação estrutural que não existia na Fase 0: o **prefixo** `/api/v1/programacao/`
  faz um endpoint novo nascer coberto. Está no contrato como regra, não como convenção.
- **VII** ficou mais barato do que o previsto: `movie_detail` já usa `append_to_response`, então
  importar um filme completo custa **uma** requisição ao TMDb — a persistência mínima teria custado
  o mesmo e entregado menos (R2).
- **V** ganhou um item verificável a mais: `pode_editar` / `pode_publicar` / `pode_cancelar` vão no
  payload para a interface **desabilitar com explicação** em vez de esconder controle — e o servidor
  revalida os três.

**Um risco que o design tornou nomeável**: o campo `pousa` pode regredir o cliente. Se
`destinoAposEntrada` passar a mandar `customer` para a casa dele, um cliente novo aterrissa no estado
vazio de "Meus ingressos" em vez do catálogo. Está fixado como teste obrigatório em
`contracts/casa-do-papel.md` §Testes novos, item 3.

## Complexity Tracking

| Violação | Por que é necessária | Alternativa simples rejeitada porque |
|---|---|---|
| `seed_demo` passa a recusar rodar sem `--force` quando existe grade | FR-041/FR-042: sem marcador de origem, apagar a programação do painel seria perda silenciosa | Coluna de origem em `Screening` resolveria com precisão — rejeitada por exigir migração numa feature que declara não precisar de nenhuma, e por criar um segundo conceito de "de quem é esta sessão" que nada mais consome |
| `seed_demo` passa a importar `screening/services/salas.py` | FR-017: a regra do mapa da sala tem de ter um dono só | Copiar a função para o painel — rejeitada porque é exatamente a divergência que a spec nomeia como armadilha; a primeira correção de acessibilidade iria para um dos dois lados |
| `IsOrganizer` em `accounts`, servindo dois apps | A programação atravessa `catalog` (filme) e `screening` (sala, sessão) | Uma classe por app — rejeitada por duplicar a decisão de papel em dois lugares, que é o erro que o Princípio IV existe para evitar |
| `CASA_DO_PAPEL` ganha um segundo campo booleano | FR-002: "pousa aqui" e "não alcança mais nada" deixaram de ser o mesmo fato | Manter um campo só — rejeitada porque trancaria o organizador fora do catálogo público (o middleware nega por padrão), contrariando FR-004 |
