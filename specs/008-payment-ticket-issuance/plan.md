# Implementation Plan: Pagamento Simulado e Emissão do Ingresso

**Branch**: `008-payment-ticket-issuance` (criada; o trabalho vem sendo commitado em `main` desde a
001 — ver nota ao fim de "Project Structure") | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-payment-ticket-issuance/spec.md`

## Summary

Cobrar a reserva de forma simulada e — **na mesma transação** — emitir um ingresso por assento, com
código assinado por um segredo próprio. Aprovação e emissão não se separam: é o Princípio II
declarando que não existe estado durável em que o assento esteja pago e sem dono.

**A decisão que estrutura a feature no banco**: duas constraints, não uma. Um índice **parcial**
`UNIQUE(reserva) WHERE aprovado` no pagamento, e `UNIQUE(assento reservado)` absoluta no ingresso.
A parcial é possível aqui e era impossível na 007 — lá o predicado dependia de `now()`, que o
PostgreSQL recusa em índice; aqui é `status = 'approved'`, imutável. É essa diferença que permite
guardar todas as tentativas recusadas sem que a unicidade as proíba.

**E a descoberta que vale mais que a constraint**: a 007 decide ocupação por
`expires_at > now()`, em **três cópias** da mesma regra. Uma reserva paga não mexe em `expires_at`
— dez minutos depois da compra ela vira indistinguível de uma reserva abandonada, o lugar vendido
volta ao mapa como livre, e a terceira cópia (`_liberar_ou_recusar`) **apaga a ocupação** e entrega
o assento a outro cliente. Nenhuma constraint impede isso: apagar antes de inserir é uma operação
perfeitamente legal para o banco.

É a única falha desta feature que a garantia da 007 não pega, e a correção — regra de ocupação com
dois termos, escrita **uma vez** e consumida pelos três pontos — é o trabalho mais importante do
plano.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 + DRF · Next.js 15 · **`qrcode` (nova, Python puro, sem Pillow)**
— justificada em R11 e em Complexity Tracking. Assinatura usa `django.core.signing`, já no Django.

**Storage**: PostgreSQL 16. **Uma** migração cria `Payment`, `Ticket`, as duas constraints e
`Status.PAID` — as cinco coisas juntas, porque separar aprovação de emissão é o que o Princípio II
proíbe

**Testing**: `pytest` + `pytest-django` com **transações reais e threads** para concorrência, e
`django_assert_num_queries(0)` para provar que a assinatura é verificada antes do banco · Vitest +
Testing Library · Playwright

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Performance Goals**: pagamento respondido em ≤ 1 s · confirmação com até 6 ingressos e seus QR
em ≤ 1 s · a emissão não pode fazer uma consulta por ingresso

**Constraints**: nenhuma asserção das features 001–007 pode mudar · disciplina de tokens mantida ·
pagamento e emissão funcionam com o TMDb fora do ar · autorização no servidor · a chave de
assinatura nunca chega ao navegador

**Scale/Scope**: reservas de 1 a 6 lugares, dezenas de sessões. Escala de avaliação — mas a
unicidade do pagamento precisa valer sob concorrência real.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | Aprovação, recusa, reserva vencida, reserva já paga, sessão indisponível e recusa por papel têm cada um estado próprio em pt-BR. Fecha a etapa 3 da ordem de construção e destrava a 4. |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS **com leitura registrada** | Aprovação e emissão na mesma transação e na mesma migração. Duas constraints de banco (R1). Bloqueio da reserva antes de revalidar. Teste de concorrência é prova obrigatória e precisa **falhar** sem a constraint. **A cláusula "pagamento recusado DEVE liberar o assento" recebe leitura explícita — ver abaixo.** |
| **III. Ingresso Inforjável (NÃO NEGOCIÁVEL)** | ✅ PASS | `django.core.signing` com **chave própria**, distinta da `SECRET_KEY`, fora do front-end, no `.env.example`. Identidade pública em UUID, nunca sequencial. Conteúdo carrega a sessão, para a portaria distinguir "sessão errada" de "inválido". Verificação **sem tocar o banco**, provada por `num_queries == 0`. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Só papel cliente paga (`403` para organizador e portaria); só o dono paga a dela (`404`, não `403`, para não confirmar existência). Teste de acesso cruzado obrigatório. |
| **V. Interface Autoral** | ✅ PASS | Três motivos de recusa com frase própria em pt-BR, dizendo o que houve e a próxima ação. Erro de preenchimento distinto de recusa de cobrança. Tokens da 006 preservados. |
| **VI. Rastro de Decisão** | ✅ PASS | README ganha a variável nova e a tabela de cartões (FR-052). A leitura do Princípio II, a escolha das duas constraints e a dependência nova ficam registradas com o motivo. |
| **VII. Isolamento da API Externa** | ✅ PASS | Pagamento e emissão leem só o banco local. Nenhum provedor externo de pagamento — a cobrança é simulada (FR-005). |

### O ponto que exige julgamento: "pagamento recusado DEVE liberar o assento"

O Princípio II contém essa cláusula, e esta feature **não** libera o assento na recusa. A spec
registra a leitura numa seção própria; o gate confirma-a, com a avaliação exigida pela Governance:

**A leitura se sustenta.** A frase seguinte do próprio princípio dá o critério — "não existe estado
intermediário durável em que o assento esteja preso sem dono". Depois de uma recusa o assento tem
**dono** (a mesma reserva, do mesmo cliente) e tem **prazo correndo** (o vencimento original,
intocado). Nenhum dos dois defeitos que a cláusula previne ocorre, e quem devolve o lugar ao
estoque continua sendo o vencimento, por consulta, sem rotina agendada — exatamente como já
acontece com quem abandona a reserva sem tentar pagar.

**O que tornaria a leitura falsa**, e por isso vira exigência de implementação verificável:

1. se a recusa **estendesse** o vencimento, o cartão recusado viraria ferramenta para segurar o
   lugar indefinidamente → FR-027, e `expira_em` volta no corpo do `402` justamente para que a
   ausência de mudança seja observável;
2. se a recusa deixasse a reserva num estado que a expiração não alcança → não deixa: o caminho de
   recusa não escreve nada em `Reservation`.

**Se em revisão a leitura não se sustentar, o caminho é emendar a constitution** — com incremento
de versão e Sync Impact Report —, nunca implementar a divergência em silêncio. Registrado também em
Complexity Tracking, para que não dependa de alguém ler esta seção.

**Nenhuma violação.** Três itens em Complexity Tracking: a leitura acima, a dependência nova e a
alteração de código da 007.

## Project Structure

### Documentation (this feature)

```text
specs/008-payment-ticket-issuance/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 14 decisões; R3 é o achado que mais importa
├── data-model.md        # Fase 1 — Payment, Ticket, e a regra de ocupação corrigida
├── quickstart.md        # Fase 1 — incluindo como forjar um QR e ver a recusa
├── contracts/
│   └── payment-ticket-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/screening/
│   ├── models.py                        # ALTERADO — Payment, Ticket, Status.PAID, predicado OCUPANDO
│   ├── migrations/0003_*.py             # NOVO — os dois modelos, as duas constraints e o estado, juntos
│   ├── services/
│   │   ├── pagamentos.py                # NOVO — a transação que aprova e emite
│   │   ├── ingressos.py                 # NOVO — assinar e verificar; PURO, sem banco
│   │   └── reservas.py                  # ALTERADO — nunca apagar ocupação de reserva paga
│   ├── selectors.py                     # ALTERADO — ocupacoes_vivas passa a usar OCUPANDO
│   ├── serializers.py                   # ALTERADO — entrada do cartão, saída de pagamento e ingresso
│   ├── permissions.py                   # ALTERADO — mensagem própria do pagamento
│   ├── views.py                         # ALTERADO — PaymentCreateView
│   └── urls.py                          # ALTERADO
├── config/settings/base.py              # ALTERADO — TICKET_SIGNING_KEY e a tabela de cartões
├── pyproject.toml                       # ALTERADO — dependência `qrcode`
└── tests/
    ├── test_payment_api.py              # NOVO — autorização, estados, mensagens, cartões
    ├── test_payment_concurrency.py      # NOVO — a prova do Princípio II
    ├── test_ticket_signature.py         # NOVO — a prova do Princípio III
    ├── test_paid_seat_retention.py      # NOVO — a prova de R3, a armadilha da 007
    └── test_reservation_api.py          # ALTERADO — casos novos, nenhuma asserção existente tocada

frontend/
├── app/pagamento/[id]/
│   ├── page.tsx                         # NOVO — uma rota, quatro estados (R13)
│   └── pagamento.module.css             # NOVO
├── app/api/pagar/route.ts               # NOVO — proxy, padrão da 002/003/007
├── components/payment/
│   ├── ResumoDaCompra.tsx               # NOVO — o que está sendo comprado e o prazo
│   ├── FormularioDeCartao.tsx           # NOVO
│   └── payment.module.css               # NOVO
├── components/tickets/
│   ├── Ingresso.tsx                     # NOVO — um ingresso, com QR e código legível
│   └── tickets.module.css               # NOVO
└── tests/
    ├── pagamento.test.tsx               # NOVO
    └── ingresso.test.tsx                # NOVO

.env.example                             # ALTERADO — TICKET_SIGNING_KEY
README.md                                # ALTERADO — variável nova e tabela de cartões (FR-052)
```

**Structure Decision**: a feature vive em `apps/screening`, junto de `Reservation` e `ReservedSeat`.
`Ticket` aponta para `ReservedSeat` e **carrega uma constraint sobre ela** — a garantia fica na
mesma app do modelo que protege, e a migração que cria as duas coisas é uma só. Uma app `billing`
separada faria chave estrangeira e constraint atravessarem fronteira de app para nada (R12).

`services/pagamentos.py` e `services/ingressos.py` são arquivos distintos de propósito: o primeiro
tem transação e banco, o segundo é **puro** e não pode importar modelo nenhum. A separação é o que
torna `num_queries == 0` verificável em vez de aspiracional (R7).

`/pagamento/[id]` não é rota nova por escolha: `ReservationPanel.tsx` da 007 já aponta para lá.
Honrá-la evita mexer em código da 007 sem necessidade (R13).

> **Nota sobre a branch**: o hook do Spec Kit criou `008-payment-ticket-issuance`, mas o `HEAD`
> está em `main`, e é em `main` que as features 001–007 foram commitadas — a spec da 007 registra
> "o projeto trabalha sem branches de feature". Este plano não muda a prática; a decisão de
> trabalhar na branch ou seguir em `main` é do usuário, e o único requisito da constitution é que
> os commits sejam incrementais e descritivos.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **Duas constraints, não uma** — `UNIQUE(reserva) WHERE aprovado` parcial no pagamento, e
   `UNIQUE(assento reservado)` absoluta no ingresso. A segunda sozinha impediria dois conjuntos de
   ingressos; sem a primeira, seria possível existir pagamento aprovado **sem** ingresso.
2. **O índice parcial é possível aqui e era impossível na 007** — `status = 'approved'` é predicado
   imutável; `expira_em > now()` não é. As duas features têm formas diferentes porque o banco
   permite coisas diferentes, não por preferência.
3. **A armadilha da 007** — ocupação decidida só por `expires_at` faz o lugar **vendido** voltar ao
   estoque, e `_liberar_ou_recusar` **apaga** a ocupação paga sem violar constraint alguma. A regra
   ganha um segundo termo e passa a existir num lugar só.
4. **A recusa retorna, não levanta** — exceção dentro de `atomic()` desfaria o registro da própria
   recusa, e o rastro exigido por FR-012 sumiria. Por isso a recusa é `402`, não `400` nem `409`.
5. **Assinatura com `django.core.signing` e chave própria** — HMAC-SHA256 já revisado, sem
   dependência nova. `salt` dá separação de domínio; a chave separada é que dá separação de
   segredo, e é isso que FR-031 pede.
6. **O conteúdo assinado carrega a sessão** — para a portaria distinguir "sessão errada" de
   "inválido" na feature seguinte. Entra agora porque acrescentá-lo depois invalidaria todo código
   já emitido.
7. **A verificação é função pura, provada por `num_queries == 0`** — afirmação sobre ausência só
   vale se algo falhar quando a ausência acabar.
8. **Recusa determinística por número de cartão**, tabela fixa em contrato com o README. Sorteio
   não é exercitável pelo avaliador nem testável.
9. **QR gerado no back-end como SVG em `data:` URI** — quem gera a verdade gera a representação; e
   `<img>` com `alt` evita `dangerouslySetInnerHTML`.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — `Payment`, `Ticket`, o estado `paid`, a transação de
  pagamento passo a passo, e a regra de ocupação viva corrigida.
- **[contracts/payment-ticket-api.md](./contracts/payment-ticket-api.md)** — o `POST` do pagamento
  com seus seis desfechos, o `GET` da reserva ampliado, e os campos proibidos.
- **[quickstart.md](./quickstart.md)** — percorrer o fluxo, **provocar as três recusas**,
  **tentar forjar um QR**, e reproduzir a corrida à mão.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Cinco pontos a vigiar na implementação:

- **Os dois modelos e as duas constraints entram na mesma migração.** Um commit com o pagamento e
  outro com o ingresso deixaria uma janela em que existe aprovação sem emissão — literalmente o
  estado que o Princípio II proíbe.
- **`_liberar_ou_recusar` nunca apaga ocupação de reserva paga.** É a única falha desta feature que
  o banco aceita sem reclamar, e por isso a única que depende inteiramente de teste.
- **`services/ingressos.py` não importa modelo.** No dia em que importar, `num_queries == 0` deixa
  de ser garantido pela estrutura e passa a depender de disciplina.
- **`TICKET_SIGNING_KEY` sem valor padrão utilizável**, como a `SECRET_KEY` já faz. Um padrão em
  código vira o segredo real de todo mundo que não leu o README, e o QR passa a ser forjável por
  quem leu o repositório.
- **O teste de concorrência precisa de transação real.** Herdado da 007: sem `transaction=True` as
  threads compartilham conexão, e o teste passa com ou sem a constraint.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Leitura do Princípio II**: a recusa não libera o assento, contrariando a letra de "pagamento recusado DEVE liberar o assento" | O critério do próprio princípio é a frase seguinte — "nenhum estado durável com o assento preso sem dono". Após a recusa o assento tem dono e prazo correndo, e o vencimento continua devolvendo-o ao estoque. Liberar na recusa faria quem digitou o cartão errado perder o lugar entre uma tentativa e a seguinte. | Liberar imediatamente foi rejeitado por piorar o produto sem melhorar a integridade. **Se a leitura não se sustentar em revisão, o caminho é emendar a constitution**, com incremento de versão e Sync Impact Report — não implementar a divergência em silêncio. |
| Dependência nova `qrcode`, depois de a 007 fechar com "nenhuma dependência nova" | Codificação QR é padrão publicado com casos de borda reais — nível de correção, seleção de versão, máscara. É a única parte do projeto onde reimplementar um padrão seria indefensável. | Gerar no navegador foi rejeitado por transferir a integridade da imagem para código do cliente. `qrcode[pil]` foi rejeitado por arrastar Pillow e uma cadeia de bibliotecas de imagem para desenhar quadrados; a saída SVG não precisa de nenhuma. |
| Alterar `services/reservas.py`, `selectors.py` e `Screening.seats_taken`, que pertencem à 007 e à 004 | Sem a correção, o lugar **vendido** volta ao estoque dez minutos depois da compra e pode ser apagado e revendido — a falha exata que o Princípio II existe para prevenir, num caminho que nenhuma constraint pega (R3). | Empurrar `expires_at` para o futuro na aprovação resolveria com uma linha e sem tocar em nada — rejeitado porque o campo passaria a mentir: "vence em 2099" é uma flag disfarçada de data, e quebraria a exibição do prazo em toda tela que já usa o campo. Corrigir as três cópias sem unificar foi rejeitado porque uma regra de dois termos escrita três vezes é uma regra que alguém corrige em dois lugares. |
