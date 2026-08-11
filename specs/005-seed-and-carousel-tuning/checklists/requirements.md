# Specification Quality Checklist: Ajuste da Vitrine — Seed e Carrossel

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Alignment

- [x] **I. Fluxo Completo** — nenhum comportamento do carrossel é removido; FR-003 exige que
  navegação circular, rotação, trailer e os três estados continuem valendo com 3 filmes.
- [x] **V. Interface Autoral** — é o princípio que motiva a feature. A vitrine passa a demonstrar
  escolha em vez de exibir o resultado bruto de uma ordenação por data.
- [x] **VI. Rastro de Decisão** — a fragilidade de fixar filmes por nome está registrada em
  Assumptions, com a mitigação exigida em FR-011.
- [x] **VII. Isolamento da API Externa** — nenhuma chamada nova ao TMDb; o seed opera sobre o
  catálogo já importado.

## Notes

### Por que uma feature nova em vez de emendar a 001

O limite do carrossel é FR-001 da `001-movie-highlights-carousel`, entregue e testada. Optei por
registrar a mudança aqui, apontando a emenda, em vez de reescrever a spec da 001 — assim o
histórico mostra **quando** e **por que** o número mudou, que é justamente o que o desafio pede
que o processo revele.

Difere do caso da 004, onde a emenda foi feita no lugar: lá o pedido do usuário foi explícito
("atualizar a spec existente, não criar nova feature").

### Verificação feita antes de escrever

Os quatro filmes nomeados foram conferidos no catálogo real: *Homem-Aranha: Um Novo Dia*,
*A Odisseia*, *Minions & Monstros* e *Moana* — todos presentes, com cartaz e arte, e três deles
já marcados como em alta. Sem isso, a spec estaria pedindo algo possivelmente impossível.

### O número que ficou como suposição

"Aumente o seed" não veio com quantidade. Assumi **cerca de 12** filmes com sessão, contra 5
hoje, e registrei em Assumptions. O número foi escolhido para resolver três coisas ao mesmo
tempo: dar substância à trilha Em cartaz, afastar a trilha Em alta de ser quase idêntica a ela
(problema levantado ao fim da 004), e fazer o carrossel de 3 parecer um recorte em vez da lista
inteira.

### Efeito colateral esperado, e bem-vindo

Três dos quatro filmes nomeados já estão marcados como em alta no catálogo. Como a trilha Em alta
passou a exigir sessão planejada (emenda da 004), dar sessão a eles deve fazer aquela trilha sair
de 3 filmes — todos duplicados de Em cartaz — para algo mais substancial. Não é objetivo desta
feature, mas é consequência direta e vale conferir na verificação.

### Decisão de desenho que evita complexidade

Moana ficar fora do carrossel **não** exige lista fixa nem campo de curadoria no produto. O
carrossel continua sendo "os N com sessão mais próxima"; é o seed que agenda os três destaques
antes dela. Toda a curadoria vive no cenário de demonstração, e nenhuma no código de produto.
