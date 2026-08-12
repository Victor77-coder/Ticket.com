# Research — Telas de Compra

**Feature**: `012-telas-de-compra` · **Data**: 2026-08-12

Onze decisões. Cada uma registra o que foi rejeitado e o número da spec que a exige. Nenhuma
reabre catálogo, reserva, pagamento ou validação.

---

## R1 — Agrupar sessões no cliente, não na API

**Decision**: A página do filme continua recebendo `screenings[]` como hoje. O agrupamento por
**dia civil** e depois por **sala** acontece no navegador.

**Rationale**: FR-003 proíbe mudar contrato de catálogo. A lista já chega completa; reapresentá-la
não cria sessão. Um endpoint novo de "grade" seria a 001 reaberta.

**Alternatives considered**:
- `GET /api/v1/filmes/<slug>/grade/` — rejeitado: contrato novo de catálogo.
- Agrupar no serializer — rejeitado: muda o formato que a 007 já consome indiretamente (a página
  monta o link `/sessoes/{id}` a partir de `screenings[].id`). Quebrar esse formato para ganhar
  um agrupamento que o cliente faz em dez linhas é o tipo de economia que vira regressão.

**Fuso**: dia civil em `America/Sao_Paulo`. "Hoje" é hoje nesse fuso. Dias sem sessão **não**
aparecem no seletor — inventar um dia vazio seria marcador de posição (FR-027). Um único dia
continua no seletor (edge case da spec).

---

## R2 — `trailers` aditivo no detalhe do filme, sem mexer no sync

**Decision**: `GET /api/v1/filmes/<slug>/` ganha `trailers`: lista dos registros **já persistidos**
(`Trailer` da 001). Sem sync novo, sem campo novo no `Movie`, sem tocar `GET /api/v1/highlights/`.

**Rationale**: FR-010 diz explicitamente que expor trailer que o registro já tem não é alteração
de catálogo; sincronizar campo novo, sim. A home já reproduz o primário. A página do filme não o
recebe hoje — é oco, não ausência de dado.

**Formato**: array, nunca `null`. Vazio = seção Trailers explica a ausência (FR-011). Cada item:
`provider`, `external_key`, `kind` (`trailer` | `teaser`), `name` (pode ser `""`). `kind` e `name`
já existem no modelo; a home não os usa e **não passa a usar**.

**Alternatives considered**:
- Reusar o `trailer` singular do highlights — rejeitado: a spec pede os trailers persistidos, e o
  modelo já guarda teaser e oficiais. Singular esconderia o que já está no banco.
- Buscar o trailer no cliente via highlights — rejeitado: a página do filme não é a home, e um
  filme fora do carrossel ficaria sem trailer por acidente de vitrine.
- Chamar o TMDb na hora — rejeitado: Princípio VII.

---

## R3 — Página do filme: servidor busca, ilha cliente só para abas e dia

**Decision**: `filmes/[slug]/page.tsx` permanece Server Component. Uma ilha cliente recebe o
filme já carregado e cuida das três seções e do dia ativo. O fetch **não** muda.

**Rationale**: Converter a página inteira em cliente arrastaria o cartaz para o bundle e perderia
o `notFound()` que a 001 já acertou. Estado de aba e de dia não precisa de URL: a spec não pede
deep link, e query string na página do filme misturaria navegação com apresentação.

**Alternatives considered**:
- Três rotas (`/filmes/x/sessoes`, `/sobre`, `/trailers`) — rejeitado: a spec pede a **mesma**
  página, e três rotas triplicam o fetch.
- `?aba=` na URL — rejeitado: complexidade sem requisito. Voltar do mapa cai em Sessões, que é o
  passo da compra.

---

## R4 — Reusar `TrailerFrame`, não movê-lo

**Decision**: A seção Trailers importa `TrailerFrame` de `components/highlights/`. O arquivo da
home **não é editado**.

**Rationale**: FR-002 proíbe alterar o carrossel. Mover o componente obrigaria a editar o painel
de destaque. Importar de `highlights/` é acoplamento visível e honesto: o trailer da página do
filme é o mesmo objeto da home. O CSS do frame continua no módulo do carrossel; o filme não
reimplementa iframe.

**Alternatives considered**:
- Copiar o frame — rejeitado: duas falhas de "trailer indisponível" divergiriam (edge case da spec).
- Extrair para `components/trailer/` — rejeitado nesta feature: o extrair toca o import da home,
  que FR-002 congela. Extração fica para se o acoplamento doer numa feature que possa tocar a home.

---

## R5 — Horário disponível continua sendo o mesmo alvo da 007

**Decision**: Visualmente o horário é um alvo compacto. Semanticamente continua um link para
`/sessoes/{id}` com rótulo acessível `Escolher lugares — {horário}, {sala}` — o mesmo padrão que
`reserva.spec.ts` já usa. Esgotada **não** é link.

**Rationale**: FR-007 pede uma interação até o mapa. FR-023 permite ajuste de seletor, mas
**preservar o nome acessível** evita enfraquecer o e2e da 007. Chip que parece botão e é `<a>` é
o mesmo critério da lista atual ("a sessão inteira é o alvo").

**Alternatives considered**:
- `<button>` + `router.push` — rejeitado: perde "abrir em nova aba" e obriga a reescrever o e2e
  sem ganho de composição.
- Mudar o rótulo para só a hora — rejeitado: o teste da 007 quebraria por seletor, e a spec
  autoriza isso só quando inevitável. Aqui é evitável.

---

## R6 — Mapa: duas colunas em tela larga; estados do assento intocados

**Decision**: `SeatSelection` passa a um layout de duas colunas ≥ 1000px (SC-004): sala à
esquerda, resumo (`SelectionSummary` / `ReservationPanel`) à direita, sticky no topo abaixo do
cabeçalho. Em estreita, o resumo empilha abaixo — o sticky inferior atual pode permanecer como
comportamento estreito. **Nenhuma regra de `.selecionado` / `.tomado` / `.acessibilidade` muda.**

**Rationale**: FR-013 pede o resumo ao lado, não só embaixo. FR-014 e SC-005 existem porque o
ajuste fino de layout é exatamente quando alguém reduz a marca de conferido do assento. O token
`--desfoque-resumo-assentos` nasceu para a barra inferior; em tela larga o resumo é superfície
opaca (`--cor-superficie`), não véu sobre o mapa.

**Alternatives considered**:
- Só tornar a barra inferior mais alta — rejeitado: continua "abaixo", que é o que a spec tira.
- Redesenhar o assento — rejeitado: fora de escopo e risco direto de SC-005.

---

## R7 — Ingresso-objeto só na tela de pagamento, via variante

**Decision**: `Ingresso` ganha uma variante de composição (`objeto` na tela de pagamento; o
padrão permanece o cartão atual). Meus ingressos e a página pública **não mudam**. QR branco nas
duas. Lugar em destaque nas duas — o objeto só acrescenta hierarquia (lugar maior, picote).

**Rationale**: A spec exclui meus ingressos e a página pública. Alterar o cartão no componente
único sem variante vazaria a 012 para a 009. Duas cópias do QR divergiriam no tamanho — a 009
já registrou isso como o motivo de reusar o componente.

**Alternatives considered**:
- Trocar o cartão em todas as superfícies — rejeitado: FR de escopo.
- Componente novo só para pagamento — rejeitado: o QR e o código digitável viveriam em dois
  arquivos, e a 009 existe precisamente para isso não acontecer.

---

## R8 — Pagamento: as colunas já existem; o trabalho é hierarquia

**Decision**: Não refazer o grid da 008. Conferir que resumo e formulário continuam lado a lado
em ≥ 1000px, que o prazo não esconde o resumo, e que após a aprovação os ingressos usam a
variante `objeto`. Recusa vs erro de preenchimento **não** se unificam.

**Rationale**: A spec assume isso. Inventar um terceiro layout seria fingir que a 008 não
entregou colunas.

**Alternatives considered**:
- Resumo em drawer / modal — rejeitado: some o "ver o que se leva" (US4).

---

## R9 — Congelamento do catálogo é lista de arquivos, não intenção

**Decision**: A implementação **não edita** estes caminhos: `components/highlights/` (exceto o
import de `TrailerFrame` **a partir** deles), `components/rows/`, `components/header/`,
`app/page.tsx`, `app/api/busca/`, contratos e testes de highlights/home/search, `seed_demo.py`,
`tmdb_sync.py`. O teste de contrato do detalhe do filme afirma o campo novo **e** que highlights
continua sem `kind`/`name` se já era assim.

**Rationale**: SC-007 não é automatizável por screenshot. A defesa prática é não tocar os
arquivos. Um diff que inclua `highlights.module.css` é falha de recorte, não "reuso".

---

## R10 — Tokens: nenhum valor de cor novo; espaço de coluna pode nascer

**Decision**: Cores da 011 intactas. Se o resumo ao lado do mapa precisar de largura, ela entra
como token de medida (irmã de `--largura-conteudo`), não como literal no CSS do assento. Picote
do ingresso-objeto usa tokens de superfície e borda já existentes — círculos do picote são
`--cor-fundo` recortando `--cor-superficie`, não uma cor nova.

**Rationale**: FR-024. A 006 tornou a 011 barata; a 012 não pode ser a feature que espalha
literal de novo.

**Alternatives considered**:
- Literal `20rem` no módulo de assentos — rejeitado: é exatamente o que a 006 tirou.

---

## R11 — Testes: seletor nas três telas; regra de negócio intocada

**Decision**: Novos testes de apresentação (abas, agrupamento por dia, resumo ao lado, variante
objeto, `trailers` no detalhe). O e2e da 007 atualiza o **caminho** até o horário se o DOM mudar,
mas o nome acessível permanece (R5). Nenhum `expect` de reserva, pagamento, QR assinado ou
portaria é afrouxado.

**Rationale**: FR-023. A armadilha desta feature é a mesma da 011 numa classe diferente: o layout
pode quebrar o clique e alguém "conserta" o teste. O conserto permitido é o seletor; o
proibido é `getByRole("link", { name: /sessão/i })` mais frouxo.

**Alternatives considered**:
- Reescrever o e2e da 007 contra um chip sem nome acessível — rejeitado: enfraquece a única
  prova de que o horário continua sendo um alvo até o mapa.
- Screenshot da grade — rejeitado: SC-010 é julgamento humano; o contrato de composição
  existe para isso, não um pixel-test.
