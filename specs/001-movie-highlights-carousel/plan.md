# Implementation Plan: Carrossel de Highlights de Filmes

**Branch**: `feat/add-carrossel-filmes` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-movie-highlights-carousel/spec.md`

## Summary

Entregar o carrossel de 5 filmes em destaque da home, com trailer reproduzido dentro do próprio
painel e botão que conduz à página do filme. Como esta é a primeira feature do repositório, o
plano também levanta a fundação mínima que ela exige: projeto Django + PostgreSQL na porta 5438,
importador do catálogo TMDb, modelos de Filme/Sessão, um endpoint público de leitura, e o app
Next.js servido na porta 5003.

A abordagem central é **desacoplar o TMDb do caminho de leitura**: um comando de sincronização
traz filmes, gêneros, classificação indicativa e a chave do trailer para o PostgreSQL; a home lê
apenas do banco. O TMDb pode cair sem afetar o carrossel — só a reprodução do trailer degrada.

O carrossel é construído sem biblioteca de terceiros. É a superfície mais visível do projeto e o
Princípio V exige que ela não seja a saída padrão de uma ferramenta; além disso, o controle total
sobre foco, rotação automática e semântica ARIA é mais barato de escrever do que de contornar em
uma lib genérica.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 LTS (front-end)

**Primary Dependencies**: Django 5.x + Django REST Framework · `httpx` (cliente TMDb) ·
`psycopg[binary]` · `django-environ` · Next.js 15 (App Router) + React 19 · sem biblioteca de
carrossel

**Storage**: PostgreSQL 16, exposto em `localhost:5438` (mapeado de 5432 no contêiner)

**Testing**: `pytest` + `pytest-django` (back-end) · Vitest + Testing Library (componentes) ·
Playwright para o percurso ponta a ponta do carrossel

**Target Platform**: Aplicação web. Front-end em `http://localhost:5003`, API Django em
`http://localhost:8000`, ambos em Docker Compose junto do banco.

**Project Type**: Web application (front-end + back-end separados)

**Performance Goals**: Primeiro painel legível em ≤ 2 s (SC-002) · trailer iniciando em ≤ 3 s
(SC-003) · endpoint de highlights respondendo em ≤ 150 ms com dados locais

**Constraints**: Porta do banco fixada em **5438** e porta da interface web fixada em **5003**
(exigência do usuário) · nenhuma chave TMDb pode chegar ao navegador · carrossel funcional sem
o TMDb no ar · layout utilizável de 360 px a 1920 px · sem rolagem horizontal indesejada

**Scale/Scope**: 5 painéis em destaque, ~20 filmes no catálogo semeado, escala de avaliação
(dezenas de acessos simultâneos), não de produção.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliado contra a Constitution v1.0.0.

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | Todos os estados do painel são entregues juntos: carregando, vazio, erro, sem trailer, esgotado (FR-021 a FR-024). O botão "Ver ingressos" tem destino real — a página de filme mínima entra neste escopo, ver Complexity Tracking. |
| **II. Integridade da Reserva** | ➖ N/A | Feature exclusivamente de leitura; não cria, reserva nem libera assento. **Restrição imposta**: nenhum código deste plano pode escrever ocupação de assento. A constraint `UNIQUE(sessão, assento)` pertence à feature de reserva e não é antecipada aqui. |
| **III. Ingresso Inforjável** | ➖ N/A | Não emite nem valida ingresso. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | `GET /api/v1/highlights/` é público e somente leitura, coerente com FR-019. Teste obrigatório: o endpoint responde sem autenticação **e** não expõe campo algum restrito ao organizador (custo, rascunho, sessão não publicada). |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | Carrossel próprio, sem lib. Tokens de cor/tipografia/espaçamento definidos uma vez em `tokens.css`. Toda mensagem de erro em pt-BR dizendo o que houve e a próxima ação (FR-024, SC-008). Estado do painel comunicado por forma e texto, não só por cor. |
| **VI. Rastro de Decisão Versionado** | ⚠ PASS com pendência | `research.md`, `data-model.md`, `contracts/` e `quickstart.md` versionados. **Pendência herdada**: o `README.md` do projeto ainda não existe e é exigido pelo Princípio VI — criá-lo faz parte desta feature, já que é ela quem introduz o setup (portas, `.env.example`, seed). |
| **VII. Isolamento da API Externa** | ✅ PASS | Chave TMDb só no back-end. Sincronização por comando de gerência persiste título, sinopse, arte, duração, gênero, classificação e chave do trailer. A home lê apenas o PostgreSQL. Timeout explícito e erro tratado no cliente TMDb. |

**Nenhuma violação sem justificativa.** Duas ampliações de escopo estão registradas em
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-movie-highlights-carousel/
├── plan.md              # Este arquivo
├── spec.md              # Especificação da feature
├── research.md          # Fase 0 — decisões técnicas e alternativas descartadas
├── data-model.md        # Fase 1 — entidades, campos, regras e migrações
├── quickstart.md        # Fase 1 — subir o ambiente do zero
├── contracts/
│   └── highlights-api.md   # Contrato do endpoint público de highlights
├── checklists/
│   └── requirements.md     # Checklist de qualidade do spec
└── tasks.md             # Fase 2 — gerado por /speckit-tasks (NÃO por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/
│   ├── settings/
│   │   ├── base.py           # DB em 5438, CORS para :5003, TMDB_API_KEY do ambiente
│   │   └── dev.py
│   ├── urls.py
│   └── asgi.py
├── apps/
│   ├── catalog/              # Filme, Gênero, Trailer + sincronização TMDb
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── selectors.py      # regra de elegibilidade ao destaque (FR-002)
│   │   ├── views.py          # HighlightsView (pública, somente leitura)
│   │   ├── urls.py
│   │   ├── services/
│   │   │   ├── tmdb_client.py    # único ponto que fala com o TMDb
│   │   │   └── tmdb_sync.py      # mapeia payload TMDb → modelos locais
│   │   └── management/commands/
│   │       ├── sync_tmdb.py      # importa catálogo
│   │       └── seed_demo.py      # 5 filmes + sessões + 4 usuários do desafio
│   └── screening/            # Sala, Sessão — mínimo para a elegibilidade
│       └── models.py
├── tests/
│   ├── test_highlights_api.py    # contrato, ordenação, limite 5, acesso público
│   ├── test_tmdb_sync.py         # mapeamento e resiliência a falha do TMDb
│   └── test_selectors.py         # regra de elegibilidade e desempate
├── pyproject.toml
└── manage.py

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  # home — renderiza o carrossel (server component)
│   └── filmes/[slug]/page.tsx    # destino de "Ver ingressos" (mínima, ver Complexity)
├── components/highlights/
│   ├── HighlightsCarousel.tsx    # estado de índice, rotação, teclado, gesto
│   ├── HighlightPanel.tsx        # arte, metadados, os dois botões
│   ├── TrailerFrame.tsx          # iframe montado sob demanda, desmontado ao fechar
│   ├── CarouselControls.tsx      # avançar, retroceder, indicadores
│   ├── HighlightsEmpty.tsx       # estado vazio em pt-BR (FR-022)
│   └── HighlightsSkeleton.tsx    # esqueleto de mesma altura (FR-021)
├── lib/
│   ├── api.ts                    # fetch server-side da API Django
│   └── types.ts
├── styles/tokens.css             # única fonte de cor, tipografia e espaçamento
├── tests/
│   ├── carousel.test.tsx         # navegação circular, pausa, movimento reduzido
│   └── e2e/highlights.spec.ts    # percurso home → trailer → ver ingressos
└── next.config.ts                # remotePatterns para image.tmdb.org

docker-compose.yml                # db:5438 · backend:8000 · frontend:5003
.env.example                      # sem segredo real
README.md                         # setup, credenciais de seed, uso de IA, limitações
```

**Structure Decision**: Web application com `backend/` e `frontend/` separados, refletindo a
stack obrigatória da constitution (Django + Next.js + PostgreSQL). O back-end é organizado por
domínio (`catalog`, `screening`) em vez de por camada técnica, para que a feature de reserva
possa crescer em `apps/booking/` sem tocar no catálogo. A lógica de elegibilidade ao destaque
vive em `selectors.py`, isolada da view, para ser testável sem HTTP.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **Carrossel próprio, track com `translateX`** — não usar biblioteca. Navegação circular
   (FR-008) fica trivial com índice modular; `scroll-snap` foi descartado por exigir clonagem de
   slides para fechar o ciclo.
2. **Trailer por montagem/desmontagem de `<iframe>` do `youtube-nocookie.com`** — o iframe só
   existe enquanto o trailer toca. Desmontar garante FR-014 e FR-016 sem depender da API
   JavaScript do YouTube, e evita carregar script de terceiro na abertura da home (FR-017).
3. **Classificação indicativa via `/movie/{id}/release_dates`**, filtrando `iso_3166_1 == "BR"`
   e tipo 3 (Theatrical). Confirmado na documentação do TMDb.
4. **Trailer via `/movie/{id}/videos`**, escolhendo `site == "YouTube"`, `type == "Trailer"`,
   `official == true`, preferindo `iso_639_1 == "pt"` e caindo para `"en"`.
5. **Leitura server-side no Next.js** — a home é server component e busca a API Django no
   servidor. Atende SC-002 e mantém a superfície de rede longe do navegador.
6. **Elegibilidade ao destaque** — filmes com ao menos uma sessão publicada e futura, ordenados
   pela sessão mais próxima, limitados a 5 (FR-002).

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — `Genre`, `Movie`, `Trailer`, `Room`, `Screening`, com
  campos, índices, regras de validação e a fronteira explícita com a feature de reserva.
- **[contracts/highlights-api.md](./contracts/highlights-api.md)** — contrato de
  `GET /api/v1/highlights/`: payload, códigos de resposta, comportamento com catálogo vazio, e a
  lista de campos que **não** podem aparecer na resposta pública.
- **[quickstart.md](./quickstart.md)** — subir banco, back-end e front-end nas portas fixadas,
  rodar a sincronização TMDb e o seed, e verificar o carrossel.

### Post-Design Constitution Re-check

Reavaliado após o desenho acima: **nenhuma violação nova**. Dois pontos a vigiar durante a
implementação:

- O serializer público **não pode** vazar `Screening.cost_price`, sessões em rascunho ou
  qualquer campo de gestão — é o que sustenta o gate do Princípio IV.
- `Screening` é introduzido aqui apenas com o necessário para a elegibilidade. Qualquer campo de
  ocupação de assento pertence à feature de reserva; adicioná-lo aqui violaria o Princípio II ao
  criar um caminho de escrita de assento sem a constraint que o protege.

## Complexity Tracking

> Duas ampliações além do enunciado literal da feature, ambas exigidas por princípios da
> constitution.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Introduzir os modelos `Room` e `Screening` em uma feature de carrossel | FR-002 define o destaque como "filme com sessão publicada e futura", e SC-004 exige que 100% dos destaques levem a uma sessão comprável. Sem sessão não há como decidir o que destacar. | Destacar simplesmente os 5 filmes mais recentes do TMDb dispensaria `Screening`, mas produziria destaques apontando para páginas sem nada à venda — exatamente a "tela pela metade" proibida pelo Princípio I. |
| Entregar uma página de filme mínima em `filmes/[slug]` | FR-018 exige que "Ver ingressos" leve a uma página com as sessões listadas. O spec exclui a página de detalhe completa do escopo, mas um botão para lugar nenhum viola o Princípio I. | Apontar o botão para uma rota inexistente ou para um "em breve" seria mais barato, mas o Princípio V proíbe explicitamente seção "coming soon" na entrega. A página fica limitada a: cartaz, título, sinopse e lista de sessões futuras — o detalhe completo e o mapa de assentos ficam para a feature de reserva. |
