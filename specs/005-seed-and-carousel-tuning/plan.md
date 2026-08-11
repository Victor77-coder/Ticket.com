# Implementation Plan: Ajuste da Vitrine — Seed e Carrossel

**Branch**: `main` (o projeto trabalha sem branches de feature) | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-seed-and-carousel-tuning/spec.md`

## Summary

Duas mudanças pequenas e independentes: o limite do carrossel cai de 5 para 3, e o seed passa a
colocar à venda quatro filmes nomeados mais um preenchimento até cerca de doze.

A descoberta que simplifica tudo: **o seed já agenda as sessões pela posição do filme na lista**.
`starts_at = agora + offset + 30min × índice` significa que quem está primeiro na lista tem a
sessão mais próxima — e o carrossel ordena exatamente por isso. Garantir A Odisseia, Homem-Aranha
e Minions no carrossel é, portanto, **ordenar a lista**, não criar lógica de curadoria. Nenhum
campo novo, nenhuma migração, nenhuma regra nova no código de produto.

## Technical Context

**Language/Version**: Python 3.12 (back-end). O front-end **não é tocado**.

**Primary Dependencies**: Django 5 + DRF — **nenhuma dependência nova**

**Storage**: PostgreSQL 16 — **nenhuma migração**

**Testing**: `pytest` + `pytest-django`

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Performance Goals**: nenhuma nova. O seed passa de ~15 para ~36 sessões, irrelevante no tempo
de execução de um comando manual.

**Constraints**: o seed continua idempotente · não pode falhar quando um filme nomeado não existe
· a busca por nome tolera acento, caixa e sufixo · o carrossel mantém todo comportamento entregue

**Scale/Scope**: 2 arquivos de produto, 3 de teste, o README. Nenhum arquivo novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliado contra a Constitution v1.0.0.

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | Nenhum comportamento removido. Navegação circular, rotação, trailer e os estados de carregando/vazio/erro continuam valendo com 3 painéis (FR-003) — e ganham teste com o número novo. |
| **II. Integridade da Reserva** | ➖ N/A | Nenhuma escrita de assento. O seed cria sessões, não reservas. |
| **III. Ingresso Inforjável** | ➖ N/A | Nenhum ingresso emitido. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Nenhum endpoint muda de forma nem de permissão. O seed continua criando os quatro usuários exigidos. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | É o princípio que motiva a feature: a vitrine passa a demonstrar escolha em vez de exibir o resultado bruto de uma ordenação por data. |
| **VI. Rastro de Decisão Versionado** | ✅ PASS | A fragilidade de fixar filmes por nome está registrada, com a mitigação exigida em FR-011. O README ganha a nova composição do seed. |
| **VII. Isolamento da API Externa** | ✅ PASS | Nenhuma chamada nova ao TMDb. O seed opera sobre o catálogo já importado — se um filme não foi sincronizado, ele simplesmente não é encontrado (FR-011). |

**Nenhuma violação.** Uma alteração em arquivo de outra feature está registrada em Complexity
Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-seed-and-carousel-tuning/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0
├── data-model.md        # Fase 1 — registra que NÃO há mudança de modelo
├── quickstart.md        # Fase 1
├── contracts/
│   └── highlights-limit.md   # A emenda ao contrato da feature 001
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/catalog/
│   ├── selectors.py                          # ALTERADO — HIGHLIGHTS_LIMIT 5 → 3
│   └── management/commands/seed_demo.py      # ALTERADO — filmes nomeados + volume
└── tests/
    ├── test_selectors.py                     # ALTERADO — o teste que fixa o limite em 5
    ├── test_highlights_api.py                # ALTERADO — idem, se afirmar 5
    └── test_seed_demo.py                     # NOVO — nomeados, ordem, degradação, idempotência

README.md                                     # ALTERADO — composição do seed
```

**Structure Decision**: nenhum arquivo de produto novo. O `seed_demo` já tem a forma certa —
`_pick_movies` escolhe e `_seed_screenings` agenda pela ordem. A mudança é **dentro** de
`_pick_movies`, que passa a colocar os nomeados na frente.

O `test_seed_demo.py` é novo porque o seed nunca teve teste próprio: até aqui era verificado
indiretamente, rodando o comando. Com regras de seleção e de ordem, passa a merecer teste.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **Ordenar, não fixar** — a posição na lista já determina o horário da sessão, e o carrossel
   ordena por sessão mais próxima. Colocar os três nomeados no início resolve, sem campo de
   curadoria nem lógica nova no produto.
2. **Busca por nome com `unaccent` + `icontains`**, que já existe no projeto desde a busca do
   cabeçalho — nenhuma dependência nova.
3. **Desempate determinístico** por `-release_date, pk`, com o título escolhido impresso na saída
   — duas execuções não podem produzir vitrines diferentes.
4. **12 filmes com sessão**, dos quais 4 nomeados e 8 do critério existente.
5. **Ausência é aviso, não falha** — um filme nomeado que não está no catálogo é reportado e o
   seed segue.
6. **O limite do carrossel é uma constante**, e mudá-la quebra dois testes que fixam 5. Atualizar
   os testes é parte da mudança, não regressão.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — registra explicitamente que **não há mudança de modelo**
  e por quê.
- **[contracts/highlights-limit.md](./contracts/highlights-limit.md)** — a emenda ao contrato de
  `GET /api/v1/highlights/` da feature 001: o `count` máximo passa de 5 para 3. A forma da
  resposta não muda.
- **[quickstart.md](./quickstart.md)** — sincronizar, semear e conferir a vitrine sem abrir o
  navegador.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Dois pontos a vigiar:

- **A ordem dos nomeados importa e é frágil na leitura.** Quem mexer em `_pick_movies` depois
  precisa saber que a posição na lista determina o carrossel. Sem comentário explicando isso, uma
  refatoração inocente — ordenar alfabeticamente, por exemplo — mudaria a vitrine sem que ninguém
  percebesse.
- **A trilha Em cartaz e o carrossel não podem convergir.** Com 12 filmes à venda e carrossel de
  3, a trilha tem quatro vezes mais conteúdo (SC-004). Se o volume do seed cair, esse critério é
  o primeiro a quebrar.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Alterar `HIGHLIGHTS_LIMIT` e os testes de `001-movie-highlights-carousel` | O pedido é exatamente esse: o carrossel passa a exibir 3. O limite é uma constante daquela feature e não há outro lugar onde mudá-lo. | Adicionar um segundo limite configurável seria generalização sem demanda — não existe caso em que o número precise variar em tempo de execução. |
