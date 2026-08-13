# Implementation Plan: Cartão de Sessão e Meia-Entrada

**Branch**: `main` — sem branch própria, como nas 003–013 | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-cartao-de-sessao-e-meia-entrada/spec.md`

## Summary

A grade de horários vira **cartão por sala** com duas ações — **Assentos** e **Preços** — que abrem
painéis sobrepostos de leitura. O painel de assentos consome o **mesmo endpoint de mapa** que a
seleção real já usa; o de preços exibe inteira e meia derivadas do preço da sessão.

A segunda metade torna a **meia comprável**: `ReservedSeat` ganha **tipo** e **valor unitário
gravado**, e o total da reserva deixa de ser uma multiplicação para virar uma **soma dos valores
gravados**.

**Essa troca é o coração técnico do plano, e ela simplifica em vez de complicar.** Hoje a regra
`preço × quantidade` está escrita em **três lugares** — `services/pagamentos.total_da_reserva`,
`ReservationSerializer.get_total` e `SeatSelection.tsx` no navegador. Somar uma coluna gravada
elimina as duas primeiras cópias em vez de criar uma terceira variante delas. Implementar meia sobre
a estrutura atual exigiria ensinar a nova regra às três.

## Technical Context

**Language/Version**: Python 3.12 (back-end), TypeScript 5 / React 19 (front-end)

**Primary Dependencies**: Django 5 + Django REST Framework; Next.js 15 (App Router). **Nenhuma
dependência nova** — os painéis são markup e estado local, não biblioteca de modal.

**Storage**: PostgreSQL 16. **Uma migração**, sobre `ReservedSeat` (ver data-model.md).

**Testing**: pytest + pytest-django (back-end), Vitest + Testing Library (front-end), Playwright (e2e)

**Target Platform**: Navegador moderno; aplicação servida por Docker Compose local e Render no ar

**Project Type**: Web — back-end e front-end separados, já estabelecidos

**Performance Goals**: O painel de assentos abre com **uma** requisição, a mesma que o mapa já
serve. Nenhuma consulta N+1 nova: o total passa a ser agregação sobre linhas já carregadas.

**Constraints**:
- O e2e da 007 (`reserva.spec.ts`) e o da 012 não podem ser afrouxados para acomodar o cartão.
- `test_payment_concurrency.py` e `test_reservation_concurrency.py` continuam válidos e ganham o
  caso de tipos mistos.
- O contrato de entrada da reserva é **aditivo**: `assentos: [int]` continua significando o que
  significava.

**Scale/Scope**: 2 painéis novos, 1 migração, 1 campo aditivo no contrato de reserva, ~4 arquivos de
back-end e ~6 de front-end tocados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | O que o garante nesta feature |
|---|---|---|
| **I. Fluxo completo antes de profundidade** | **PASSA** | O fluxo está fechado desde a 010; esta é a etapa 6. Nenhuma tela nova sem estado de sucesso, erro e vazio — FR-011 exige os três nos painéis. |
| **II. Integridade da reserva (NÃO NEGOCIÁVEL)** | **PASSA COM OBRIGAÇÃO** | `unit_price` e `ticket_type` são gravados **na mesma transação e no mesmo `bulk_create`** que já cria a ocupação. `UNIQUE(screening, seat)` intocada. **Obrigação**: estender os dois testes de concorrência com tipos mistos (T-CONC abaixo). |
| **III. Ingresso inforjável e validação única (NÃO NEGOCIÁVEL)** | **PASSA** | O tipo **não entra no código assinado** e não precisa entrar: ele é lido do banco **depois** da verificação de assinatura. Assinar o tipo criaria uma segunda verdade sobre o mesmo fato. Os quatro desfechos ficam intocados (FR-024). |
| **IV. Papéis explícitos, autorização no servidor** | **PASSA** | Nenhum endpoint novo de escrita. O campo novo da reserva é do papel cliente, no endpoint que já exige cliente. Os painéis são leitura pública, como o mapa já é. |
| **V. Interface autoral (Anti AI-Slop)** | **RISCO REAL — ver mitigação** | Esta é a primeira feature que nasce de uma **captura de tela de um concorrente**. O desafio diz "não copie; use como ponto de partida". Mitigação registrada abaixo e em research.md R8. |
| **VI. Rastro de decisão versionado** | **PASSA** | Spec, plano, research, data-model, contratos e quickstart versionados. As duas decisões de escopo foram tomadas com o autor e estão registradas na checklist da spec. |
| **VII. Isolamento da API externa** | **PASSA** | O TMDb não é tocado. Nenhuma chamada nova. |

### Mitigação do Princípio V

O que **não** vem da imagem, e por quê, já está em FR-005: nome e endereço de cinema, selo de
áudio e favoritar. Sobra o **arranjo** — cabeçalho, régua, ações à direita, horários como alvos — que
é vocabulário de grade de cinema, não assinatura de uma marca.

O que torna o cartão desta plataforma e não uma cópia:

1. **O cabeçalho é a sala**, a unidade que este domínio de fato tem, e não uma unidade comercial que
   ele não modela.
2. **O preço vive no horário**, decisão tomada hoje mesmo e que a referência não tem — lá o preço
   está escondido atrás do botão.
3. **A paleta, a tipografia e o ritmo são os tokens da 006/011.** Nenhum valor solto entra; o teste
   `tokens.test.ts` reprova respingo de cor.
4. **O painel de assentos é prévia declarada**, com caminho para o mapa real — a referência abre
   direto no mapa de compra.

## Project Structure

### Documentation (this feature)

```text
specs/014-cartao-de-sessao-e-meia-entrada/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — as decisões e o que foi descartado
├── data-model.md        # Fase 1 — a migração e por que ela é uma só
├── quickstart.md        # Fase 1 — os percursos de verificação
├── contracts/
│   ├── reserva-com-tipo.md   # O contrato aditivo de reserva e de ingresso
│   └── paineis-do-cartao.md  # O contrato de interface dos dois painéis
├── checklists/
│   └── requirements.md  # Já existe (saída do /speckit-specify)
└── tasks.md             # Fase 2 — NÃO criado por este comando
```

### Source Code (repository root)

```text
backend/
├── apps/screening/
│   ├── migrations/
│   │   └── 0006_reservedseat_ticket_type_and_unit_price.py   # NOVO — a única
│   ├── models.py                    # ReservedSeat ganha dois campos
│   ├── serializers.py               # total passa a somar; tipo exposto
│   ├── services/
│   │   ├── precos.py                # NOVO — dono único do valor por lugar
│   │   ├── reservas.py              # grava tipo e valor na criação
│   │   └── pagamentos.py            # total_da_reserva vira soma
│   └── views.py                     # aceita `meias` no corpo da reserva
└── tests/
    ├── test_precos.py               # NOVO — arredondamento e derivação
    ├── test_reservation_api.py      # tipos mistos entram aqui
    ├── test_payment_concurrency.py  # estendido com tipos mistos
    └── test_meia_entrada.py         # NOVO — total, ingresso e portaria

frontend/
├── app/filmes/[slug]/
│   ├── GradeDoDia.tsx               # vira cartão por sala com as duas ações
│   └── filme.module.css             # tokens do cartão
├── components/
│   ├── sessao/                      # NOVO
│   │   ├── CartaoDeSessao.tsx
│   │   ├── PainelDeAssentos.tsx
│   │   ├── PainelDePrecos.tsx
│   │   ├── Sobreposicao.tsx         # foco preso, Esc, devolução de foco
│   │   └── sessao.module.css
│   └── seats/
│       ├── SeatSelection.tsx        # tipo por lugar; total do servidor
│       └── SelectionSummary.tsx     # linha por lugar com o tipo
├── lib/
│   ├── meia.ts                      # NOVO — espelho puro da regra de preço
│   └── types.ts                     # tipo no ingresso e no lugar reservado
└── tests/
    ├── cartao-de-sessao.test.tsx    # NOVO
    ├── paineis.test.tsx             # NOVO — teclado, foco, estados
    ├── meia.test.ts                 # NOVO — o espelho bate com o servidor
    └── e2e/meia-entrada.spec.ts     # NOVO
```

**Structure Decision**: mantém a separação `backend/` + `frontend/` já estabelecida desde a 001. Os
componentes do cartão nascem em `components/sessao/` — diretório novo, porque não são nem
apresentação de assento (`components/seats/`, que é do fluxo de compra) nem de catálogo
(`components/rows/`). Colocá-los em `seats/` sugeriria que participam da seleção, e o FR-007 diz
exatamente o contrário.

## As três obrigações que o plano carrega

Não são tarefas; são condições de aceitação do plano inteiro.

**T-CONC — os testes de concorrência ganham tipos mistos.** `test_payment_concurrency.py` prova hoje
que uma reserva não gera dois conjuntos de ingressos. Com valor gravado por lugar, ele precisa provar
o mesmo com **uma inteira e uma meia na mesma reserva**, e o valor cobrado precisa ser o da soma.
Sem isso, a garantia mais cara do projeto passa a cobrir só o caso uniforme.

**T-DONO — o total tem um dono só, e ele é a soma.** Ao fim desta feature, `screening.price *
quantidade` **não pode existir em lugar nenhum do back-end**. A busca `price *` no `backend/` é parte
da revisão.

**T-VAZAMENTO — o tipo entra na lista de permitidos por decisão explícita.**
`test_share_link_leakage.py` inspeciona a resposta pública por valor. O tipo é permitido lá (FR-023);
o teste precisa ser atualizado **deliberadamente**, com a razão escrita no próprio teste — e não
afrouxado para deixar de olhar.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Uma migração**, quando a 013 se orgulhou de zero | Meia comprável exige que o valor cobrado por lugar exista como fato, não como cálculo. Sem coluna, o valor teria de ser recalculado a cada leitura, e "exibido" e "cobrado" divergiriam na primeira mudança de regra | **Derivar o valor na leitura** foi rejeitado: recalcular a partir de `screening.price` toda vez significa que uma sessão cujo preço mudasse reescreveria o passado de uma compra fechada. Gravar o valor é o que torna a nota do que foi vendido imutável |
| **Um diretório novo de componentes** (`components/sessao/`) | Os painéis não pertencem a nenhum dos diretórios existentes, e o FR-007 depende de eles **não** serem confundidos com seleção | **Pôr em `components/seats/`** foi rejeitado porque colocaria prévia e seleção lado a lado, que é exatamente a confusão que a spec proíbe |
| **Campo `meias` no contrato de reserva**, em vez de trocar `assentos` para objetos | Mantém `assentos: [int]` com o mesmo significado, então o e2e da 007 e qualquer chamada existente continuam válidos sem edição | **Trocar `assentos` para `[{id, tipo}]`** foi rejeitado: quebraria o contrato da 007 e forçaria afrouxar um teste ponta a ponta que existe para não ser afrouxado |
