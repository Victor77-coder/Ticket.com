# Phase 1 — Data Model: Escolha de Assentos

**Feature**: `007-seat-selection` | **Date**: 2026-08-11

Três modelos novos e uma constraint. **Tudo numa migração só** — separar o modelo da constraint,
mesmo por um commit, é exatamente o que o Princípio II proíbe.

---

## A fronteira que esta feature atravessa

Desde a `001`, `apps/screening/models.py` carrega este aviso:

> **FRONTEIRA COM A FEATURE DE RESERVA — não adicionar aqui:** modelos `Seat`, `Reservation`,
> `Ticket`; a constraint `UNIQUE(screening, seat)`; qualquer coluna que materialize ocupação.

Quatro features passaram por perto e respeitaram. A `004` chegou a criar `seats_taken` como
propriedade derivada retornando zero, com o comentário "quando a feature de reserva chegar, esta
propriedade passa a contar os ingressos confirmados — sem migração de dados aqui".

**Esta é a feature.** O aviso sai do arquivo e é substituído pela constraint que ele exigia.

`Ticket` **continua fora**: emissão de ingresso é a próxima feature.

---

## `screening.Seat`

Um lugar físico da sala. O mesmo em todas as sessões dela.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `room` | FK → `Room` | `related_name="seats"`, `on_delete=CASCADE` |
| `row` | varchar(2) | letra da fileira — "A", "B"… |
| `number` | positive int | 1 a 10 dentro da fileira |
| `kind` | varchar(16) | `common` \| `accessible` |

**Constraints**

- `UNIQUE(room, row, number)` — a sala não tem dois lugares na mesma posição.

**Índices**: `(room, row, number)` já vem da constraint e é a ordem de leitura do mapa.

**Por que persistido e não derivado da capacidade** (R6): a ocupação precisa apontar para o
assento por chave estrangeira, e chave estrangeira exige linha. Derivar serviria para desenhar,
não para garantir.

---

## `screening.Reservation`

A intenção de compra de um cliente para uma sessão. É a unidade que segue ao pagamento.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `screening` | FK → `Screening` | `on_delete=PROTECT` |
| `customer` | FK → `User` | `on_delete=PROTECT` |
| `status` | varchar(12) | `held` \| `expired` \| `cancelled` |
| `expires_at` | datetime | obrigatório |
| `idempotency_key` | uuid | **único** |
| `created_at` | datetime | auto |

**Constraints**

- `UNIQUE(idempotency_key)` — envio duplo devolve a reserva existente em vez de criar outra
  (R9, FR-023).

**Estados**

```
              expira o prazo
   held ─────────────────────────► expired
     │
     └──── (pagamento: próxima feature) ────► paid
```

`cancelled` existe no vocabulário mas **nenhum caminho desta feature o produz** — cancelamento
pelo cliente está fora de escopo. Fica declarado para que a próxima feature não precise de
migração para acrescentá-lo.

**`expired` é registro, não gatilho**: a leitura considera vencida toda reserva cujo `expires_at`
já passou, independentemente do `status`. A coluna existe para histórico e para a próxima feature
distinguir "venceu" de "foi paga"; ela **não** é o que libera o assento.

**Prazo**: 10 minutos, em `RESERVATION_HOLD_MINUTES`.

---

## `screening.ReservedSeat` — onde a garantia vive

A ocupação de um lugar por uma reserva. **É esta tabela que carrega o Princípio II.**

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `reservation` | FK → `Reservation` | `related_name="seats"`, `on_delete=CASCADE` |
| `screening` | FK → `Screening` | **denormalizado** — ver abaixo |
| `seat` | FK → `Seat` | `on_delete=PROTECT` |

**A constraint**

```
UniqueConstraint(fields=["screening", "seat"], name="unico_assento_por_sessao")
```

**Absoluta, sem predicado** (R1). Nenhuma sequência de operações, nenhum bug de aplicação e
nenhum acesso direto ao banco produz duas ocupações do mesmo lugar na mesma sessão.

### Por que `screening` está duplicado aqui

`reservation.screening` já tem a informação. A duplicação existe por uma razão só: **a constraint
precisa das duas colunas na mesma tabela**, e nem o Django nem o PostgreSQL declaram unicidade
através de travessia de chave estrangeira.

Alternativas e por que não (R5):

| Alternativa | Por que não |
|---|---|
| `UNIQUE(reservation, seat)` | Impede repetir o assento **dentro** de uma reserva — problema errado. Duas reservas ainda tomariam o mesmo lugar. |
| Gatilho de banco | Funciona sem duplicar, mas move a regra para fora do modelo, onde some da leitura do código. |
| Uma reserva por assento | A constraint ficaria natural, mas comprar três lugares viraria três reservas e três pagamentos. |

**Como a duplicação não vira inconsistência**: `screening` é preenchido a partir de
`reservation.screening` num único ponto do código — o serviço de reserva — e nunca é editável
depois.

---

## A transação — o coração da feature

```
com transação atômica:

  1. valida que a sessão é publicada e futura
  2. bloqueia as ocupações daqueles assentos naquela sessão
         SELECT ... WHERE screening=S AND seat IN (...) FOR UPDATE
  3. para cada ocupação bloqueada:
         reserva vencida  → apaga a linha
         reserva viva     → recusa a reserva INTEIRA
  4. cria a Reservation
  5. cria as ReservedSeat
         se estourar violação de unicidade → recusa com "acabou de ser tomado"
```

**Três detalhes que não podem ser trocados de ordem:**

- O bloqueio vem **antes** de apagar. Apagar primeiro deixaria duas transações removerem a mesma
  linha vencida e ambas seguirem para inserir (R2).
- A recusa é da **reserva inteira**, nunca parcial. Reservar "o que sobrou" entrega algo diferente
  do que a pessoa escolheu (FR-019).
- A violação de unicidade no passo 5 é **resultado esperado**, não erro de sistema. É a rede
  pegando o que o bloqueio deixou passar (R3).

---

## Consulta de disponibilidade

Uma consulta por mapa, nunca uma por assento (R8).

```
assentos da sala da sessão
  anotados com "ocupado" = existe ReservedSeat para (esta sessão, este assento)
                           cuja reserva tem expires_at > agora
  ordenados por fileira, número
```

Reserva vencida **não** conta como ocupação — sem depender de rotina ter passado.

---

## O que muda no que já existe

| Onde | O quê |
|---|---|
| `screening/models.py` | O aviso de fronteira sai; a constraint entra |
| `Screening.seats_taken` | Deixa de retornar zero e passa a contar — **sem migração de dados**, como a 004 previu |
| `Screening.has_available_seats` | Passa a refletir ocupação real |
| `seed_demo` | Gera os assentos das salas |

`has_available_seats` já é consumido pelo cartão da home e pelo painel de destaques. A partir
daqui ele diz a verdade — e o estado "esgotado", que a 004 desenhou e nunca pôde exercitar, passa
a acontecer.

---

## O que NÃO é criado

| Não criado | Por quê |
|---|---|
| `Ticket` | Emissão de ingresso é a próxima feature |
| `Payment` | Idem |
| Rotina de expiração | A liberação é por consulta; uma rotina criaria a janela que ela evita |
| Bloqueio de assento pelo organizador | Não há painel de organizador |
| Histórico de mudança de assento | Não há troca de assento no escopo |
