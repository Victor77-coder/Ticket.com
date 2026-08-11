---
description: "Task list for feature implementation"
---

# Tasks: Ajuste da Vitrine — Seed e Carrossel

**Input**: Design documents from `/specs/005-seed-and-carousel-tuning/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/highlights-limit.md](./contracts/highlights-limit.md)

**Tests**: Incluídos. O `seed_demo` nunca teve teste próprio — era verificado rodando o comando.
Com regras de seleção e de **ordem**, passa a merecer: a ordem é o mecanismo inteiro da feature
(R1) e quebra em silêncio.

**Organization**: Duas user stories, ambas P1. Nenhuma migração, nenhum arquivo de produto novo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (carrossel de 3), US2 (seed com filmes de verdade)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Back-end**: `backend/apps/catalog/`
- O front-end **não é tocado** — o indicador do carrossel lê `count` e se ajusta sozinho

---

## Phase 1: Setup

**Purpose**: A constante do carrossel, que é o menor pedaço independente

- [X] T001 Alterar `HIGHLIGHTS_LIMIT` de 5 para 3 em `backend/apps/catalog/selectors.py`, com comentário registrando que a mudança veio da feature 005

---

## Phase 2: Foundational

*Nenhuma tarefa.* Não há migração, modelo nem infraestrutura compartilhada a preparar — a feature
altera duas constantes e uma função. Registrado aqui de propósito: uma fase vazia é informação,
não omissão.

---

## Phase 3: User Story 1 — Carrossel com três filmes (Priority: P1) 🎯 MVP

**Goal**: O carrossel exibe no máximo 3 filmes, mantendo todo o comportamento entregue

**Independent Test**: Consultar `/api/v1/highlights/` com 8 filmes à venda e confirmar que o
`count` é 3; abrir a home e confirmar que o ciclo, a rotação e o trailer continuam funcionando

### Testes da User Story 1

- [X] T002 [P] [US1] Atualizar `test_limita_em_cinco_destaques` em `backend/tests/test_selectors.py` para fixar o limite em 3, renomeando a função — o nome antigo passaria a mentir
- [X] T003 [P] [US1] Atualizar a asserção de `count == 5` em `backend/tests/test_highlights_api.py` (linha ~132) para 3
- [X] T004 [P] [US1] Escrever em `backend/tests/test_highlights_api.py` o teste de que, com apenas 2 filmes à venda, o carrossel devolve 2 — o limite é teto, não piso (cenário 4 da US1)

### Implementação da User Story 1

*Nenhuma além da T001.* A mudança do limite é a implementação inteira desta story — o front-end
lê `count` e se ajusta sozinho, e a trilha Em cartaz não usa o limite.

**Checkpoint**: o carrossel exibe 3 e a suíte volta ao verde

---

## Phase 4: User Story 2 — Seed com filmes de verdade (Priority: P1)

**Goal**: O seed coloca à venda ~12 filmes, com A Odisseia, Homem-Aranha e Minions no carrossel e
Moana só na trilha

**Independent Test**: Rodar `sync_tmdb` e `seed_demo` em ambiente limpo e confirmar, pela saída
do comando, que os três destaques são os esperados e que Moana está à venda fora do carrossel

### Testes da User Story 2

- [X] T005 [P] [US2] Criar `backend/tests/test_seed_demo.py` com o teste de FR-004: os quatro filmes nomeados recebem sessão publicada e futura
- [X] T006 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-005 e SC-002: A Odisseia, Homem-Aranha e Minions são os três filmes com sessão mais próxima — **é o mecanismo inteiro da feature** (R1)
- [X] T007 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-006 e SC-003: Moana tem sessão e **não** está entre os três primeiros
- [X] T008 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-007 e SC-004: o seed coloca à venda mais filmes do que os quatro nomeados, ao menos o dobro do carrossel
- [X] T009 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-011 e SC-006: com um filme nomeado ausente do catálogo, o comando conclui sem erro e informa a ausência
- [X] T010 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-013 e SC-005: duas execuções seguidas produzem exatamente a mesma vitrine
- [X] T011 [P] [US2] Escrever em `backend/tests/test_seed_demo.py` o teste de FR-010: a busca encontra "homem aranha" em "Homem-Aranha: Um Novo Dia" e "minions" em "Minions & Monstros" — tolerando acento, caixa e sufixo

### Implementação da User Story 2

- [X] T012 [US2] Declarar os filmes nomeados e o volume alvo como constantes em `backend/apps/catalog/management/commands/seed_demo.py`, com a ordem dos três destaques explícita
- [X] T013 [US2] Implementar a busca por nome em `backend/apps/catalog/management/commands/seed_demo.py` usando `title__unaccent__icontains`, com desempate determinístico por `-release_date, pk` (R2)
- [X] T014 [US2] Alterar `_pick_movies` em `backend/apps/catalog/management/commands/seed_demo.py` para colocar os nomeados no início da lista, na ordem definida, e completar com o critério existente até o volume alvo
- [X] T015 [US2] Documentar em `backend/apps/catalog/management/commands/seed_demo.py`, com comentário no ponto exato, que **a posição na lista determina o carrossel** — sem isso uma refatoração inocente muda a vitrine em silêncio (R1)
- [X] T016 [US2] Implementar a degradação graciosa em `backend/apps/catalog/management/commands/seed_demo.py`: filme nomeado ausente vira aviso, nunca exceção (FR-011)
- [X] T017 [US2] Estender a saída do comando em `backend/apps/catalog/management/commands/seed_demo.py` para listar quais filmes ficaram no carrossel e quais entraram só na trilha (FR-014)
- [X] T018 [US2] Conferir em `backend/apps/catalog/management/commands/seed_demo.py` que 12 filmes × 3 sessões em 2 salas não colidem com `UNIQUE(sala, horário)`

**Checkpoint**: a vitrine é conferível pela saída do comando, sem abrir o navegador

---

## Phase 5: Polish

- [X] T019 Executar as verificações de `specs/005-seed-and-carousel-tuning/quickstart.md` com a aplicação no ar: carrossel com 3, Moana fora dele, trilha com o quádruplo, e duas execuções idênticas
- [X] T020 Percorrer o carrossel em `frontend/components/highlights/HighlightsCarousel.tsx` pela home confirmando que ciclo, rotação, pausa e trailer continuam funcionando com 3 painéis, e que o indicador mostra "1 / 3" (FR-003)
- [X] T021 [P] Atualizar `README.md` com a nova composição do seed — ~12 filmes à venda, três no carrossel — e as contagens de teste
- [X] T022 Medir o efeito real na trilha Em alta consultando `/api/v1/home/`, comparar com os 3 filmes totalmente duplicados de antes, e registrar o número em `specs/005-seed-and-carousel-tuning/quickstart.md` — era o problema levantado ao fim da feature 004

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: vazia
- **US1 (Phase 3)**: depende da T001
- **US2 (Phase 4)**: independente da US1 — pode ser feita antes, depois ou em paralelo
- **Polish (Phase 5)**: depende das duas stories

### User Story Dependencies

As duas stories são **genuinamente independentes**. A US1 mexe numa constante do seletor; a US2
mexe no comando de seed. Nenhuma lê o código da outra.

Só a verificação final (T019, T020) precisa das duas, porque é ali que a vitrine aparece inteira.

### Dependências pontuais

- T002 e T003 dependem da T001 (senão passam pelo motivo errado)
- T013 depende da T012
- T014 depende da T013
- T016 e T017 dependem da T014
- T019 depende da T017 e da T001
- T021 depende da T019

### Parallel Opportunities

- **US1**: T002, T003 e T004 em paralelo
- **US2**: T005 a T011 em paralelo — sete testes, arquivo único mas funções distintas
- **Cruzada**: a US1 inteira em paralelo com a US2, por não compartilharem arquivo
- **Polish**: T021 em paralelo com T019 e T020

---

## Parallel Example: User Story 2

```bash
# Os sete testes do seed, antes de qualquer implementação:
Task: "Filmes nomeados recebem sessão em backend/tests/test_seed_demo.py"
Task: "Os três destaques têm a sessão mais próxima em backend/tests/test_seed_demo.py"
Task: "Moana à venda fora do carrossel em backend/tests/test_seed_demo.py"
Task: "Volume acima do carrossel em backend/tests/test_seed_demo.py"
Task: "Filme ausente não quebra em backend/tests/test_seed_demo.py"
Task: "Duas execuções idênticas em backend/tests/test_seed_demo.py"
Task: "Busca tolera acento e sufixo em backend/tests/test_seed_demo.py"
```

---

## Implementation Strategy

### MVP

Não há MVP parcial aqui: são 22 tarefas pequenas, e as duas stories juntas levam menos tempo do
que separar a entrega. A ordem sugerida é a numérica.

Se for preciso parar no meio, a **US1 sozinha** é entregável — o carrossel passa a exibir 3, com
os filmes que o seed atual escolhe. A vitrine melhora só pela metade, mas nada fica quebrado.

### Entrega incremental

1. T001 + US1 → carrossel com 3, suíte verde
2. + US2 → a vitrine com os filmes certos
3. + Polish → verificação, README e o relato do efeito em Em alta

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- **Nenhuma migração, nenhuma dependência nova, nenhum arquivo de produto novo**
- **T015 é a tarefa que mais parece dispensável e menos é**: sem o comentário no ponto exato,
  quem refatorar `_pick_movies` depois — ordenando alfabeticamente por higiene, por exemplo —
  muda a vitrine sem perceber. A ordem da lista é o mecanismo inteiro (R1)
- **T002 e T003 não são regressão**: os testes codificavam o limite antigo. O commit precisa
  dizer isso, senão parece que a suíte quebrou
- T001 altera arquivo da feature 001 — justificado em Complexity Tracking do plan.md
- Commitar por contexto, com mensagem descritiva (Princípio VI)
