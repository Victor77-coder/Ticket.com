# Specification Quality Checklist: Cartão de Sessão e Meia-Entrada

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

## Content Quality

- [~] No implementation details (languages, frameworks, APIs) — **desvio deliberado**, ver Notas
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

**Sobre o desvio de "no implementation details":** o preâmbulo e as dependências citam a constraint
`UNIQUE(sessão, assento)` e o teste de concorrência do pagamento pelo nome. Isso é implementação, e
está lá de propósito — é a house style das specs 007 a 013 deste projeto, onde o valor de uma spec
nova é justamente dizer **qual garantia existente ela não pode quebrar**. Uma spec desta feature que
não nomeasse o cálculo do total protegido por teste concorrente esconderia o único risco real dela.
Os requisitos numerados (FR) permanecem livres de tecnologia.

**Duas decisões foram tomadas com o autor antes de escrever**, e não sobraram como marcadores:

1. **Meia-entrada é comprável**, não apenas informativa. O autor escolheu essa opção depois de ver
   o custo de cada uma — a alternativa informativa não tocaria em modelo nem em pagamento. A escolha
   está registrada aqui porque é ela que torna a P3 a história mais cara da feature.
2. **O painel de assentos é somente leitura.** A alternativa — selecionar dentro do painel — criaria
   um segundo caminho de reserva ao lado do mapa da 007.

**Riscos que o planejamento precisa endereçar**, não defeitos da spec:

- A FR-019 e a FR-020 mexem no cálculo do total, hoje coberto por `test_payment_concurrency.py`. O
  plano precisa manter esse teste válido e estendê-lo com tipos mistos (SC-007).
- A FR-024 é a fronteira mais fácil de violar sem perceber: exibir o tipo ao operador é permitido,
  transformá-lo em condição de entrada não é. A constitution exige exatamente quatro desfechos.
- A FR-018 (arredondamento para baixo) precisa de decisão registrada no data-model sobre onde o
  valor por lugar é gravado, para que exibido e cobrado nunca divirjam.

**Corte de escopo previsto**: P1+P2+P3 (cartão e os dois painéis) entregam o pedido visual completo
sem a P4. Se o prazo apertar, a P4 sai inteira e nenhuma tela fica pela metade.
