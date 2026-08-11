# Specification Quality Checklist: Escolha de Assentos

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

- [x] **I. Fluxo Completo** — sessão esgotada, lugar recém-tomado, sessão cancelada e reserva
  vencida têm cada um mensagem própria (FR-030). O caminho termina em handoff explícito para o
  pagamento (FR-028), não em beco sem saída.
- [x] **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** — é o princípio que esta feature realiza.
  FR-016 exige a garantia **no banco**, FR-017 a transação com bloqueio, FR-018 a atomicidade da
  reserva, e o SC-002 é o teste de concorrência que a constitution torna obrigatório.
- [x] **III. Ingresso Inforjável** — N/A e explicitamente fora de escopo (FR-029). Nenhum ingresso
  é emitido aqui.
- [x] **IV. Papéis e Autorização no Servidor** — FR-024 a FR-027. A recusa por papel acontece no
  servidor, e FR-025 diz com todas as letras que esconder o botão não conta.
- [x] **V. Interface Autoral** — FR-008 proíbe distinguir estado só por cor; FR-031 proíbe texto
  genérico; FR-035 mantém a disciplina de tokens da 006.
- [x] **VI. Rastro de Decisão** — as cinco suposições e a limitação da demonstração estão
  registradas com o motivo.
- [x] **VII. Isolamento da API Externa** — FR-032 e SC-010: o mapa funciona com o TMDb fora do ar,
  porque sala, sessão e lugares são dados locais.

## Notes

### Esta é a feature que a constitution vinha esperando

Desde a `001`, `backend/apps/screening/models.py` carrega um aviso escrito: nenhuma escrita de
ocupação de assento entra sem a constraint que a protege. Quatro features passaram por perto e
respeitaram a fronteira — a `004` chegou a criar `seats_taken` como propriedade derivada
justamente para não materializar ocupação.

Esta é a feature que cria o modelo **e** a constraint juntos. Separá-los, mesmo por um commit, é
o que o Princípio II proíbe.

### O quarto estado precisou de decisão do usuário

O pedido listava quatro estados do assento, mas **"indisponível" não tinha significado no modelo**:
`Room` só tem `capacity`, e as capacidades semeadas (60 e 40) preenchem uma grade de 10 colunas
exata, sem sobra. Um estado que nunca ocorre não é testável e não deveria estar na spec.

Levado ao usuário com três leituras. Escolhida: **assentos de acessibilidade**, três por sala na
última fileira, marcados e fora da venda comum. Convenção de sala real, estado testável, e
profundidade honesta em vez de inventada.

### Uma limitação que o usuário escolheu conscientemente

Prazo de reserva fixo em 10 minutos. Ofereci a alternativa de torná-lo configurável por ambiente,
para que o avaliador pudesse encurtar para segundos e **ver** o assento voltar ao estoque. O
usuário preferiu o fixo.

Consequência registrada no spec e destinada ao README: a expiração fica provada por **teste**, não
por demonstração. Quem avaliar vai ler o teste, não assistir ao comportamento.

### A decisão que evita uma janela de inconsistência

A liberação por vencimento é **por consulta**, não por rotina agendada. Um lugar cuja reserva
venceu conta como livre no instante do vencimento.

Uma tarefa periódica que varresse reservas vencidas criaria uma janela — entre o vencimento e a
próxima varredura — em que o lugar está livre por direito mas aparece tomado. Derivar da consulta
elimina a janela e a rotina.

### Onde a spec deliberadamente não decide

Como a garantia de FR-016 é expressa no esquema — coluna denormalizada, constraint composta,
índice parcial — é decisão do plano, não da spec. O que a spec fixa é o **comportamento**: o mesmo
lugar da mesma sessão nunca tomado duas vezes, imposto pelo banco.

Isso importa porque a forma da constraint tem alternativas legítimas, e escolher aqui seria
decidir implementação antes de pesquisar.
