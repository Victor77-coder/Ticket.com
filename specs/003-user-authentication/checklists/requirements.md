# Specification Quality Checklist: Autenticação e Acesso à Conta

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

- [x] **I. Fluxo Completo** — entrar e sair são ambos P1; login sem logout seria beco sem saída.
  Expiração de sessão tem comportamento definido (FR-017), não é caso omitido.
- [x] **IV. Papéis e Autorização no Servidor** — FR-022 é explícito: o papel exposto à interface
  escolhe o que apresentar, nunca concede acesso. FR-023 proíbe vazamento de credencial.
- [x] **V. Interface Autoral** — FR-026 proíbe distinguir os estados só por cor; FR-027 exige
  mensagem que diga o que houve e a próxima ação. Nenhum ícone novo: reusa o que a 002 desenhou.
- [x] **VI. Rastro de Decisão** — as duas decisões de escopo estão em Assumptions com data e
  origem.

## Notes

### Descoberta que redefiniu a feature

O pedido foi "adicione o ícone de login no header". O ícone **já existe**:
`frontend/components/header/AccountButton.tsx`, entregue pela feature 002 com o desenho próprio e
testes. Ele não está montado porque o FR-023 daquela feature proíbe conduzir a destino
inexistente, e as tarefas T037/T038 estão marcadas `🚧 NÃO EXECUTAR AINDA`.

Esta feature entrega o destino e monta o que existe. Não redesenha ícone. O SC-009 amarra isso:
a feature só está completa quando T037 e T038 da 002 estiverem concluídas.

### Decisões tomadas com o usuário

Ambas confirmadas em 2026-08-11 antes da redação:

1. **Sem auto-cadastro** — as quatro contas do seed são as únicas. O desafio não pede criação de
   conta e exclui recuperação de senha.
2. **Retorno único para todos os papéis** — nenhuma landing por papel. Criar três telas quase
   vazias agora contrariaria o Princípio V, que proíbe "em breve" na entrega.

### Requisitos de segurança tratados como comportamento, não como implementação

FR-004 (mensagem idêntica para os três motivos de falha), FR-007 (limite de tentativas), FR-011
(retorno só para endereços internos), FR-018 (identificador de sessão fora do alcance de scripts)
e FR-019 (proteção contra requisição forjada) são escritos como comportamento observável, com
critérios de sucesso verificáveis em SC-005 e SC-006 — sem nomear mecanismo, cookie ou biblioteca.

### Dependência não resolvida no momento da redação

A feature `002-site-header-navigation` está **42/44 concluída e sem commit** na árvore de
trabalho. O plano desta feature deve assumir que ela será commitada antes; se for revertida ou
alterada, FR-024 a FR-026 e o SC-009 precisam ser revistos.
