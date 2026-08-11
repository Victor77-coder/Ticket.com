---
description: "Task list for feature implementation"
---

# Tasks: Identidade Visual — Anti AI-Slop

**Input**: Design documents from `/specs/006-visual-identity/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/token-contract.md](./contracts/token-contract.md),
[contracts/anti-slop-review.md](./contracts/anti-slop-review.md)

**Tests**: **Nenhuma asserção nova de comportamento e nenhuma existente alterada.** O FR-030
congela os 95 testes de front-end de propósito — se um precisar mudar, a feature saiu do escopo
visual. O teste que não muda é, aqui, o instrumento de contenção.

A única exceção é um teste novo de movimento reduzido na trilha, porque R6 acrescenta um
movimento ali que a 004 não cobria.

**Organization**: Quatro user stories, na **ordem mandatória** do pedido: ritmo → tipografia →
movimento → checagem. Nenhuma migração, nenhum endpoint, nenhum arquivo de produto novo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (ritmo), US2 (tipografia), US3 (movimento), US4 (identidade)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **Tokens**: `frontend/styles/tokens.css` — o núcleo da feature
- **Consumidores**: 5 módulos CSS com 329 referências a token no total
- **O back-end não é tocado**

---

## Phase 1: Setup

**Purpose**: A varredura antes de mexer, para saber de onde se parte

- [X] T001 Executar os quatro comandos de varredura de `specs/006-visual-identity/contracts/token-contract.md` e registrar a saída inicial — é a linha de base contra a qual o SC-001 será medido no fim
- [X] T002 Registrar em `specs/006-visual-identity/quickstart.md` a contagem atual de asserções de front-end, para provar depois que nenhuma mudou (FR-030)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: A fonte carregada e os tokens novos declarados — tudo depende disto

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar

- [X] T003 Carregar Archivo como fonte variável em `frontend/app/layout.tsx` via `next/font/google`, declarando o eixo `wdth` e expondo como variável CSS (R2)
- [X] T004 Confirmar em `frontend/app/layout.tsx` que a fonte é servida pelo próprio domínio, sem requisição a terceiro em tempo de visita (FR-010, Princípio VII)
- [X] T005 Substituir `--fonte-base` em `frontend/styles/tokens.css` pela variável gerada, mantendo pilha de reserva (FR-007, FR-009)
- [X] T006 Declarar os tokens novos de tipografia em `frontend/styles/tokens.css`: `--texto-display`, `--largura-display`, `--largura-normal`, `--peso-display`, `--espacamento-display` (data-model.md)
- [X] T007 Declarar `--cor-sobre-destaque` em `frontend/styles/tokens.css` e substituir a cor literal `#150703` em `frontend/components/highlights/highlights.module.css` e `frontend/app/entrar/entrar.module.css` — dívida herdada, R10
- [X] T008 Verificar que nenhum nome de token existente foi removido ou renomeado, conferindo contra a lista congelada de `specs/006-visual-identity/contracts/token-contract.md`

**Checkpoint**: a fonte carrega e os tokens existem; nada mudou de aparência ainda

---

## Phase 3: User Story 1 — Ritmo e hierarquia (Priority: P1) 🎯 MVP

**Goal**: A home tem hierarquia vertical legível: a dobra domina, as trilhas se organizam abaixo

**Independent Test**: Abrir a home e confirmar que o espaço entre o carrossel e a primeira trilha
é visivelmente maior que entre trilhas, e que os títulos de seção se distinguem por peso e escala

### Implementação da User Story 1

- [X] T009 [US1] Declarar `--ritmo-dobra` e `--ritmo-secao` em `frontend/styles/tokens.css`, com valores fluidos e distintos entre si (R4, FR-001)
- [X] T010 [US1] Reescrever a escala tipográfica em `frontend/styles/tokens.css` com razão 1,25, ajustando `--texto-sm`, `--texto-xl` e `--texto-2xl` (R3)
- [X] T011 [US1] Ajustar `--peso-forte` para 600 e introduzir `--peso-display` 700 em `frontend/styles/tokens.css` — 700 em texto de interface fica pesado ao lado de um display expandido (data-model.md)
- [X] T012 [US1] Aplicar `--ritmo-dobra` entre o painel de destaques e a primeira trilha em `frontend/app/page.tsx`
- [X] T013 [US1] Aplicar `--ritmo-secao` entre trilhas consecutivas em `frontend/components/rows/rows.module.css`
- [X] T014 [US1] Ajustar o peso e a escala dos títulos de seção em `frontend/components/rows/rows.module.css`, distinguindo do corpo por peso e escala, não por cor (FR-002)
- [X] T015 [US1] Ajustar a densidade dos cartazes em `frontend/components/rows/rows.module.css`: largura maior, espaçamento menor, proporção 2:3 mantida (R8, FR-003)
- [X] T016 [US1] Remover a borda e o fundo circular das setas em `frontend/components/rows/rows.module.css`, ancorando à linha de base do título — **sem alterar a regra de quando aparecem** (R7, FR-004)
- [X] T017 [US1] Conferir que o ritmo se mantém proporcional de 360px a 1920px em `frontend/components/rows/rows.module.css` (FR-006, SC-011)
- [X] T018 [US1] Verificar que a primeira dobra não ganhou cartão decorativo, chip, selo nem sobreposição além do véu, em `frontend/components/highlights/highlights.module.css` (FR-005)

**Checkpoint**: a home tem ritmo — a base sobre a qual tipografia e movimento se apoiam

---

## Phase 4: User Story 2 — Tipografia autoral (Priority: P2)

**Goal**: O título do destaque tem presença de cartaz; nenhum texto usa fonte do sistema

**Independent Test**: Abrir a home e confirmar que o título do filme é largo e pesado, e que a
varredura por `font-family` fora dos tokens não retorna nada

### Implementação da User Story 2

- [X] T019 [US2] Aplicar o tratamento de display ao título do filme em `frontend/components/highlights/highlights.module.css`, usando `--texto-display`, `--peso-display` e `--largura-display` via `font-variation-settings` (FR-008)
- [X] T020 [US2] Aplicar `--largura-normal` ao corpo de texto em `frontend/styles/tokens.css`, para que o eixo de largura não vaze do display (R1)
- [X] T021 [US2] Verificar que o título longo continua legível e não estoura o painel nem invade os botões, em `frontend/components/highlights/highlights.module.css` (edge case)
- [X] T022 [US2] Verificar que o título curto não fica perdido no espaço do painel, em `frontend/components/highlights/highlights.module.css` (edge case)
- [X] T023 [US2] Executar a varredura por `font-family` sobre `frontend/components` e `frontend/app` e confirmar saída vazia (SC-002)
- [X] T024 [US2] Verificar a ausência de salto de layout ao carregar a fonte definida em `frontend/app/layout.tsx`, com cache desativado (SC-006, FR-011)

**Checkpoint**: a tipografia é reconhecível como escolha, não como padrão de framework

---

## Phase 5: User Story 3 — Microdetalhe e movimento (Priority: P3)

**Goal**: Três gestos de movimento, suaves, que cessam sob preferência reduzida

**Independent Test**: Percorrer cartaz, carrossel e trilha confirmando resposta em cada um;
ativar movimento reduzido e confirmar que todos cessam

### Testes da User Story 3

- [X] T025 [P] [US3] Escrever em `frontend/tests/rows.test.tsx` o teste de movimento reduzido na trilha — **é o único teste novo da feature**, porque R6 acrescenta um movimento que a 004 não cobria

### Implementação da User Story 3

- [X] T026 [US3] Declarar `--movimento-cartaz`, `--elevacao-cartaz` e `--curva-saida` em `frontend/styles/tokens.css` (data-model.md)
- [X] T027 [US3] Polir a elevação do cartaz ao ponteiro em `frontend/components/rows/rows.module.css`, animando **apenas** `transform`, com resposta na entrada e na saída (FR-013, R6)
- [X] T028 [US3] Ajustar a curva da transição de painel do carrossel em `frontend/components/highlights/highlights.module.css`, mantendo o comportamento de ciclo intacto (FR-014)
- [X] T029 [US3] Ajustar o deslocamento da trilha em `frontend/components/rows/rows.module.css` para parar de forma previsível (FR-014)
- [X] T030 [US3] Reescrever o brilho do esqueleto em `frontend/components/rows/rows.module.css` para animar `transform` em vez de `background-position` — hoje repinta a área inteira em loop durante o carregamento (R6)
- [X] T031 [US3] Aplicar a mesma reescrita ao esqueleto em `frontend/components/highlights/highlights.module.css` (R6)
- [X] T032 [US3] Refinar os estados de vazio, erro e cartaz ausente em `frontend/components/rows/rows.module.css` e `frontend/components/highlights/highlights.module.css` para parecerem do produto (FR-018)
- [X] T033 [US3] Garantir que todos os gestos cessam sob `prefers-reduced-motion` em `frontend/styles/tokens.css` e nos módulos, sem exigir recarga (FR-016, SC-005)
- [X] T034 [US3] Executar a varredura por propriedades proibidas em animação sobre `frontend/components` e `frontend/app` e confirmar saída vazia (R6)
- [X] T035 [US3] Contar os gestos de movimento em `frontend/components/**/*.module.css` e confirmar que são no máximo três (FR-015, SC-004)

**Checkpoint**: a interface responde sem chamar atenção

---

## Phase 6: User Story 4 — Checagem de identidade (Priority: P4)

**Goal**: A primeira dobra sem logotipo é atribuível a esta marca

**Independent Test**: Capturar a primeira dobra, recortar o cabeçalho, aplicar os critérios de
`contracts/anti-slop-review.md`

- [ ] T036 [US4] ⏸️ **REQUER O USUÁRIO** — Capturar a primeira dobra em 1440×900 com o catálogo semeado, recortar o cabeçalho inteiro e aplicar as duas listas de `specs/006-visual-identity/contracts/anti-slop-review.md`
- [ ] T037 [US4] ⏸️ **REQUER O USUÁRIO** — Responder por escrito a pergunta final do `contracts/anti-slop-review.md` e registrar o resultado — se falhar, abrir tarefa de correção dentro do escopo visual
- [X] T038 [US4] Confirmar que a paleta permanece escura com laranja, sem roxo, creme com serifada nem brilho excessivo, conferindo `frontend/styles/tokens.css` (FR-020)
- [X] T039 [US4] Executar a varredura por texto de preenchimento em `frontend/app` e `frontend/components` e confirmar saída vazia (SC-010, FR-021)

---

## Phase 7: Polish & verificação final

- [X] T040 Executar `npm run test` e confirmar as mesmas asserções passando **sem nenhuma edição** — se uma falhou, a feature atravessou para comportamento (FR-030, SC-008)
- [X] T041 [P] Executar `pytest` e confirmar que o back-end permanece intacto
- [X] T042 [P] Verificar operação por teclado e foco visível na home servida por `frontend/app/page.tsx`, confirmando que o refino não tornou o foco sutil (FR-028)
- [X] T043 [P] Medir o contraste do título e dos botões sobre os véus definidos em `frontend/styles/tokens.css`, confirmando nível igual ou melhor que a baseline (SC-007)
- [X] T044 Executar os quatro comandos de `specs/006-visual-identity/contracts/token-contract.md` e confirmar saída vazia nos quatro, comparando com a linha de base da T001 (SC-001, SC-002)
- [X] T045 [P] Registrar em `README.md` a tipografia escolhida, sua licença e por que não a fonte do sistema (FR-012, SC-009)
- [X] T046 [P] Registrar em `README.md`, na seção de decisões, o ritmo em dois níveis e o teto de três gestos (FR-022)
- [X] T047 Percorrer os sete princípios da constitution contra a aplicação rodando e registrar desvios nas limitações conhecidas do `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — mede o ponto de partida
- **Foundational (Phase 2)**: depende da Phase 1 — **BLOQUEIA todas as user stories**
- **US1 → US2 → US3 → US4**: a ordem é **mandatória**, definida pelo usuário
- **Polish (Phase 7)**: depende de todas

### Por que a ordem é sequencial, não paralela

Diferente das features anteriores, as stories aqui **não** são independentes:

- A **US2** precisa do ritmo da US1 para calibrar as escalas tipográficas — ajustar fonte numa
  página sem ritmo só troca o tipo do problema.
- A **US3** polir movimento antes de tipografia e ritmo estarem certos seria refinar o que ainda
  vai mudar.
- A **US4** é checagem, não construção: só faz sentido depois das três.

### Dependências pontuais

- T005 depende de T003
- T009 a T011 alteram o mesmo arquivo — sequenciais
- T012 depende de T009
- T019 depende de T006 e T010
- T027 e T030 dependem de T026
- T036 depende de toda a US3
- T044 compara com T001

### Parallel Opportunities

Poucas, e é consequência do desenho: quase tudo passa por `tokens.css`, que é arquivo único.

- **US3**: T025 em paralelo com a implementação
- **Phase 7**: T041, T042, T043, T045 e T046 em paralelo

---

## Implementation Strategy

### MVP

A **US1 sozinha** é entregável e já melhora a home de forma perceptível — ritmo é o que mais
transforma a leitura de uma página. Mas o pedido é a identidade completa, e parar na US1 deixaria
a fonte do sistema, que é o traço mais genérico de todos.

O menor recorte que cumpre o Princípio V é **US1 + US2**: ritmo e tipografia.

### Entrega incremental

1. Setup + Foundational → a fonte carrega, nada mudou ainda
2. + US1 → a home ganha hierarquia
3. + US2 → a tipografia deixa de ser do sistema (**menor recorte que cumpre o princípio**)
4. + US3 → a interface responde
5. + US4 → a checagem confirma, ou aponta o que corrigir
6. + Polish → verificação, README e a revisão da constitution

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- **Nenhuma migração, nenhuma dependência nova, nenhum arquivo de produto novo**
- **T007 é dívida herdada**, não parte do refino: a cor `#150703` já violava o Princípio V no
  código entregue. Sem corrigi-la, a varredura do SC-001 não teria autoridade
- **T030 e T031 não são cosméticos**: o brilho do esqueleto anima `background-position` hoje,
  repintando a área inteira em loop justamente durante o carregamento
- **T040 é o gate da feature**: se uma asserção precisou mudar, a mudança visual atravessou para
  comportamento e o escopo foi rompido (FR-030)
- **T037 pode falhar** — e falhar é resultado legítimo. Uma checagem que nunca reprova é teatro
- Commitar por contexto, com mensagem descritiva (Princípio VI)

---

## Estado final — 2026-08-11

**45 de 47 concluídas.** As duas pendentes são a checagem de identidade (T036, T037), que exige
capturar a tela e julgar a imagem — não é automatizável e não pode ser feita por quem não vê o
resultado renderizado.

O roteiro está pronto em `contracts/anti-slop-review.md`: capturar a primeira dobra em 1440×900,
recortar o cabeçalho, aplicar as duas listas e responder à pergunta final.

Tudo o que era verificável foi verificado:

| Critério | Resultado |
|---|---|
| SC-001 valores soltos | 0 (eram 12 na linha de base) |
| SC-002 `font-family` fora dos tokens | 0 |
| SC-004 gestos de navegação | 3 |
| SC-007 contraste sobre o véu | 18,0:1 e 8,5:1 — véu inalterado |
| SC-008 asserções congeladas | 95 originais intactas, 2 novas |
| SC-010 texto de preenchimento | 0 |
| Propriedades proibidas em animação | 0 |
