# Specification Quality Checklist: Marca sem Laranja

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-12
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

- **Zero marcadores de clarificação.** O que normalmente exigiria pergunta — qual cor, qual fonte,
  qual desenho — é justamente o que esta feature existe para **decidir**, e a decisão pertence à
  fase de research (FR-040 a FR-042 a exigem registrada com as alternativas rejeitadas). Pedir a cor
  na spec inverteria a ordem: a spec fixa os **critérios** que a escolha precisa satisfazer, e são
  eles que tornam a escolha avaliável em vez de opinativa.

- **A spec não nomeia a cor de propósito, e isso não é vagueza.** Todo requisito de cor aqui é
  verificável sem saber qual ela é: contraste medido (FR-008, FR-009), ausência da antiga (FR-004),
  ausência de valor fora de token (FR-006), funcionamento nos quatro papéis (FR-007), e as
  proibições nomeadas (FR-011). Uma spec que dissesse "use âmbar" seria menos testável, não mais.

- **Verificado em 2026-08-12, e muda o tamanho da feature:** o laranja existe em **4 declarações**,
  todas em `frontend/styles/tokens.css`, e **12 arquivos** consomem apenas os nomes. A disciplina de
  tokens da 006 segurou por completo. É por isso que FR-005 fixa os nomes e as Assumptions explicam
  por que renomear seria pior — renomear obrigaria a tocar os doze consumidores e multiplicaria a
  chance de uma superfície ficar para trás.

- **A emenda tem endereço exato**, e está no preâmbulo: o FR-020 da 006 diz "a paleta DEVE
  permanecer escura com destaque laranja". Esta feature revoga a segunda metade e mantém a primeira.
  O item "Laranja de projeção" do contrato anti-slop da 006 é substituído, não apagado — sem
  sucessor, o único critério subjetivo da 006 ficaria sem regra escrita, que é o que aquele contrato
  existe para impedir.

- **FR-030, FR-031 e FR-029 são a proteção contra o dano colateral típico** de uma troca de paleta:
  assentos e desfechos que passam a depender só de cor, e um fundo de QR "harmonizado" com a marca.
  Os três já eram exigência de features anteriores; aqui viram requisito explícito porque é esta a
  feature que pode quebrá-los sem querer.

- **SC-008 e SC-009 dependem de julgamento humano**, e é deliberado: "parece template" não é
  automatizável. A resposta é a mesma da 006 — procedimento escrito e repetível, para que "não
  passou" venha com motivo. O restante dos critérios é varredura ou medição.

- Itens marcados incompletos exigiriam atualização da spec antes de `/speckit-clarify` ou
  `/speckit-plan`. Nenhum está incompleto.
