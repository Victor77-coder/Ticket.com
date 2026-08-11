# Implementation Plan: Trilhas de Filmes na Home

**Branch**: `main` (o projeto trabalha sem branches de feature) | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-home-movie-rows/spec.md`

## Summary

Preencher a home com três trilhas horizontais de cartazes — **Em cartaz**, **Em alta** e **Em
breve** — abaixo do painel de destaques já existente.

Duas decisões estruturam o trabalho. A primeira: **a classificação vem do TMDb, mas é persistida**
— o comando de sincronização passa a importar três listas em vez de uma e marca cada filme com o
que ele é, para que a home continue lendo apenas o banco. A segunda: **a trilha usa `scroll-snap`
nativo**, ao contrário do carrossel, porque aqui não há ciclo a fechar nem rotação automática — e
sem esses dois requisitos o CSS resolve gesto, inércia e acessibilidade melhor do que qualquer
código nosso.

A trilha Em cartaz não vem do TMDb: ela reusa a mesma regra de elegibilidade do carrossel, sem o
limite de 5.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 + DRF · Next.js 15 App Router — **nenhuma dependência nova**

**Storage**: PostgreSQL 16. Uma migração acrescenta a classificação de catálogo a `Movie`

**Testing**: `pytest` + `pytest-django` · Vitest + Testing Library · Playwright

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Project Type**: Web application (front-end + back-end separados)

**Performance Goals**: primeira trilha visível e navegável em ≤ 2 s (SC-007) · a home resolve as
três trilhas em uma única requisição ao back-end

**Constraints**: a home não chama o TMDb durante a visita · sem rolagem horizontal da página de
360px a 1920px · trilha vazia é omitida, nunca título órfão · Em alta limitada a 9

**Scale/Scope**: 3 trilhas, ~20 a 60 filmes no catálogo, escala de avaliação

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliado contra a Constitution v1.0.0.

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | Trilha vazia é omitida por inteiro (FR-006), não vira título sem conteúdo. Filme sem sessão tem página completa com data de estreia e explicação (FR-024 a FR-027) — nenhum card leva a beco sem saída. Carregando, vazio e erro entregues juntos. |
| **II. Integridade da Reserva** | ➖ N/A | Feature de leitura. Nenhuma escrita de assento. |
| **III. Ingresso Inforjável** | ➖ N/A | Nenhum ingresso emitido ou validado. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Tudo público e somente leitura. O mesmo gate das features anteriores se aplica ao endpoint novo: nenhuma sessão em rascunho, custo, capacidade ou identificação de usuário na resposta. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | Trilha desenhada com os tokens existentes. Cartaz ausente vira substituto legível, não retângulo cinza (FR-011). Nenhum texto genérico (FR-030). Controles de seta só aparecem quando há conteúdo além da borda — botão desabilitado permanente é ruído. |
| **VI. Rastro de Decisão Versionado** | ✅ PASS | Artefatos versionados. O README ganha a nova superfície e perde nada. |
| **VII. Isolamento da API Externa** | ✅ PASS | A classificação é importada pelo comando de sync e persistida (FR-020). A home lê só o banco (FR-021). Com o TMDb fora do ar as trilhas continuam completas (FR-022, SC-004). |

**Nenhuma violação sem justificativa.** Uma ampliação está registrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-home-movie-rows/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── home-api.md      # Contrato do endpoint das trilhas
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/catalog/
│   ├── models.py                     # ALTERADO — classificação de catálogo em Movie
│   ├── migrations/0003_*.py          # NOVO — os campos de classificação
│   ├── selectors.py                  # ALTERADO — seletores das três trilhas
│   ├── serializers.py                # ALTERADO — cartão de filme e resposta da home
│   ├── views.py                      # ALTERADO — HomeRowsView
│   ├── urls.py                       # ALTERADO — rota /api/v1/home/
│   └── services/
│       ├── tmdb_client.py            # ALTERADO — trending e upcoming
│       └── tmdb_sync.py              # ALTERADO — marca a classificação
├── apps/catalog/management/commands/
│   ├── sync_tmdb.py                  # ALTERADO — importa as três listas
│   └── seed_demo.py                  # ALTERADO — prefere filmes em cartaz com arte
└── tests/
    ├── test_home_rows_api.py         # NOVO — composição, limites, gate público
    └── test_tmdb_sync.py             # ALTERADO — classificação e sua expiração

frontend/
├── app/
│   ├── page.tsx                      # ALTERADO — carrossel + trilhas
│   └── filmes/[slug]/page.tsx        # ALTERADO — estreia e ausência de sessões
├── components/rows/
│   ├── MovieRow.tsx                  # NOVO — trilha com scroll-snap e controles
│   ├── MovieCard.tsx                 # NOVO — cartaz, título, link
│   ├── MovieRowSkeleton.tsx          # NOVO — mesma altura da trilha final
│   └── rows.module.css               # NOVO — tokens existentes
├── lib/
│   ├── api.ts                        # ALTERADO — fetchHomeRows
│   └── types.ts                      # ALTERADO — tipos de trilha e cartão
└── tests/
    ├── rows.test.tsx                 # NOVO — composição, teclado, vazio
    └── e2e/home-rows.spec.ts         # NOVO — percurso trilha → filme
```

**Structure Decision**: as trilhas ganham diretório próprio em `components/rows/` em vez de
entrarem em `components/highlights/`. São padrões visuais distintos — o painel de destaque é um de
cada vez com rotação; a trilha é muitos ao mesmo tempo sem rotação — e misturá-los levaria a um
módulo CSS com dois conjuntos de regras que só compartilham o nome do arquivo.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **`scroll-snap` nativo na trilha**, ao contrário do carrossel — aqui não há ciclo nem rotação
   automática, os dois motivos que levaram a escrever o carrossel à mão. Sem eles, o CSS entrega
   gesto, inércia e rolagem por teclado de graça e melhor.
2. **Classificação persistida em `Movie`** com dois campos booleanos e a data de atualização, em
   vez de tabela de coleção — a cardinalidade é fixa em três e nenhuma delas tem atributo próprio.
3. **Uma requisição para as três trilhas** (`GET /api/v1/home/`), não três — a home precisa das
   três juntas e três idas separadas só multiplicariam latência.
4. **Em cartaz reusa o seletor do carrossel** sem o limite de 5, o que garante a mesma promessa
   de compra em ambas as superfícies.
5. **`sync_tmdb` importa três listas** — em cartaz, em alta e estreias — e marca cada filme.
6. **Classificação expira**: um filme deixa de ser "em alta" quando some da lista da sincronização
   seguinte, e "em breve" é derivado da data de estreia, não congelado no momento do sync.
7. **Controles de seta só quando há transbordo**, detectado por observação de tamanho.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — os campos de classificação em `Movie`, a migração, e por
  que não há entidade nova.
- **[contracts/home-api.md](./contracts/home-api.md)** — `GET /api/v1/home/` com as três trilhas,
  a forma do cartão, o comportamento com trilha vazia e a lista de campos proibidos.
- **[quickstart.md](./quickstart.md)** — sincronizar, semear e verificar as três trilhas,
  incluindo o teste de resiliência à queda do TMDb.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Três pontos a vigiar na implementação:

- O serializer do cartão **não pode** ganhar campo de gestão. É o mesmo gate do Princípio IV que
  já vale para highlights e busca.
- A trilha Em cartaz precisa continuar honrando SC-003: todo filme listado tem sessão comprável.
  Se o seletor for relaxado por conveniência, a trilha vira promessa quebrada.
- `overflow-x` na trilha exige `min-width: 0` no contêiner pai dentro de grid ou flex, senão o
  transbordo vaza para a página e quebra SC-005. É a armadilha clássica desse padrão.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Alterar `seed_demo`, que pertence à feature 001 | Com catálogo real, o seed escolhe os 5 filmes por data de lançamento e trouxe um show de banda e um curta de 9 minutos para o carrossel. A trilha Em cartaz herda os mesmos filmes, então o problema aparece duas vezes na home. | Deixar como está seria mais barato, mas entrega ao avaliador uma vitrine de cinema sem filmes de cinema — contra o Princípio V, que cobra que a interface tenha escolha por trás. O ajuste é no critério de seleção, não na estrutura. |
