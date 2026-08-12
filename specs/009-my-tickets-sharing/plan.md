# Implementation Plan: Meus Ingressos e Compartilhamento por Link

**Branch**: `main` — o hook do Spec Kit criaria `009-my-tickets-sharing`; o projeto trabalha sem
branches de feature desde a 001, por decisão registrada do autor | **Date**: 2026-08-12 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-my-tickets-sharing/spec.md`

## Summary

Dar endereço permanente ao ingresso que a 008 emitiu, e um link que permita mostrá-lo a outra pessoa
sem que ela entre em conta nenhuma. São duas superfícies: a área do cliente (`/meus-ingressos`) e a
página pública (`/ingresso/[token]`).

**A decisão que estrutura a feature no banco**: um modelo próprio, `TicketShareLink`, com um índice
**parcial** `UNIQUE(ingresso) WHERE revogado_em IS NULL`. É o terceiro capítulo da mesma história —
a 007 precisou de constraint absoluta porque `now()` não é imutável, a 008 pôde usar parcial porque
`status = 'approved'` é, e aqui `revogado_em IS NULL` também é. A forma muda por limitação do
PostgreSQL, nunca por preferência. É o índice parcial que permite **preservar os links revogados**,
e é preservá-los que faz "revogado nunca volta a valer" ser estrutura em vez de sorte do gerador.

**A decisão que estrutura a feature no código**: a página pública é servida pelo `TicketSerializer`
da 008, **sem alteração**, e os campos novos da área do dono vão para um serializer separado. O
`TicketSerializer` já expõe exatamente o recorte que FR-037 autoriza; o risco não é o que ele mostra
hoje, é a pressão de crescimento. Dois serializers fazem essa pressão apontar para o lado que não é
público, por construção — o teste de não vazamento vira a segunda linha de defesa, não a única.

**E a armadilha herdada** — cada feature tem tido a sua, e esta não é exceção. Toda consulta de
sessão escrita da 001 até a 008 passa por `sellable()`, que é `published() AND starts_at > now()`.
É o filtro certo para estoque e o **errado para histórico**: usá-lo aqui esvaziaria para sempre o
grupo "já aconteceram" e faria sumir justamente o ingresso da sessão cancelada, sobre o qual o
cliente mais precisa de explicação. A linha errada é mais parecida com o resto do projeto do que a
certa, e nenhuma constraint a pega.

**Nenhuma dependência nova.** O token é `secrets.token_urlsafe(32)`, biblioteca padrão.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 + DRF · Next.js 15 · `qrcode` (já trazida pela 008, reaproveitada
sem mudança). **Nada acrescentado** a `pyproject.toml` nem a `package.json`

**Storage**: PostgreSQL 16. **Uma** migração cria `TicketShareLink` e seu índice parcial juntos —
mesma disciplina de 007 e 008: o modelo não entra sem a constraint que o protege

**Testing**: `pytest` + `pytest-django`, com `transaction=True` e threads para a corrida de geração
de link, e `django_assert_num_queries` para fixar a ausência de N+1 · Vitest + Testing Library ·
Playwright. **SC-005 (leitura por leitor de QR de terceiro) é verificada à mão**, pelo quickstart —
está dito abaixo por que, e o que o automatizado cobre no lugar

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Performance Goals**: lista com até 12 ingressos, com os QR, em ≤ 1 s · página compartilhada em
≤ 500 ms · a lista não pode fazer uma consulta por ingresso

**Constraints**: nenhuma asserção das features 001–008 removida ou enfraquecida · disciplina de
tokens da 006 mantida · as três superfícies funcionam com o TMDb fora do ar · autorização no
servidor · a `TICKET_SIGNING_KEY` continua sem chegar ao navegador · a página pública não recebe
cookie de sessão

**Scale/Scope**: dezenas de ingressos por cliente no cenário de avaliação. A unicidade do link ativo
precisa valer sob concorrência real, como a das duas features anteriores

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | Fecha a etapa 4 da ordem de construção obrigatória ("área Meus ingressos e link de compartilhamento") e destrava a 5. Estado vazio, link revogado, link inexistente, sessão cancelada e recusa por papel têm cada um estado próprio em pt-BR. Nenhum item da lista de fora de escopo é construído. |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | Esta feature **não escreve** em reserva, assento, pagamento ou ingresso — é leitura, mais uma tabela nova ao lado. A única escrita nova é o link, e a unicidade dele é do banco (índice parcial), com teste de concorrência que precisa **falhar** se a constraint sair. |
| **III. Ingresso Inforjável (NÃO NEGOCIÁVEL)** | ✅ PASS | O código do QR não muda: continua derivado de `public_id` + sessão em `services/ingressos.py`, módulo puro. O token do link é **outro segredo, com outro ciclo de vida** (FR-026, FR-033), e SC-010 fixa isso com teste que compara o código antes e depois de revogar. A cláusula do próprio princípio sobre o link — "conceder apenas visualização, nunca a conta, o histórico ou dado de pagamento" — é o recorte de FR-037, provado por FR-042. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Só papel cliente acessa a área (`403` para organizador e portaria); só o dono abre, gera e revoga (`404`, não `403`, para não confirmar existência). Teste de acesso cruzado nas 12 combinações. A página pública é `AllowAny` **com `authentication_classes = []`** — decisão declarada, como o mapa da 007. |
| **V. Interface Autoral** | ✅ PASS | Estado vazio escrito para humanos com saída para o catálogo. Link revogado e link inexistente têm a mesma frase, e é uma frase, não uma 404 genérica. Futuro e passado distinguidos sem depender só de cor. Tokens da 006 preservados; o `--cor-fundo-qr` da 008 é reaproveitado. |
| **VI. Rastro de Decisão** | ✅ PASS | README ganha a área, o comportamento do link e — obrigatoriamente — a decisão de guardar o token em texto claro, com o que se ganha e o que se perde (R3). Quinze decisões em research.md. |
| **VII. Isolamento da API Externa** | ✅ PASS | As três superfícies leem só o banco local. Filme, sessão, sala e lugar estão persistidos desde a 001; nenhuma chamada ao TMDb entra neste caminho. |

### O ponto que exige julgamento: o token fica em texto claro no banco

Guardar um segredo ao portador em texto claro contraria o hábito correto — senha e chave de API se
guardam em hash. A escolha é deliberada e o motivo é do produto, não da preguiça:

**FR-028 e FR-035 exigem que o dono reencontre o link ativo depois**, para copiar de novo. Com hash,
o token existiria só no instante da criação: quem fechou a aba perderia o link e teria de revogar e
gerar outro. "Meu link" deixaria de ser algo que se tem para virar algo que se recebe uma vez — e
essa forma de produto foi fixada pelo autor na spec.

**O que se perde, sem eufemismo**: um vazamento do banco entrega links utilizáveis contra o servidor
vivo, e a página compartilhada renderiza QR válido para eles. **O que não se perde**: a
`TICKET_SIGNING_KEY` não está no banco, então um dump sozinho não permite forjar código nenhum — o
alcance se limita aos ingressos que já têm link ativo, e o dono revoga.

**Mitigações que entram junto**: 256 bits de entropia; revogação imediata e definitiva; o token
nunca aparece em resposta que não seja a do dono; `noindex` e `no-referrer` na página pública.

Vai para o README pelo Princípio VI, e para Complexity Tracking para não depender de alguém ler esta
seção. **Se em revisão a troca não se sustentar, o caminho é mudar FR-028 na spec** — não guardar
hash em silêncio e deixar o botão de copiar quebrado.

**Nenhuma violação.** Dois itens em Complexity Tracking: a decisão acima e a alteração aditiva num
componente da 008.

## Project Structure

### Documentation (this feature)

```text
specs/009-my-tickets-sharing/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 15 decisões; R10 é a armadilha que mais importa
├── data-model.md        # Fase 1 — TicketShareLink, a constraint e as consultas da lista
├── quickstart.md        # Fase 1 — incluindo ler o QR com o celular e revogar um link ao vivo
├── contracts/
│   └── my-tickets-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/screening/
│   ├── models.py                        # ALTERADO — TicketShareLink e seu índice parcial
│   ├── migrations/0004_*.py             # NOVO — modelo e constraint, juntos
│   ├── services/
│   │   └── compartilhamento.py          # NOVO — gerar (idempotente) e revogar
│   ├── selectors.py                     # ALTERADO — ingressos_do_cliente, ingresso_do_dono,
│   │                                    #   ingresso_por_token. NENHUMA usa sellable() (R10)
│   ├── serializers.py                   # ALTERADO — MeuIngressoSerializer, LinkSerializer.
│   │                                    #   TicketSerializer INTOCADO (R6, FR-058)
│   ├── permissions.py                   # ALTERADO — IsCustomerParaIngressos
│   ├── views.py                         # ALTERADO — MyTicketsView, TicketDetailView,
│   │                                    #   TicketShareLinkView, SharedTicketView
│   └── urls.py                          # ALTERADO — cinco endereços novos
└── tests/
    ├── test_my_tickets_api.py           # NOVO — lista, ordem, grupos, vazio, autorização
    ├── test_share_link_api.py           # NOVO — gerar, idempotência, revogar, token morto
    ├── test_share_link_leakage.py       # NOVO — a prova de FR-042, obrigatória
    ├── test_share_link_concurrency.py   # NOVO — a prova de FR-029
    └── test_ticket_signature.py         # ALTERADO — acrescenta SC-010 (revogar não toca o código)

frontend/
├── app/meus-ingressos/
│   ├── page.tsx                         # NOVO — a lista, com grupos e estado vazio
│   ├── [id]/page.tsx                    # NOVO — o ingresso do dono, com as ações de link
│   └── meus-ingressos.module.css        # NOVO
├── app/ingresso/[token]/
│   ├── page.tsx                         # NOVO — a página pública; noindex + no-referrer
│   └── publico.module.css               # NOVO
├── app/api/link-do-ingresso/route.ts    # NOVO — proxy POST (gerar) e DELETE (revogar)
├── components/tickets/
│   ├── Ingresso.tsx                     # ALTERADO — indice/total viram opcionais (aditivo)
│   ├── PainelDeLink.tsx                 # NOVO — ilha cliente: copiar, gerar, revogar
│   └── tickets.module.css               # ALTERADO — estilos do painel e dos grupos
├── components/header/AccountMenu.tsx    # ALTERADO — item "Meus ingressos" só para cliente
├── lib/api.ts                           # ALTERADO — fetchMeusIngressos, fetchIngresso,
│                                        #   fetchIngressoCompartilhado, postLink, deleteLink
├── lib/types.ts                         # ALTERADO — MeuIngresso, LinkDeCompartilhamento
└── tests/
    ├── meus-ingressos.test.tsx          # NOVO
    ├── ingresso-publico.test.tsx        # NOVO — inclui a ausência de campos proibidos
    └── e2e/compartilhamento.spec.ts     # NOVO — gerar, abrir sem sessão, revogar

README.md                                # ALTERADO — a área, o link e a decisão do token (FR-061)
```

**Structure Decision**: a feature continua em `apps/screening`, junto de `Ticket`. `TicketShareLink`
tem chave estrangeira para `Ticket` e carrega uma constraint sobre ela — mesma regra das duas
features anteriores: a garantia mora na app do modelo que protege, e a migração que cria os dois é
uma só. Uma app `sharing` separada faria chave estrangeira e constraint atravessarem fronteira de app
sem ganhar nada.

`services/compartilhamento.py` é arquivo próprio, e não mais uma função em `services/ingressos.py`:
aquele módulo é **puro** por decisão da 008 — não importa modelo, não toca o banco, e é essa ausência
que torna `num_queries == 0` verificável no Princípio III. Gerar e revogar link escrevem no banco. Se
entrassem lá, a garantia da 008 deixaria de vir da estrutura e passaria a depender de disciplina.

`selectors.py` ganha as consultas da lista em funções próprias, com o motivo de **não** usar
`sellable()` escrito ao lado (R10) — é onde a próxima pessoa que for padronizar consultas vai ler.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **O link é modelo próprio, não coluna** — porque revogado precisa ser preservado, para nunca voltar
   a valer e para responder igual a um token inexistente.
2. **`UNIQUE(ingresso) WHERE revogado_em IS NULL`**, índice parcial. "Consultar se já existe e criar
   se não" é o padrão exato que a concorrência quebra; a perdedora da corrida não recebe erro,
   recebe o link do vencedor — que é literalmente a idempotência que FR-028 promete.
3. **Token em texto claro**, com a troca declarada. `secrets.token_urlsafe(32)`, 256 bits, sem
   dependência nova.
4. **A resposta pública é definida por inclusão** e o `TicketSerializer` da 008 fica intocado. O risco
   é a pressão de crescimento, e dois serializers fazem essa pressão apontar para longe do público.
5. **Duas consultas, não uma**, porque a ordenação inverte de direção entre os grupos — e entregar os
   grupos já separados tira o relógio do navegador da decisão (FR-010).
6. **A armadilha herdada é `sellable()`** — some com o passado e com a sessão cancelada, sem que
   nenhuma constraint reclame.
7. **Revogação e cache**: sem `force-dynamic` na rota pública, a revogação fica correta no banco e
   irrelevante na prática. É a falha mais discreta da feature.
8. **`noindex` e `no-referrer`** na página compartilhada. O segundo é o que impede o token de vazar
   pelo cabeçalho `Referer` no dia em que alguém acrescentar um link de saída.
9. **O componente `Ingresso` da 008 é reaproveitado nas três superfícies** — e, como só aceita a forma
   `Ingresso`, ele **não tem como** renderizar comprador ou valor na página pública.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — `TicketShareLink`, o índice parcial, o caminho da corrida de
  geração, e as consultas da lista com o motivo de não filtrarem por `sellable()`.
- **[contracts/my-tickets-api.md](./contracts/my-tickets-api.md)** — os cinco endereços, seus
  desfechos, e a **lista de campos proibidos** na resposta pública.
- **[quickstart.md](./quickstart.md)** — percorrer as três superfícies, **ler o QR com o celular**,
  **revogar um link ao vivo** e conferir que o código do ingresso não mudou.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Seis pontos a vigiar na implementação:

- **Nenhuma consulta desta feature pode usar `sellable()`.** O grupo "já aconteceram" ficaria vazio
  para sempre e o ingresso de sessão cancelada sumiria — e a linha errada parece mais idiomática que
  a certa (R10).
- **A rota pública precisa de `force-dynamic`.** Sem ele a revogação continua correta no banco e
  irrelevante na tela, e nenhum teste de back-end falha (R13).
- **`TicketSerializer` não ganha campo nenhum.** No dia em que ganhar, o campo aparece na página
  pública no mesmo commit, em silêncio.
- **`services/ingressos.py` continua sem importar modelo.** A escrita do link mora em módulo separado
  justamente para não derrubar a garantia de `num_queries == 0` da 008.
- **O teste de concorrência precisa de transação real.** Herdado da 007 e repetido na 008: sem
  `transaction=True` as threads compartilham conexão e o teste passa com ou sem a constraint.
- **A alteração em `Ingresso.tsx` tem de ser aditiva.** Props opcionais com o comportamento atual
  preservado quando presentes — nenhuma asserção de `tests/ingresso.test.tsx` pode mudar (FR-057).

### Nota sobre SC-005: o que é automatizado e o que é manual

SC-005 exige que **um leitor de QR de terceiro** leia o código da tela a 320px. Isso não é
automatizável aqui sem trazer um decodificador nativo (`zbar` e afins) só para esta asserção —
dependência de sistema, em teste, para verificar uma propriedade física de renderização.

**Verificação manual**, no quickstart: abrir o ingresso em 320px e ler com o celular.

**O que o automatizado cobre no lugar**, para que a verificação manual não seja a única coisa entre
o projeto e um QR ilegível: o QR é SVG vetorial (não pixeliza), renderiza com no mínimo 128px de
lado no viewport estreito, mantém o fundo claro do token `--cor-fundo-qr` da 008 (leitor precisa do
contraste, e é por isso que essa superfície não segue o tema escuro), e o código em texto está
presente e **é igual** ao conteúdo assinado — que é a via alternativa quando a leitura falha.

Está dito assim, e não escondido atrás de um teste que verifica outra coisa, porque o Princípio VI
pede honestidade sobre o que não está coberto.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Token de compartilhamento guardado em texto claro**, contrariando o hábito correto de guardar segredo ao portador em hash | FR-028 e FR-035 exigem que o dono reencontre e recopie o link ativo depois. Com hash o token só existe no instante da criação, e quem fechou a aba perderia o link — "meu link" viraria algo que se recebe uma vez, e não algo que se tem. A forma do produto foi fixada pelo autor na spec. | **Hash do token** rejeitado por quebrar FR-028/FR-035. **Token assinado sem linha no banco** rejeitado por ser irrevogável sem uma lista de revogados — ou seja, sem a tabela que se tentaria evitar — e por aproximar o token do código do QR, que é a fusão que a decisão 2 da spec proíbe. Mitigado com 256 bits, revogação imediata, `noindex` e `no-referrer`. **Se a troca não se sustentar em revisão, o caminho é mudar FR-028 na spec**, não guardar hash em silêncio e deixar o botão de copiar quebrado. |
| **Alterar `components/tickets/Ingresso.tsx`**, que pertence à 008 | O componente é o cartão com QR e código legível, e a feature precisa dele em três superfícies. Um ingresso só (página pública) não tem "Ingresso 1 de 1" para exibir. | **Componente novo** rejeitado: duas cópias do mesmo cartão, e a primeira divergência entre elas seria o tamanho do QR — ou seja, a legibilidade na catraca, exatamente o que SC-005 protege. A alteração é **aditiva** (props opcionais, comportamento preservado quando presentes), então nenhuma asserção existente muda. |
