# Specification Quality Checklist: Trilhas de Filmes na Home

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

- [x] **I. Fluxo Completo** — trilha vazia é omitida em vez de virar título órfão (FR-006);
  filme sem sessão tem página completa e explicação, não beco sem saída (FR-024 a FR-027).
- [x] **IV. Papéis e Autorização no Servidor** — N/A: todas as trilhas e a página do filme são
  públicas; nenhuma ação desta feature exige conta.
- [x] **V. Interface Autoral** — FR-030 proíbe texto genérico; FR-011 exige substituto legível em
  vez de retângulo vazio; FR-006 omite a trilha vazia em vez de deixar título órfão.
- [x] **VII. Isolamento da API Externa** — a home não consulta o catálogo externo durante a visita
  (FR-021) e as trilhas sobrevivem à sua queda (FR-022, SC-004).

## Notes

### O que a pesquisa da API mudou no pedido

O pedido previa um plano B: "se a api não fornecer, busque os filmes e derive se estão em cartaz
ou se sairão em breve". **Esse plano B não é necessário** — o catálogo externo classifica filmes
em alta da semana, em cartaz por região e com estreia futura por região, este último devolvendo
até a janela de datas considerada. Verificado na documentação antes da redação.

Consequência registrada no spec: os "9 filmes" que o pedido reservava como emergência viram
**limite de exibição** da trilha Em alta (FR-003), não fallback.

### Decisões tomadas com o usuário em 2026-08-11

1. **"Em cartaz" = comprável na plataforma**, não o "em exibição nos cinemas" do catálogo externo.
   Motivo: num site de ingressos, a trilha que promete compra não pode levar a filme sem sessão —
   e o painel de destaques já segue essa regra.
2. **Filme sem sessão leva à página normalmente**, com a composição completa, a data de estreia e
   a explicação. O usuário forneceu o texto de referência, incluindo a opção de pedir aviso.

### Escopo que cresceu e foi cortado

A resposta do usuário sobre o card introduziu o **pedido de aviso** ("Lembre-me"). Foi escrito
como US4 (P3) e depois **descartado por decisão do usuário em 2026-08-11**, quando a limitação
ficou explícita: o sistema registraria o interesse mas não entregaria aviso algum — não há envio
de e-mail nem notificação nesta entrega, e construí-los está fora do escopo do desafio.

Um botão que promete aviso e nunca avisa é a interface enganosa que o Princípio V veta, e seria
pior do que não ter o botão. Cortar foi a decisão certa: entregá-lo de verdade dobraria o escopo.

A US4 permanece, mas reduzida ao que sempre foi necessário — a página do filme sem sessão explicar
o motivo e a data de estreia, sem prometer nada.

### Sobreposição deliberada com o painel de destaques

O carrossel destaca 5 filmes compráveis; a trilha Em cartaz lista todos. Os cinco aparecem nas
duas superfícies. É intencional (FR-005, cenário 3 da US1) — suprimir a repetição faria o conteúdo
de uma trilha depender da ordem de renderização da outra, o que é mais difícil de entender e de
testar do que a repetição.
