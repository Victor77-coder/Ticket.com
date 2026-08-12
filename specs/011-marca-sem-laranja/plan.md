# Implementation Plan: Marca sem Laranja — Cor, Tipografia de Marca e Logo

**Branch**: `main` — sem branch própria, como nas 003–010 | **Date**: 2026-08-12 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-marca-sem-laranja/spec.md`

## Summary

Trocar a cor da marca, dar tipografia própria ao nome e desenhar uma logo que deriva dele — emendando
a direção da 006 sem reabrir uma linha de comportamento.

**A cor sai por eliminação, e é o achado que estrutura o plano.** Parecia decisão de gosto e não é:
quatro restrições aplicadas em ordem deixam uma região só do círculo cromático. A que ninguém
antecipa é a segunda — **a marca não pode colidir com cor de estado**. O sistema já tem sucesso
(verde, 153°), alerta (âmbar, **38°**) e erro (coral, 0°). Isso **elimina o âmbar**, que era o
candidato mais óbvio para um cinema: ele fica a **8°** do alerta, e adotá-lo exigiria mover uma cor de
estado — coisa que a spec excluiu. O laranja que está saindo, medido pelo mesmo critério, era o mais
próximo de todos de uma cor de estado (ΔE 20 do erro).

O que sobra é o magenta, e o que a região significa neste domínio tem nome: das quatro luzes de um
cinema à noite — marquise, saída, projeção, fachada —, três já estão ocupadas pelas cores de estado.
**Sobrou o neon da fachada**, que por acaso é a luz que se vê antes de entrar, para uma marca cuja
função é vender a entrada.

**A 006 é o motivo de isto ser barato.** Verificado: o laranja vive em **4 declarações**, todas em um
arquivo; **12 arquivos** consomem só os nomes, em **28 usos**. A disciplina de tokens segurou por
completo, e trocar a identidade cromática inteira é trocar quatro valores.

**E a armadilha é de uma classe nova.** Nas features 007–010 o risco era de correção, e sempre havia
um teste ou uma constraint que reclamava. Aqui, **trocar um valor de cor não quebra nada**: os 197
testes de front-end continuam verdes com o contorno de foco invisível, o texto do botão ilegível e o
assento selecionado indistinguível do tomado. Nenhum teste mede contraste. Por isso o entregável
central deste plano é um teste que **lê os tokens e mede**.

## Technical Context

**Language/Version**: TypeScript 5.x / Node 20 · CSS (custom properties)

**Primary Dependencies**: Next.js 15 · **família tipográfica nova para a marca (Cabinet Grotesk,
Fontshare), auto-hospedada** — justificada em R6 e em Complexity Tracking. Nenhuma biblioteca de
componentes, de efeito ou de cor

**Storage**: N/A — a feature não toca banco, API, seed nem migração

**Testing**: Vitest + Testing Library · Playwright · **teste novo que lê `tokens.css` e calcula
contraste WCAG e distância perceptual (ΔE) entre marca e cores de estado** (R10)

**Target Platform**: Web. Interface em `localhost:5003`

**Performance Goals**: a família da marca não pode adiar a primeira pintura nem produzir salto de
layout ao chegar (FR-018)

**Constraints**: nenhuma regra de negócio alterada · nenhuma asserção de comportamento das 001–010
removida ou enfraquecida · fundo do QR permanece branco · assentos e desfechos da portaria continuam
distinguíveis sem cor · disciplina de tokens da 006 integralmente mantida · nenhum valor de cor fora
dos tokens

**Scale/Scope**: 4 valores de token, 1 arquivo de tokens, 12 arquivos consumidores **que não devem
ser tocados**, 10 superfícies a conferir, 1 componente de marca a evoluir

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | Nenhuma etapa do fluxo é tocada. Todas as dez superfícies recebem a paleta nova — nenhuma fica para trás, e nenhuma perde estado de erro ou vazio. Nada de "em breve". |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | A feature não escreve no banco. Nenhuma constraint, transação ou consulta é tocada. |
| **III. Ingresso Inforjável (NÃO NEGOCIÁVEL)** | ✅ PASS | Assinatura, verificação e os quatro desfechos intactos. **O fundo do QR permanece branco** — exceção deliberada da 008, e o item mais provável de ser "harmonizado" por engano numa feature de paleta (FR-029). |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Nenhuma decisão de autorização muda. O destino da marca por papel, entregue na 010, é **preservado** e continua guardado pelo teste daquela feature (R9). |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS — **é a feature inteira** | Cor escolhida por eliminação, com as rejeitadas registradas e medidas. Tipografia de marca própria. Marca gráfica derivada do nome, não de biblioteca. Disciplina de tokens integral. Assentos e desfechos continuam não dependendo de cor. Contrato anti-slop ganha sucessor. |
| **VI. Rastro de Decisão** | ✅ PASS | Doze decisões em research.md, com as alternativas e o número que as eliminou. README ganha fontes, licenças, uso de IA e a nota de que esta feature emenda o FR-020 da 006. O contrato sucedido permanece no lugar, marcado. |
| **VII. Isolamento da API Externa** | ✅ PASS | Nenhuma chamada ao TMDb. A fonte da marca é **auto-hospedada** — nenhuma requisição a terceiro em tempo de visita, mesma regra que a 006 aplicou à família da interface (R7). |

### O ponto que exige julgamento: emendar um requisito de outra feature

Esta feature **revoga** parte do FR-020 da 006 — *"a paleta DEVE permanecer escura com destaque
laranja"*. Emendar requisito de feature entregue não é rotina, e por isso o registro:

**A emenda é cirúrgica e tem endereço.** Revoga a segunda metade da frase e mantém a primeira. A base
escura, o ritmo, a família da interface e todas as proibições anti-slop da 006 continuam valendo —
há uma tabela na spec separando o que é emendado do que é preservado.

**O contrato anti-slop ganha sucessor, não edição.** Aquele documento é o único critério subjetivo da
006 com regra escrita, e existe para que "não passou" venha com motivo. Editá-lo no lugar apagaria o
registro de que a paleta um dia foi outra; o Princípio VI pede rastro, não estado final.

**O que tornaria a emenda ilegítima**, e por isso vira exigência verificável: se ela reabrisse
comportamento. FR-035 a FR-039 fecham isso, e a suíte das 001–010 é a prova — se um teste de regra de
negócio quebrar, a mudança visual está errada, não o teste.

**Nenhuma violação.** Dois itens em Complexity Tracking: a emenda acima e a família tipográfica nova.

## Project Structure

### Documentation (this feature)

```text
specs/011-marca-sem-laranja/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 12 decisões; R1 (a eliminação) e R10 (a falha silenciosa)
├── data-model.md        # Fase 1 — o grafo de tokens e onde cada papel do destaque atua
├── quickstart.md        # Fase 1 — incluindo como quebrar o contraste de propósito
├── contracts/
│   ├── anti-slop-review.md   # SUCESSOR do contrato da 006
│   └── contraste.md          # os limites medidos, e o que o teste verifica
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
frontend/
├── styles/tokens.css                    # ALTERADO — 4 valores + --fonte-marca. O ÚNICO arquivo
│                                        #   onde cor de marca é definida
├── app/layout.tsx                       # ALTERADO — carrega a família da marca, com fallback
│                                        #   métrico para não saltar (R7)
├── public/fontes/                       # NOVO — a família da marca e o ARQUIVO DE LICENÇA
├── components/header/
│   ├── BrandMark.tsx                    # ALTERADO — marca gráfica + wordmark. PRESERVA o destino
│   │                                    #   por papel que a 010 entregou (R9)
│   ├── MarcaGrafica.tsx                 # NOVO — SVG em caminho vetorial, completa e compacta
│   └── header.module.css                # ALTERADO — só o que a marca nova exige
├── app/icon.svg                         # NOVO — variante compacta como ícone de aba
└── tests/
    ├── tokens.test.ts                   # NOVO — A PROVA: contraste, ΔE e ausência da cor antiga
    ├── marca.test.tsx                   # NOVO — variantes, rótulo acessível, destino por papel
    └── header.test.tsx                  # ALTERADO — aditivo; nada existente enfraquecido

specs/006-visual-identity/contracts/anti-slop-review.md   # ALTERADO — marcado como SUCEDIDO
README.md                                # ALTERADO — fontes, licenças, uso de IA, a emenda ao FR-020
```

**Structure Decision**: os **12 arquivos consumidores não são tocados**, e isso é o resultado da
feature, não uma economia. Se algum precisar de edição, é sinal de que um valor de cor vazou para
fora dos tokens — e a varredura de SC-003 é o que denuncia.

`MarcaGrafica.tsx` é separado de `BrandMark.tsx` porque são coisas com ciclos diferentes: a marca é
geometria fixa em caminho vetorial; o `BrandMark` decide destino por papel, rótulo acessível e qual
variante mostrar. Juntos, a lógica de papel ficaria enterrada dentro de um `<svg>`, que é o lugar
mais fácil de perdê-la numa refatoração — e perdê-la significa a portaria voltando a cair no
catálogo.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **A cor sai por eliminação** — proibições nomeadas, colisão com cor de estado, os quatro papéis
   funcionais, e "não ser a cor padrão de tecnologia". Sobra o magenta: `#ff2e88`.
2. **O âmbar morre pela colisão**, a 8° do `--cor-alerta` — não por gosto. Era o candidato mais
   óbvio para um cinema, e custaria mover uma cor de estado.
3. **O azul tem a melhor medida e perde assim mesmo** (ΔE 101): é o azul padrão de todo software,
   vizinho do índigo vetado. A melhor nota não vence o pior resultado no critério anti-slop.
4. **O conceito é "neon de fachada"** — das quatro luzes de um cinema, três já são cores de estado.
5. **Os nomes de token ficam; só os valores mudam.** Renomear custaria 28 edições para ganhar nada
   verificável, e cada arquivo tocado é uma chance de uma superfície ficar para trás.
6. **`-forte` é mais clara que a base**, e é contraintuitivo de propósito: ela é o contorno de foco
   global e o hover de botões já preenchidos.
7. **A cor sobre o destaque é medida em DOIS fundos** — base e `-forte` —, porque o texto do botão
   vive nos dois, e o segundo é o estado em que a pessoa está quando vai clicar.
8. **Família própria para a marca**, e não um corte extremo do Archivo: a interface já usa dois
   cortes do mesmo eixo, e um terceiro some no tamanho em que a marca é vista.
9. **A logo é o `t` com o ponto do `.com`**, em caminho vetorial — promove o que o nome já tem, em
   vez de inventar um ícone de ingresso que serviria a qualquer cinema.
10. **A falha silenciosa é o contraste**, e nenhum teste existente a pega.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — o grafo de tokens da marca, o mapa dos 28 usos por papel
  (ação, foco, seleção, marca, vestígio) e os invariantes que o teste verifica.
- **[contracts/contraste.md](./contracts/contraste.md)** — os pares medidos, os limites e o que
  acontece quando um cai.
- **[contracts/anti-slop-review.md](./contracts/anti-slop-review.md)** — o sucessor do contrato da
  006, com "Neon de fachada" no lugar de "Laranja de projeção" e dois itens novos.
- **[quickstart.md](./quickstart.md)** — percorrer as dez superfícies, **quebrar o contraste de
  propósito** e conferir que o teste falha.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Sete pontos a vigiar na implementação:

- **O contorno de foco é `--cor-destaque-forte`** (`tokens.css:293`). É o token mais fácil de
  escurecer "para a marca ficar mais elegante", e escurecê-lo apaga o foco de teclado sem quebrar
  nada.
- **O fundo do QR continua branco.** É a superfície que mais parece fora do lugar numa feature de
  paleta, e a única que não pode mudar.
- **Nenhum dos 12 consumidores deve ser editado.** Se um precisar, um valor vazou dos tokens.
- **`--cor-sobre-destaque` precisa passar em dois fundos**, não em um.
- **O `BrandMark` preserva o destino por papel da 010.** Reescrevê-lo do zero é a forma mais provável
  de perder isso — o comportamento não é óbvio olhando um componente de logotipo.
- **Assentos e desfechos da portaria** entram na conferência mesmo estando corretos hoje: o ajuste
  fino da cor nova é exatamente quando alguém reduz a borda do assento selecionado.
- **A fonte da marca não pode saltar o layout ao chegar.** Fallback com métrica declarada.

### Nota sobre o que depende de julgamento humano

**SC-008 (nomear a marca em 2 segundos) e SC-009 (a primeira dobra sem cabeçalho)** não são
automatizáveis, e não se tenta fingir que são. A resposta é a mesma que a 006 deu: um procedimento
escrito e repetível, em `contracts/anti-slop-review.md`, com lista do que precisa e do que não pode
estar presente — para que "não passou" venha com motivo, e para que outra pessoa chegue ao mesmo
veredito.

Todo o resto é varredura ou medição: ausência da cor antiga, contraste, ΔE, valores fora de token,
ausência de rolagem lateral, distinção em escala de cinza.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Emendar o FR-020 da 006**, requisito de feature já entregue, revogando o destaque laranja | É o pedido explícito desta feature: a identidade não podia continuar sendo a de todo produto de entretenimento escuro. A emenda é cirúrgica — revoga a exigência de laranja e mantém base escura, ritmo, tipografia de interface e todas as proibições anti-slop. | **Manter o laranja** foi rejeitado pelo pedido e pela medida: ele é, dos candidatos avaliados, o mais próximo de uma cor de estado (ΔE 20 do `--cor-erro`). **Editar o contrato anti-slop da 006 no lugar** foi rejeitado por apagar o rastro de que a paleta um dia foi outra — o sucessor declara o que substitui, e o original fica marcado como sucedido. **Se a emenda não se sustentar em revisão, o caminho é reverter os valores dos tokens** — quatro linhas —, não deixar duas identidades convivendo. |
| **Família tipográfica nova** para a marca, depois de a 006 ter fechado com uma família só | O nome do site não tinha desenho: era o mesmo texto da interface com o sufixo colorido. Uma marca precisa de tratamento próprio, e a spec o exige. A família é auto-hospedada, sem requisição a terceiro, e consumida por **exatamente um** componente. | **Corte extremo do Archivo** (`wdth` 62) foi seriamente considerado — zero dependência, argumento tipográfico real de bloco de créditos — e rejeitado porque a interface já usa dois cortes do mesmo eixo, e a diferença some a 20px, que é o tamanho em que a marca vive. Fica registrado como a saída se a licença travar. **Clash Display** foi rejeitada por ser a face de display mais usada em interface escura contemporânea — escolhê-la seria escolher a tipografia que o critério anti-slop existe para evitar. |
