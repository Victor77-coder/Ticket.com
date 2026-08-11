# Specification Quality Checklist: Cabeçalho Global do Site

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

## Notes

**Iteração 1 — 2026-08-11**: três marcadores [NEEDS CLARIFICATION] abertos (formato dos
resultados de busca, efeito da localidade, extensão do fluxo de conta) e o item
"Scope is clearly bounded" reprovado por dependerem dessas respostas.

**Iteração 2 — 2026-08-11**: as três decisões foram tomadas pelo usuário e incorporadas ao
spec; todos os itens passam.

- **Busca** → sugestões ancoradas ao campo dentro do cabeçalho, sem página de resultados
  (FR-009 a FR-011).
- **Localidade** → removida da entrega. O domínio não representa praça nem cinema (`Room`
  existe sem lugar), e um seletor que não altera nada na tela violaria o Princípio V da
  constitution. Registrada em Assumptions como adiada, não como esquecida.
- **Conta** → apenas o ponto de acesso e seus dois estados; login/logout ficam com a feature
  de autenticação (FR-022).

**Ponto de atenção para o `/speckit-plan`**: FR-023 proíbe que o ícone de conta conduza a um
destino inexistente, e a seção Dependencies registra que a US3 só fecha quando a feature de
autenticação entregar o caminho de entrada. O plano precisa decidir a ordem — entregar US1 e
US2 primeiro e a US3 junto com a autenticação, ou puxar a autenticação para antes. Não é uma
lacuna do spec, é uma escolha de sequenciamento.

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
