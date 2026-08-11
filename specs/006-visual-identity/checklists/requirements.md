# Specification Quality Checklist: Identidade Visual — Anti AI-Slop

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

- [x] **I. Fluxo Completo** — FR-018 exige que carregando, vazio, erro e cartaz ausente pareçam do
  produto; FR-021 proíbe placeholder e "em breve". Nenhum estado fica pela metade.
- [x] **V. Interface Autoral** — é o princípio que a feature inteira realiza. FR-023 a FR-025
  fecham a disciplina de tokens que o princípio exige.
- [x] **VI. Rastro de Decisão** — FR-012 e FR-022 obrigam a registrar a escolha tipográfica, sua
  licença e as decisões visuais não óbvias.
- [x] **VII. Isolamento da API Externa** — FR-010 exige fontes servidas pelo próprio produto,
  sem dependência de terceiro em tempo de visita. Coerente com o princípio, aplicado a fontes.

## Notes

### O problema real desta spec: tornar "anti-slop" testável

"Parece autoral" não é verificável. A spec resolve separando o que é objetivo do que é
julgamento:

**Automatizável** — ausência de valor solto (SC-001, SC-002), teto de três gestos (SC-004),
movimento cessando sob preferência reduzida (SC-005), paleta preservada, ausência de texto de
preenchimento (SC-010), testes existentes intactos (SC-008).

**Revisão humana com critério escrito** — apenas o SC-003, a atribuição da primeira dobra à
marca. Está isolado de propósito: um único critério subjetivo, com regra registrada, em vez de
uma spec inteira de intenções vagas.

### Decisão tomada com o usuário

Tipografia **Archivo Expanded + Archivo**, SIL OFL, escolhida entre três direções apresentadas
com mockup. O usuário justificou pela licença: OFL é mais inequívoca que a ITF Free Font License
num repositório público avaliado por terceiros.

A licença Fontshare foi verificada antes de ser oferecida — permite uso comercial e self-hosting,
proibindo apenas revenda dos arquivos. A alternativa era legítima; a escolha foi por margem de
segurança, não por impedimento.

### Achado da auditoria, antes da redação

Varredura nos arquivos de estilo encontrou a cor `#150703` literal em dois arquivos
(`highlights.module.css` e `entrar.module.css`), usada como texto sobre o botão laranja. É
violação do Princípio V que já existe no código entregue. Entrou no escopo por FR-024, em vez de
ficar como dívida silenciosa.

### Fronteira explícita com a feature 005

A 005 decidiu **qual conteúdo** aparece na vitrine — quais filmes, em que ordem. Esta decide
**como ele se parece**. A separação está no topo do spec porque as duas mexem na mesma tela e
seria fácil confundir depois, lendo o histórico.

### Risco que a spec assume

Uma feature só de refinamento visual pode virar reescrita disfarçada. Os FR-026 a FR-030 existem
para impedir isso: contratos, estrutura da home, acessibilidade e testes existentes ficam
congelados. Se a implementação precisar alterar uma asserção de teste, é sinal de que saiu do
escopo.
