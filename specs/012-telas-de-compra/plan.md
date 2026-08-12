# Implementation Plan: Telas de Compra — Filme, Assentos e Pagamento

**Branch**: `main` — sem branch própria, como nas 003–011 | **Date**: 2026-08-12 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-telas-de-compra/spec.md`

## Summary

Recompor **três superfícies** — página do filme, mapa de assentos e pagamento — para que a
compra leia como cinema, sem reabrir catálogo nem regra de negócio.

**A 011 registrou o problema e se recusou a resolvê-lo.** A checagem anti-slop passou com
ressalva: a identidade estava na paleta e na tipografia; o **arranjo** das telas de compra
ainda era o de uma lista. Esta é a feature que mexe — e só aqui. A primeira dobra da home
continua o achado da 011, não o recorte desta.

**O trabalho é de apresentação sobre dado que já existe.** Sessões viram grade por dia civil
e sala no cliente, a partir do `screenings[]` que a página já recebe. Sobre usa sinopse,
classificação, duração e gênero — o que o `Movie` já persiste. Trailers expõe a lista
`Trailer` que a 001 já grava e que a home já reproduz no primário. O mapa ganha o resumo ao
lado em tela larga; o pagamento já tem colunas — o que falta é hierarquia e o ingresso como
objeto **nessa** tela. Nenhuma tabela, nenhuma constraint, nenhum sync.

**A armadilha é de classe diferente da 011, e pior no clique.** Trocar cor não quebrava
nada. Recompor o horário **quebra o caminho até o mapa** se o alvo deixar de ser o link
`Escolher lugares —`. A defesa não é afrouxar o e2e da 007: é preservar o nome acessível
(R5) e só ajustar seletor quando o DOM mudar de forma inevitável. A segunda armadilha é
"harmonizar" o QR no ingresso-objeto — `--cor-fundo-qr` continua branco.

**O recorte é uma lista de arquivos, não uma intenção.** Diff em `components/highlights/`
(além de nenhum), `components/rows/`, `app/page.tsx` ou `components/header/` é falha de
FR-002. Importar `TrailerFrame` **a partir** de highlights, na página do filme, não conta
como editar a home.

## Technical Context

**Language/Version**: TypeScript 5.x / Node 20 · Python 3.12 · CSS (módulos + tokens)

**Primary Dependencies**: Next.js 15 · Django REST Framework — **nenhuma biblioteca nova**.
O iframe do trailer continua o `TrailerFrame` da 001. O QR continua o da 008.

**Storage**: PostgreSQL — **leitura apenas**. Nenhuma migração. O único acréscimo de payload
é `trailers[]` aditivo em `GET /api/v1/filmes/<slug>/`, serializado a partir de linhas
`Trailer` já persistidas (R2). `tmdb_sync.py` e `seed_demo.py` **não são tocados**.

**Testing**: pytest (contrato aditivo do detalhe do filme + highlights inalterado) · Vitest
+ Testing Library (abas, grade do dia, resumo ao lado, variante `objeto`) · Playwright
(caminho filme → mapa → pagamento; nome acessível da 007 preservado)

**Target Platform**: Web. Interface em `localhost:5003`

**Project Type**: Web application (Django + Next.js), já existente

**Performance Goals**: a página do filme permanece Server Component; a ilha cliente não
refaz o fetch do filme ao trocar aba ou dia (R3)

**Constraints**: catálogo congelado (FR-002, FR-003) · nenhuma regra das 001–011 alterada
(FR-022) · nenhuma asserção de negócio removida ou afrouxada (FR-023) · fundo do QR branco
(FR-021) · quatro estados do assento sem cor só (FR-014) · nenhum valor de cor novo fora
dos tokens (FR-024) · `prototipo/` não é código de produto

**Scale/Scope**: 3 superfícies · 1 campo aditivo de API · 0 tabelas · 0 tokens de cor ·
possivelmente 1 token de medida (largura da coluna do resumo)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | O fluxo já está fechado desde a 010. Esta feature **não** abre etapa nova. As três telas mantêm sucesso, erro e vazio — filme sem sessão, sem trailer, confirmar sem lugar, recusa de cartão. Nada de "em breve". |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | Nenhuma escrita em reserva, assento ou pagamento. `UNIQUE(sessão, assento)`, `SELECT FOR UPDATE` e o teste de concorrência **não são tocados**. Layout do mapa não altera `.selecionado` / `.tomado` / `.acessibilidade` (R6). |
| **III. Ingresso Inforjável (NÃO NEGOCIÁVEL)** | ✅ PASS | Assinatura, `TICKET_SIGNING_KEY` e `services/ingressos.py` intactos. Variante `objeto` **não encolhe** QR nem esconde o código digitável. `--cor-fundo-qr` permanece branco — a superfície que mais parece "fora do lugar" numa recomposição de ingresso (FR-021). |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Detalhe do filme continua público. `trailers[]` não expõe gestão (sem `is_primary` como flag, sem ids internos além da chave que a home já usa, sem capacidade/custo). Portaria, login e destino por papel **não entram**. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS — **é a feature inteira** | Grade por dia e sala, resumo ao lado, ingresso-objeto. Proibições da 011 valem nestas três telas. A home **não** é reaberta — o achado da primeira dobra permanece achado. Tokens: cor nenhuma nova; medida só se a coluna do resumo precisar. |
| **VI. Rastro de Decisão** | ✅ PASS | Onze decisões em research.md. README ganha nota de que a composição das três telas mudou e a da home não. Contrato de filme-detalhe é aditivo; o de highlights permanece o da 001. |
| **VII. Isolamento da API Externa** | ✅ PASS | Nenhuma chamada ao TMDb. Trailers vêm do banco local. Sync e seed congelados. |

### O ponto que exige julgamento: campo aditivo sem reabrir catálogo

FR-003 proíbe mudar contrato de catálogo. FR-010 diz que **expor** trailer já persistido
não conta como alteração; sincronizar campo novo, sim.

**A resolução é cirúrgica.** Só `GET /api/v1/filmes/<slug>/` ganha `trailers`. Highlights,
home, busca, sync e seed **não mudam**. O serializer de destaque continua com `trailer`
singular (`provider`, `external_key`) — sem `kind`, sem `name`. Isso está no contrato e no
teste, não só na intenção.

**O que tornaria o acréscimo ilegítimo**: sync novo, coluna nova em `Movie`, direção/elenco
inventados no Sobre, ou o carrossel passando a receber `kind`/`name` "já que o serializer
existe". Qualquer um desses é reabertura da 001.

**Nenhuma violação de gate.** O campo aditivo e o acoplamento `TrailerFrame` entram em
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-telas-de-compra/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 11 decisões; R2 (trailers aditivo) e R5 (nome acessível)
├── data-model.md        # Fase 1 — apresentação, sem tabela
├── quickstart.md        # Fase 1 — as três telas e as duas quebras de propósito
├── contracts/
│   ├── filme-detalhe.md # campo `trailers` aditivo; highlights inalterado
│   └── composicao.md    # procedimento das três telas + prova de recorte do catálogo
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/apps/catalog/
├── serializers.py       # ALTERADO — MovieDetailSerializer ganha trailers[]; HighlightSerializer NÃO
├── views.py             # INTOCADO, salvo se o detalhe precisar prefetch de trailers
└── services/tmdb_sync.py  # INTOCADO

backend/tests/
└── test_filme_detalhe.py  # NOVO — trailers presente; vazio = []; highlights sem kind/name

frontend/
├── lib/types.ts         # ALTERADO — MovieDetail.trailers; tipo TrailerDoFilme ≠ Trailer da home
├── app/filmes/[slug]/
│   ├── page.tsx         # ALTERADO — Server Component busca; ilha cliente para seções e dia
│   ├── filme.module.css # ALTERADO — grade, seções; tokens só
│   └── (ilha cliente)   # NOVO — abas + seletor de dia + grade; não refaz fetch
├── components/seats/
│   ├── SeatSelection.tsx    # ALTERADO — duas colunas ≥ 1000px
│   ├── seats.module.css     # ALTERADO — layout; regras de estado do assento INTOCADAS
│   ├── Seat.tsx             # INTOCADO
│   └── SelectionSummary.tsx # ALTERADO só se a hierarquia do resumo exigir
├── components/payment/
│   └── payment.module.css   # ALTERADO só hierarquia; .colunas permanece
├── components/tickets/
│   ├── Ingresso.tsx         # ALTERADO — variante `objeto` (padrão = cartão da 009)
│   └── tickets.module.css   # ALTERADO — picote e hierarquia da variante; QR branco nas duas
├── components/highlights/TrailerFrame.tsx  # IMPORTADO, NÃO EDITADO
├── styles/tokens.css        # ALTERADO só se nascer token de MEDIDA (largura da coluna)
└── tests/
    ├── filme.test.tsx       # NOVO — seções, grade, esgotada não navega, trailer ausente
    ├── seats.test.tsx       # ALTERADO — aditivo: resumo ao lado; estados existentes intactos
    ├── pagamento.test.tsx   # ALTERADO — aditivo: variante objeto; recusa vs campo intactos
    ├── ingresso.test.tsx    # ALTERADO — aditivo: objeto; cartão padrão continua passando
    └── e2e/reserva.spec.ts  # seletor só se inevitável; nome /^Escolher lugares —/ permanece

# CONGELADOS — diff aqui é falha de FR-002, não "reuso"
frontend/components/highlights/   # exceto importar TrailerFrame a partir daqui
frontend/components/rows/
frontend/components/header/
frontend/app/page.tsx
frontend/app/api/busca/
backend/apps/catalog/services/tmdb_sync.py
backend/apps/catalog/management/  # seed
```

**Structure Decision**: três superfícies, um acréscimo de serializer, zero tabela. A ilha
cliente mora **ao lado** de `page.tsx` do filme, não no carrossel: mover estado de aba para
a home seria exatamente o vazamento que FR-002 existe para impedir.

`Ingresso` ganha variante, não um segundo componente: duas cópias do QR divergiriam no
tamanho, e a 009 existe para isso não acontecer. O padrão permanece o cartão — meus
ingressos e a página pública não entram nesta feature.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **Agrupar no cliente** — `screenings[]` não muda de forma. Dia civil em
   `America/Sao_Paulo`. Dia vazio não aparece. Um único dia continua no seletor.
2. **`trailers` aditivo no detalhe**, lista, nunca `null`. Sync e highlights intocados.
3. **Servidor busca, ilha só para aba e dia.** Sem `?aba=`. Voltar do mapa cai em Sessões.
4. **Importar `TrailerFrame`, não movê-lo** — editar highlights quebraria FR-002.
5. **O horário disponível continua o link da 007** com nome `Escolher lugares — {horário},
   {sala}`. Esgotada não é link.
6. **Mapa em duas colunas ≥ 1000px**; regras de estado do assento intocadas.
7. **Variante `objeto` só no pagamento após aprovação.** Cartão padrão intacto.
8. **Pagamento já tem `.colunas`** — não refazer o grid; hierarquia e ingresso-objeto.
9. **Congelamento é lista de arquivos.** Diff em highlights/rows/header/home é falha.
10. **Nenhum token de cor novo.** Medida de coluna, se nascer, nasce em token.
11. **Teste novo de apresentação; asserção de negócio intocada.** Seletor da 007 só se o
    nome acessível for preservado.

Nenhum NEEDS CLARIFICATION permanece.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — seção, grade do dia, resumo reposicionado,
  ingresso em duas composições. Nenhuma entidade persistida nova.
- **[contracts/filme-detalhe.md](./contracts/filme-detalhe.md)** — `trailers[]` aditivo;
  o que a resposta não ganha; teste de que highlights não herda `kind`/`name`.
- **[contracts/composicao.md](./contracts/composicao.md)** — procedimento das três telas
  e a prova de recorte (home igual à da 011).
- **[quickstart.md](./quickstart.md)** — percurso manual e as duas quebras de propósito
  (omitir `trailers`; harmonizar o fundo do QR).

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Sete pontos a vigiar na implementação:

- **O nome acessível `Escolher lugares —` é o contrato com o e2e da 007.** Chip visual
  que deixa de ser `<a>` com esse rótulo obriga a reescrever o teste — e a spec só
  autoriza ajuste de seletor quando inevitável. Aqui é evitável (R5).
- **O fundo do QR continua branco na variante `objeto`.** Harmonizá-lo com a marca é a
  falha que a 011 já nomeou e que esta feature torna mais tentadora, porque o ingresso
  "parece objeto".
- **Regras de `.selecionado` / `.tomado` / `.acessibilidade` não mudam.** Ajuste fino de
  layout do mapa é exatamente quando alguém reduz a marca de conferido.
- **`HighlightSerializer` não ganha campo.** Reusar `TrailerSerializer` enriquecido no
  carrossel vazaria `kind`/`name` para a home.
- **Sobre não inventa direção nem elenco.** Campo ausente some; nunca "N/A".
- **Nenhum arquivo congelado é editado.** Importar de `highlights/TrailerFrame.tsx` é o
  único acoplamento permitido.
- **Estados de erro e vazio das três telas permanecem em português**, com próxima ação.

### Nota sobre o que depende de julgamento humano

**SC-010 (apontar o horário em 3 segundos)** e **SC-007 (home igual à da 011)** não são
screenshot-tests, e não se tenta fingir que são. A resposta é o procedimento em
`contracts/composicao.md`: o que precisa estar presente, o que não pode, e a pergunta
final. "Não passou" vem com motivo.

Todo o resto é teste: `trailers` presente e nunca `null`, highlights sem `kind`/`name`,
esgotada que não é link, quatro estados em cinza (já medidos na 007 — não enfraquecer),
QR branco (já medido na 011 — a variante nova também precisa passar).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Campo `trailers` aditivo** em `GET /api/v1/filmes/<slug>/`, que parece mudança de contrato de catálogo | FR-010: a página do filme precisa reproduzir o que o registro **já tem**. Hoje o detalhe não serializa `Trailer`; a home serializa só o primário. Sem o campo, a aba Trailers inventaria um segundo fetch (highlights) e filmes fora do carrossel ficariam mudos por acidente de vitrine. | **Não expor e mandar a aba buscar highlights** — rejeitado: a página do filme não é a home. **Endpoint `/filmes/<slug>/trailers/`** — rejeitado: contrato novo, dois round-trips. **Enriquecer o `trailer` do highlights** — rejeitado: muda o contrato da 001 e a home, que FR-002 congela. O acréscimo é só no detalhe; o teste afirma os dois lados. |
| **Importar `TrailerFrame` de `components/highlights/`** sem extraí-lo | A seção Trailers precisa do mesmo iframe e da mesma falha "indisponível" da home. Copiar o frame criaria duas frases de erro. | **Extrair para `components/trailer/`** — rejeitado nesta feature: a extração edita o import da home, e FR-002 congela highlights. Fica para uma feature que possa tocar a home. **Copiar** — rejeitado: as duas falhas de provedor divergiriam (edge case da spec). |
