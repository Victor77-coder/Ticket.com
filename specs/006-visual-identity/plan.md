# Implementation Plan: Identidade Visual — Anti AI-Slop

**Branch**: `main` (o projeto trabalha sem branches de feature) | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-visual-identity/spec.md`

## Summary

Refinar a linguagem visual sem tocar comportamento. Três frentes, na ordem mandatória do pedido:
ritmo vertical, tipografia, movimento — e depois uma checagem de identidade.

A descoberta que simplifica a maior das três: **Archivo é fonte variável com eixo de largura**.
O "Archivo Expanded" do display sai do **mesmo arquivo** que o texto, via `wdth`, em vez de uma
segunda família. Um download, coerência garantida por construção, e a distinção display/texto
passa a ser um eixo tipográfico em vez de duas vozes a casar.

O restante é disciplina de tokens: cada número que hoje está solto ou repetido vira token
nomeado, e os componentes só consomem. É o que transforma "parece autoral" de intenção em regra
verificável.

## Technical Context

**Language/Version**: TypeScript 5.x / Node 20. **O back-end não é tocado.**

**Primary Dependencies**: Next.js 15 — `next/font/google`, que já vem no framework.
**Nenhuma dependência nova**, nenhuma biblioteca de interface ou de efeitos.

**Storage**: nenhuma mudança. **Sem migração.**

**Testing**: Vitest + Testing Library (as 95 asserções existentes ficam congeladas) · varredura
por valor solto · revisão humana com critério escrito para a checagem de identidade

**Target Platform**: Web. Interface em `localhost:5003`

**Performance Goals**: nenhum salto de layout ao carregar a fonte · movimento sem engasgo durante
rolagem · o peso da fonte variável não pode degradar o tempo até a primeira dobra legível

**Constraints**: paleta escura com laranja permanece · acessibilidade entregue permanece · sem
alterar asserção de teste existente · sem valor solto fora dos tokens · no máximo 3 gestos de
movimento

**Scale/Scope**: 1 arquivo de tokens, 5 módulos CSS, 1 layout. Nenhum arquivo de produto novo
além do carregamento da fonte.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | Nenhum estado é removido. Carregando, vazio, erro e cartaz ausente são **refinados** para parecerem do produto (FR-018), não substituídos por versão genérica. |
| **II. Integridade da Reserva** | ➖ N/A | Nenhuma escrita. Feature puramente visual. |
| **III. Ingresso Inforjável** | ➖ N/A | Idem. |
| **IV. Papéis e Autorização no Servidor** | ➖ N/A | Nenhum endpoint, nenhuma permissão. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | É a feature inteira. E vai além do refino: a disciplina de tokens que o princípio exige passa a ser **verificável por varredura**, não só declarada. |
| **VI. Rastro de Decisão Versionado** | ✅ PASS | Cada escolha visual não óbvia — a fonte, sua licença, o ritmo, o teto de movimento — fica registrada com o motivo. |
| **VII. Isolamento da API Externa** | ✅ PASS | As fontes são baixadas em tempo de build e servidas pelo próprio produto. **Nenhuma requisição a terceiro em tempo de visita** — o mesmo princípio do TMDb, aplicado a fontes. |

**Nenhuma violação.** Uma correção de dívida herdada está registrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-visual-identity/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 11 decisões visuais com alternativas
├── data-model.md        # Fase 1 — o sistema de tokens é o "modelo"
├── quickstart.md        # Fase 1 — como verificar, incluindo a checagem humana
├── contracts/
│   ├── token-contract.md      # Nomes que não podem quebrar + os novos
│   └── anti-slop-review.md    # Os critérios escritos do SC-003
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── layout.tsx                          # ALTERADO — carrega a fonte variável
│   ├── page.tsx                            # ALTERADO — ritmo entre dobra e trilhas
│   └── entrar/entrar.module.css            # ALTERADO — remove a cor literal
├── styles/
│   └── tokens.css                          # ALTERADO — o núcleo da feature
└── components/
    ├── highlights/highlights.module.css    # ALTERADO — display, hover, cor literal
    └── rows/rows.module.css                # ALTERADO — densidade, setas, esqueleto

README.md                                   # ALTERADO — fonte, licença e o porquê
```

**Structure Decision**: nenhum arquivo novo. A feature é uma reescrita concentrada de
`tokens.css` mais consumo nos cinco módulos que já existem. Criar um arquivo de "tema" separado
duplicaria a fonte única de verdade que o Princípio V exige.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **Archivo variável, eixo `wdth`** — display e texto saem do mesmo arquivo. Licença SIL OFL.
2. **`next/font/google`** — baixa em build e serve do próprio domínio, com fallback ajustado por
   métrica que elimina o salto de layout.
3. **Escala tipográfica com razão explícita**, substituindo os sete valores ad-hoc de hoje.
4. **Ritmo em dois níveis**: separação de dobra e separação de seção, com números distintos —
   é o que FR-001 exige e hoje não existe.
5. **"Movimento" definido como deslocamento ou escala**; mudança de cor é **realce**, não conta
   para o teto de três. Sem essa distinção o teto seria arbitrário.
6. **Movimento anima só `transform` e `opacity`.** O brilho do esqueleto, que hoje anima
   `background-position`, é reescrito.
7. **Setas sem borda**, ancoradas à linha de base do título — a borda circular é o traço mais
   genérico do carrossel de catálogo.
8. **Cartazes mais largos e mais juntos**, para ler como parede de cartazes em vez de grade.
9. **Critérios escritos da checagem de identidade**, em `contracts/anti-slop-review.md`.
10. **A cor literal `#150703` vira token** — dívida herdada, encontrada na auditoria.
11. **Verificação por varredura** para SC-001 e SC-002, que é o que impede a regressão silenciosa.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — o sistema de tokens: o que existe, o que entra, o que
  muda de valor, e a regra de extensão sem quebra.
- **[contracts/token-contract.md](./contracts/token-contract.md)** — os nomes de token que os
  componentes já consomem e que **não podem** desaparecer, mais os novos.
- **[contracts/anti-slop-review.md](./contracts/anti-slop-review.md)** — os critérios escritos do
  SC-003, o único ponto de julgamento humano da feature.
- **[quickstart.md](./quickstart.md)** — como verificar cada critério, incluindo a varredura
  automatizável e o roteiro da revisão.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Três pontos a vigiar na implementação:

- **O véu não pode ser afinado por estética.** Ele é o que garante contraste do texto sobre
  qualquer arte (FR-028, herdado da 001). Se o título ficar mais bonito com véu mais claro, o
  véu vence.
- **Nenhuma asserção de teste pode mudar.** É o sinal de que a feature saiu do escopo — está
  escrito em FR-030 e vale como gate.
- **O foco visível não pode virar decoração sutil.** O contorno de `:focus-visible` existe para
  quem navega por teclado; reduzi-lo em nome do refino quebraria acessibilidade entregue.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Corrigir a cor literal `#150703` em `highlights.module.css` e `entrar.module.css`, que pertencem às features 001 e 003 | É violação do Princípio V já presente no código entregue, encontrada na auditoria. Uma feature cujo objeto é a disciplina de tokens não pode deixar passar o único valor solto do projeto. | Deixar como dívida seria mais barato, mas a feature perderia a autoridade: o SC-001 exige zero valores soltos, e uma exceção conhecida invalidaria a varredura. |
