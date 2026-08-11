# Implementation Plan: Cabeçalho Global do Site

**Branch**: `002-site-header-navigation` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-site-header-navigation/spec.md`

## Summary

Entregar um cabeçalho persistente em todas as páginas, montado no `app/layout.tsx`, com três
elementos: a identidade **ticket.com** que leva à home, uma busca de filmes com sugestões
ancoradas ao próprio campo, e o ponto de acesso à conta.

A decisão técnica central é **onde a busca-enquanto-digita atravessa a rede**. A arquitetura
atual do projeto é explícita: "o navegador nunca fala com o Django direto" (`lib/api.ts`), e no
Docker Compose o front-end alcança o back-end por `http://backend:8000`, um nome que só existe
dentro da rede do Compose. Sugestões ao vivo exigem uma chamada a partir do navegador, então a
feature introduz um **Route Handler do Next (`/api/busca`) como proxy server-side** — mesma
origem, sem CORS, sem endereço de back-end no bundle, e funciona igual no Compose e fora dele.

No back-end, entra um endpoint público `GET /api/v1/busca/` que lê só o PostgreSQL local, com
correspondência parcial e insensível a acento via extensão `unaccent`. O TMDb continua fora do
caminho de leitura (Princípio VII).

O combobox é escrito à mão, sem biblioteca, seguindo a mesma decisão do carrossel: `aria-activedescendant`, corrida de respostas e foco são mais baratos de escrever do que de contornar
numa lib genérica — e o Princípio V cobra autoria justamente nas superfícies visíveis.

**A US3 (acesso à conta) não fecha nesta feature.** O FR-023 proíbe que o ícone conduza a um
destino inexistente e o FR-022 (decisão do usuário) coloca login/logout na feature de
autenticação, que ainda não existe. O plano entrega US1 e US2 completas e deixa a US3 desenhada e
bloqueada — ver [Complexity Tracking](#complexity-tracking).

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 LTS (front-end)

**Primary Dependencies**: Django 5.x + Django REST Framework · `django.contrib.postgres` (novo em
`INSTALLED_APPS`, habilita o lookup `__unaccent`) · Next.js 15 (App Router) + React 19 · **nenhuma
biblioteca nova de front-end** — sem combobox, sem ícone de terceiro, sem cliente HTTP

**Storage**: PostgreSQL 16 em `localhost:5438`, com a extensão `unaccent` criada por migração

**Testing**: `pytest` + `pytest-django` (contrato da busca, normalização, gate do Princípio IV) ·
Vitest + Testing Library (debounce, corrida de respostas, teclado, estados) · Playwright
(cabeçalho presente nas páginas, home → busca → página do filme)

**Target Platform**: Aplicação web. Front-end em `http://localhost:5003`, API Django em
`http://localhost:8000`, ambos em Docker Compose junto do banco.

**Project Type**: Web application (front-end + back-end separados)

**Performance Goals**: Sugestões visíveis em ≤ 1 s após a pausa na digitação (SC-004) · endpoint
de busca respondendo em ≤ 150 ms com ~20 filmes no catálogo · cabeçalho não pode atrasar o
primeiro painel do carrossel, que continua com o orçamento de 2 s da feature 001

**Constraints**: Nenhum endereço de back-end pode chegar ao bundle do navegador · a busca não
pode chamar o TMDb · o cabeçalho tem de caber de 360 px a 1920 px sem rolagem horizontal ·
nenhuma dependência nova de front-end · a lista de sugestões nunca pode exibir resultado de um
termo já abandonado (FR-015, SC-005)

**Scale/Scope**: 1 cabeçalho, ~20 filmes buscáveis, no máximo 6 sugestões por vez, escala de
avaliação (dezenas de acessos simultâneos), não de produção.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliado contra a Constitution v1.0.0.

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ⚠ PASS com bloqueio registrado | Busca entrega todos os estados juntos: digitando, buscando, com resultados, sem resultados, erro (FR-012, FR-013, FR-018). O ícone de conta é o ponto de atrito: entregá-lo apontando para uma rota inexistente seria a "tela pela metade" que o princípio proíbe. Por isso a US3 fica bloqueada, e não meio-entregue — registrado em Complexity Tracking. |
| **II. Integridade da Reserva** | ➖ N/A | Feature exclusivamente de leitura. **Restrição imposta**: nenhum código deste plano pode escrever ocupação de assento nem antecipar a constraint `UNIQUE(sessão, assento)`, que pertence à feature de reserva. |
| **III. Ingresso Inforjável** | ➖ N/A | Não emite nem valida ingresso. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | `GET /api/v1/busca/` é público e somente leitura, declarando `AllowAny` explicitamente na view — o padrão do projeto continua sendo `IsAuthenticated`. O FR-025 é explícito: o cabeçalho é apresentação, nunca controle de acesso. **Teste obrigatório**: a busca responde sem autenticação **e** não devolve campo algum de gestão (status de sessão, preço de custo, capacidade, contagem de assentos, dado de usuário). |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | Combobox próprio, sem lib. Ícone de conta desenhado como SVG inline, não ícone genérico de biblioteca. Cor, tipografia e espaçamento vindos de `tokens.css`, com os poucos tokens novos definidos lá e não no componente (FR-030). Toda mensagem em pt-BR dizendo o que houve e a próxima ação (FR-012, FR-018, SC-008). Nenhum "em breve" — é exatamente por isso que a US3 fica bloqueada em vez de virar um botão morto (FR-031). |
| **VI. Rastro de Decisão Versionado** | ⚠ PASS com pendência herdada | `research.md`, `data-model.md`, `contracts/` e `quickstart.md` versionados junto ao código. **Pendência herdada da feature 001: o `README.md` continua não existindo.** Esta feature acrescenta setup novo (extensão `unaccent`, nova variável de ambiente do proxy), então o README passa a ter duas features de dívida. Criá-lo entra nas tarefas. |
| **VII. Isolamento da API Externa** | ✅ PASS | A busca consulta apenas o PostgreSQL. Nenhuma chamada ao TMDb no caminho de leitura, e nenhuma chave sai do back-end — o proxy do Next fala com o Django, não com o TMDb. SC-009 é verificável derrubando o TMDb e buscando. |

**Uma pendência herdada (README) e um bloqueio de sequenciamento (US3), ambos registrados.**
Nenhuma violação silenciosa.

## Project Structure

### Documentation (this feature)

```text
specs/002-site-header-navigation/
├── plan.md              # Este arquivo
├── spec.md              # Especificação da feature
├── research.md          # Fase 0 — decisões técnicas e alternativas descartadas
├── data-model.md        # Fase 1 — o que muda no modelo (pouco) e por quê
├── quickstart.md        # Fase 1 — habilitar a busca no ambiente já existente
├── contracts/
│   ├── search-api.md       # Contrato de GET /api/v1/busca/ (Django)
│   └── search-proxy.md     # Contrato de GET /api/busca (Route Handler do Next)
├── checklists/
│   └── requirements.md     # Checklist de qualidade do spec
└── tasks.md             # Fase 2 — gerado por /speckit-tasks (NÃO por /speckit-plan)
```

### Source Code (repository root)

Arquivos marcados com **[novo]** não existem hoje; os demais já existem e são alterados.

```text
backend/
├── config/settings/base.py        # + "django.contrib.postgres" em INSTALLED_APPS
├── apps/catalog/
│   ├── migrations/
│   │   └── 0002_unaccent_extension.py   # [novo] CREATE EXTENSION unaccent
│   ├── selectors.py               # + search_movies(termo, limite)
│   ├── serializers.py             # + SearchResultSerializer (projeção mínima)
│   ├── views.py                   # + SearchView (AllowAny, somente leitura)
│   └── urls.py                    # + path("busca/", ...)
└── tests/
    └── test_search_api.py         # [novo] contrato, acento, caixa, parcial,
                                   #        limite/truncated, acesso público,
                                   #        campos proibidos, filme inativo

frontend/
├── app/
│   ├── layout.tsx                 # + <SiteHeader/>, título com "ticket.com"
│   └── api/busca/route.ts         # [novo] proxy server-side para o Django
├── components/header/             # [novo]
│   ├── SiteHeader.tsx             # server component — monta os três elementos
│   ├── BrandMark.tsx              # wordmark "ticket.com" → "/"
│   ├── SearchBox.tsx              # client component — combobox, debounce, corrida
│   ├── SearchSuggestions.tsx      # listbox: resultados, vazio, erro, buscando
│   ├── AccountButton.tsx          # ícone de pessoa + dois estados (US3, bloqueada)
│   └── header.module.css
├── lib/
│   ├── api.ts                     # + fetchSearch(termo)
│   ├── types.ts                   # + SearchSuggestion, SearchResponse
│   └── search-client.ts           # [novo] fetch do navegador p/ /api/busca
├── styles/tokens.css              # + tokens de altura do cabeçalho e do painel de sugestões
└── tests/
    ├── header.test.tsx            # [novo] presença, wordmark, nome acessível do ícone
    ├── search.test.tsx            # [novo] debounce, corrida, teclado, 4 estados
    └── e2e/header.spec.ts         # [novo] cabeçalho nas páginas, busca → filme

.env.example                       # + nada obrigatório; documenta que o proxy usa API_BASE_URL
README.md                          # [novo] dívida herdada da 001, agora com setup do unaccent
```

**Structure Decision**: mantida a separação `backend/` + `frontend/` da feature 001. O cabeçalho
ganha diretório próprio (`components/header/`) em paralelo a `components/highlights/`, porque é
uma superfície global e não um pedaço da home — misturá-lo em `highlights/` amarraria o layout de
todas as páginas ao componente do carrossel. A lógica de busca vive em `selectors.py`, junto com a
elegibilidade ao destaque, para continuar testável sem HTTP.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **Route Handler do Next como proxy** (`app/api/busca/route.ts`) em vez de o navegador chamar o
   Django direto. É o que preserva a decisão já tomada em `lib/api.ts` e o que faz a busca
   funcionar dentro do Compose, onde `backend:8000` não resolve no navegador.
2. **Extensão `unaccent` do PostgreSQL** criada por migração, com `django.contrib.postgres` em
   `INSTALLED_APPS` para habilitar o lookup `title__unaccent__icontains`. Descartada a alternativa
   de manter uma coluna `title_normalizado` denormalizada, que exigiria backfill e um segundo
   ponto de verdade a manter sincronizado com o TMDb.
3. **Debounce de 250 ms + `AbortController` + guarda por número de requisição.** Só o abort não
   basta para FR-015: uma resposta já em trânsito pode chegar depois da mais nova. A guarda por
   sequência é o que torna SC-005 verdadeiro, e é o teste unitário mais importante da feature.
4. **Combobox do padrão WAI-ARIA 1.2 escrito à mão** — `role="combobox"` no input,
   `aria-expanded`, `aria-controls`, `aria-activedescendant` apontando para a opção em foco
   virtual, e uma região `aria-live="polite"` anunciando a contagem de resultados (FR-027).
   O foco do teclado nunca sai do input; as setas movem só o descendente ativo.
5. **Ordenação prefixo-primeiro**: quem começa com o termo vem antes de quem apenas o contém, e o
   desempate é por título — determinístico, para o teste não ficar instável (mesmo raciocínio do
   `get_highlighted_movies`).
6. **A busca devolve todos os filmes ativos, com ou sem sessão à venda.** É o que o spec manda no
   caso de borda: a busca não pode mentir sobre o catálogo, e quem comunica a indisponibilidade é
   a página do filme.
7. **Cabeçalho `position: sticky`**, não `fixed`: `sticky` reserva o próprio espaço no fluxo e não
   exige compensar o topo de cada página nem quebrar a impressão (FR-006).

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — a feature quase não toca o modelo: nenhuma entidade
  nova, nenhum campo novo. O que muda é uma extensão de banco e uma projeção de leitura. O
  documento registra por que `Localidade` **não** foi modelada e onde ela entraria.
- **[contracts/search-api.md](./contracts/search-api.md)** — `GET /api/v1/busca/`: parâmetros,
  payload, códigos de resposta, regra de truncamento e a lista de campos que **não** podem
  aparecer na resposta pública.
- **[contracts/search-proxy.md](./contracts/search-proxy.md)** — `GET /api/busca` no Next: o que
  o navegador pode ver, o que o proxy nunca repassa, e como uma falha do Django vira mensagem em
  pt-BR.
- **[quickstart.md](./quickstart.md)** — habilitar a extensão, rodar a migração e verificar a
  busca no ambiente que a feature 001 já deixou de pé.

### Post-Design Constitution Re-check

Reavaliado após o desenho acima: **nenhuma violação nova**. Quatro pontos a vigiar na
implementação:

- O `SearchResultSerializer` é uma projeção deliberadamente pobre (slug, título, pôster, ano).
  Reaproveitar `MovieDetailSerializer` por conveniência arrastaria sessões para uma resposta
  pública de busca e furaria o gate do Princípio IV.
- O Route Handler **não pode** repassar corpo de erro do Django ao navegador. Ele traduz para uma
  mensagem em pt-BR; detalhe de stack ou de rota interna fica no servidor.
- Nenhum token de cor ou espaçamento novo pode nascer dentro de `header.module.css`. Se falta um
  valor, ele é definido em `tokens.css` primeiro (Princípio V).
- `AccountButton` não decide nada sobre permissão. Ele lê um estado de autenticação e escolhe o
  que mostrar; qualquer regra de acesso continua no servidor (FR-025, Princípio IV).

## Complexity Tracking

> Um bloqueio de sequenciamento e uma dívida herdada. Nenhum é ampliação de escopo — são o
> oposto: o registro do que **não** está sendo entregue e por quê.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **US3 (ícone de conta) entregue desenhada mas bloqueada, não implementada** | O FR-022 (decisão do usuário em 2026-08-11) coloca login/logout na feature de autenticação, e o FR-023 proíbe que o ponto de acesso conduza a um destino inexistente. Não existe `/entrar`, não existe sessão, não existe estado autenticado para ler. Entregar o ícone hoje significa entregar um link para o nada. | Apontar o ícone para uma rota inexistente, para um `alert()` ou para uma página "em breve" seria trivial, mas o Princípio V proíbe explicitamente seção "coming soon" e o Princípio I proíbe tela pela metade. A alternativa oposta — puxar a autenticação inteira para dentro desta feature — contraria a decisão de escopo que o usuário tomou no `/speckit-specify` e transformaria um cabeçalho em duas features. **Consequência prática**: o cabeçalho vai ao ar com dois elementos, e o terceiro entra junto com a autenticação. `AccountButton.tsx` é escrito neste branch com seus dois estados e seus testes, mas só é montado no `SiteHeader` quando `/entrar` existir. |
| **Criar o `README.md` dentro de uma feature de cabeçalho** | O Princípio VI exige README com setup, credenciais de seed e variáveis de ambiente. Ele deveria ter nascido na feature 001 e não nasceu. Esta feature acrescenta um passo de setup novo (extensão `unaccent` no PostgreSQL): sem README, o avaliador não tem como saber que precisa rodar a migração nova. | Adiar de novo para "a próxima feature" foi exatamente o que produziu a dívida. Cada feature adiada acrescenta um passo de setup não documentado, e o Princípio VI diz que omissão impacta a avaliação negativamente enquanto a honestidade não impacta. |
