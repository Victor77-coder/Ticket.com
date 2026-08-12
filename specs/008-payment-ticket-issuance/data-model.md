# Phase 1 — Data Model: Pagamento Simulado e Emissão do Ingresso

**Feature**: `008-payment-ticket-issuance` | **Date**: 2026-08-11

Dois modelos novos, duas constraints, um estado novo em `Reservation` e **uma correção na regra de
ocupação que a 007 deixou incompleta**. Tudo numa migração só — separar a aprovação da emissão,
mesmo por um commit, é o que o Princípio II proíbe.

---

## A linha que sai do `models.py`

Desde a 007, `apps/screening/models.py` termina o docstring assim:

> `Ticket` permanece fora: emissão de ingresso é a próxima feature.

**Esta é a próxima feature.** A linha sai, e no lugar entra o registro de que `Payment` e `Ticket`
nasceram na mesma migração — pelo mesmo motivo que `ReservedSeat` e sua constraint nasceram juntas.

---

## `screening.Payment`

Uma tentativa de cobrança simulada sobre uma reserva.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `reservation` | FK → `Reservation` | `related_name="payments"`, `on_delete=PROTECT` |
| `status` | varchar(12) | `approved` \| `declined` |
| `decline_reason` | varchar(32) | vazio quando aprovado |
| `amount` | decimal(8,2) | congelado no instante da cobrança |
| `card_last4` | varchar(4) | **só isto do cartão** |
| `card_brand` | varchar(16) | derivado do prefixo |
| `created_at` | datetime | auto |

**Constraints**

```
UniqueConstraint(
    fields=["reservation"],
    condition=Q(status="approved"),
    name="um_pagamento_aprovado_por_reserva",
)
```

**Índice parcial, e desta vez ele é possível.** A 007 quis um índice parcial e não pôde: o
predicado dependeria de `now()`, que o PostgreSQL recusa em índice (R1 da 007). Aqui o predicado é
`status = 'approved'` — literal contra coluna, imutável, legítimo.

É essa possibilidade que permite guardar **todas** as tentativas recusadas, como FR-012 exige, sem
que a unicidade as proíba. Uma `UNIQUE(reservation)` sem condição impediria a segunda tentativa,
que é justamente o que a US2 promete ao cliente.

**O que não é guardado**: número completo, código de segurança, validade, nome impresso. Não há
cobrança real — guardar o número seria risco sem contrapartida (R10).

**`decline_reason` é chave, não frase.** A frase em português vive na camada de apresentação. Um
motivo gravado como texto livre vira texto divergente entre o banco e a tela na primeira revisão de
redação.

---

## `screening.Ticket`

O direito de uma pessoa entrar na sala. **Um por lugar reservado**, nunca um por reserva.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | interno, nunca exposto |
| `public_id` | uuid | **identidade pública**, indexada, única |
| `reserved_seat` | **OneToOne** → `ReservedSeat` | `related_name="ticket"`, `on_delete=PROTECT` |
| `payment` | FK → `Payment` | `related_name="tickets"`, `on_delete=PROTECT` |
| `issued_at` | datetime | auto |

**A constraint**

`OneToOneField` **é** `UNIQUE` na coluna — essa é a garantia, e ela é **absoluta, sem predicado**.
Nenhuma sequência de operações produz dois ingressos para o mesmo assento reservado.

> **Não trocar por `ForeignKey`.** A troca não muda uma linha de lógica visível e remove a
> garantia inteira. É a mesma classe de erro que enfraquecer a constraint da 007 com um
> `condition`.

**Por que `public_id` além da PK**: o código do QR carrega essa identidade, e um sequencial
revelaria quantos ingressos existem e convidaria a tentar o vizinho (FR-032). A PK continua
existindo para junção interna; ela não sai daqui.

**Por que a ligação é com `ReservedSeat` e não com `(Reservation, Seat)`**: `ReservedSeat` já é a
linha que representa "este lugar, nesta sessão, é desta reserva" — e já carrega a constraint da
007. Pendurar o ingresso nela faz a unicidade do ingresso herdar a unicidade do assento: como não
existem duas ocupações do mesmo lugar, não existem dois ingressos para o mesmo lugar.

**Nenhum campo `used` / `used_at` nesta feature.** A transição para "utilizado" e a garantia de
validação única nascem juntas na feature da portaria — o mesmo cuidado da 007 com `ReservedSeat` e
sua constraint. Acrescentar a coluna agora criaria um estado que nada transiciona e nada protege.

---

## `screening.Reservation` — o que muda

**Um valor novo em `Status`:**

```
              expira o prazo
   held ─────────────────────────► expired
     │
     ├──── pagamento aprovado ───► paid        ← NOVO
     │
     └──── (cancelamento: fora de escopo) ───► cancelled
```

`paid` é **terminal**. Não há estorno nesta feature.

A 007 já previu isto ao escrever, em `Reservation.is_expired`:

> `status` é registro histórico e serve à feature de pagamento para distinguir "venceu" de "foi
> paga".

**`is_expired` não muda de definição.** Continua lendo o relógio, e uma reserva paga cujo prazo
passou continua respondendo `True` — porque a pergunta "o prazo venceu?" tem essa resposta. O que
muda é quem pergunta: a partir daqui, ninguém decide ocupação só com `is_expired`.

---

## A regra de ocupação viva — a correção que sustenta tudo

**Este é o ponto de maior risco da feature.** Detalhado em R3.

Hoje a regra é `expires_at > now()`, escrita **três vezes** em três formas:

| Onde | Como está |
|---|---|
| `selectors.ocupacoes_vivas` | `filter(reservation__expires_at__gt=now())` |
| `Screening.seats_taken` | a mesma linha, copiada |
| `services/reservas._liberar_ou_recusar` | `if ocupacao.reservation.expires_at <= agora` — em Python |

Uma reserva **paga** não mexe em `expires_at`. Dez minutos depois da compra ela vira, para essa
regra, indistinguível de uma reserva abandonada — e a terceira cópia **apaga a ocupação** e entrega
o lugar vendido a outro cliente, sem violar constraint nenhuma.

**A nova regra, em um lugar só:**

```python
class Reservation(models.Model):
    # A ocupação está viva quando a reserva foi paga OU ainda não venceu.
    #
    # Os dois termos são necessários e nenhum basta:
    #   - só o prazo  → o lugar vendido volta ao estoque no vencimento
    #   - só o status → o lugar fica preso enquanto ninguém marca a expiração,
    #                   e marcar exigiria a rotina agendada que a 007 evitou
    OCUPANDO = Q(status=Status.PAID) | Q(expires_at__gt=Now())
```

Os três pontos passam a consumir esse predicado. **Consumir, não copiar**: uma regra com dois
termos escrita três vezes é uma regra que alguém vai corrigir em dois lugares.

`_liberar_ou_recusar` ganha a exigência mais dura: **nunca apagar ocupação de reserva paga**. Não é
"não deveria" — a linha de uma reserva paga não é linha morta, e apagá-la é a única falha desta
feature que o banco aceita sem reclamar.

---

## A transação de pagamento

```
com transação atômica:

  1. bloqueia a reserva                    SELECT ... FOR UPDATE
  2. revalida SOB o bloqueio:
        é do cliente · não vencida · não paga · sessão ainda vendável
  3. autoriza (determinístico, pelo número do cartão)
  4. RECUSADO → grava Payment(declined) e RETORNA
                a reserva não muda: nem status, nem expires_at
  5. APROVADO → grava Payment(approved)
              → Reservation.status = paid
              → cria um Ticket por ReservedSeat da reserva
              → violação de unicidade → "esta reserva já foi paga"
```

**Quatro detalhes que não podem ser trocados de ordem ou de forma:**

- **A revalidação vem depois do bloqueio.** Ler o estado antes de travar é o padrão que a
  concorrência quebra: duas requisições leem "não paga", ambas seguem.
- **O passo 4 retorna, não levanta.** Uma recusa que sobe como exceção desfaz o `INSERT` do próprio
  registro de recusa junto com o rollback, e o rastro exigido por FR-012 desaparece (R8).
- **Aprovação e emissão estão dentro da mesma transação.** É literalmente o Princípio II: não
  existe instante durável em que a reserva esteja paga e sem ingresso.
- **A violação de unicidade no passo 5 é resultado esperado**, como na 007 — vira "esta reserva já
  foi paga", nunca `500`.

**A diferença a favor em relação à 007**: lá, um assento nunca ocupado não tinha linha para travar,
e a constraint era o único árbitro (R3 da 007). Aqui a linha da reserva sempre existe, então o
bloqueio serializa de verdade. A constraint continua obrigatória — e o teste de concorrência
continua tendo de **falhar** sem ela.

---

## O código do ingresso

Derivado, **nunca armazenado**:

```
codigo = signing.dumps(
    {"t": ticket.public_id, "s": screening_id},
    key=settings.TICKET_SIGNING_KEY,
    salt="ingresso.qr",
)
```

| Decisão | Por quê |
|---|---|
| Chave **própria**, não a `SECRET_KEY` | Vazar a chave da aplicação compromete sessões; vazar a do ingresso compromete a catraca. Amarrar as duas faz um incidente virar dois (FR-031) |
| `salt` de domínio além da chave | Uma assinatura de ingresso não vale em nenhum outro contexto |
| Não armazenado em coluna | É derivável; guardá-lo criaria a chance de a coluna e a chave discordarem |
| Carrega a **sessão** | A portaria precisa distinguir "sessão errada" de "inválido" — dois dos quatro desfechos do Princípio III (FR-033) |
| Verificado **sem tocar o banco** | FR-034, com teste de `num_queries == 0` (R7) |

---

## O que muda no que já existe

| Onde | O quê |
|---|---|
| `screening/models.py` | Sai "Ticket permanece fora"; entram `Payment`, `Ticket`, `Status.PAID` e o predicado `OCUPANDO` |
| `Screening.seats_taken` | Passa a consumir `OCUPANDO` em vez da cópia do filtro |
| `selectors.ocupacoes_vivas` | Idem |
| `services/reservas._liberar_ou_recusar` | Idem — e **nunca apaga ocupação de reserva paga** |
| `config/settings/base.py` | `TICKET_SIGNING_KEY` e a tabela de cartões |
| `.env.example` | `TICKET_SIGNING_KEY`, sem valor padrão utilizável |

**Nenhuma asserção das features 001–007 muda** (FR-049). Uma reserva paga é um estado que nenhum
teste anterior conseguia produzir, então nenhum deles observa a diferença.

---

## O que NÃO é criado

| Não criado | Por quê |
|---|---|
| `Ticket.used_at` e a transição para "utilizado" | Nasce junto da garantia de validação única, na feature da portaria — o mesmo cuidado da 007 |
| Estorno, cancelamento de compra | `paid` é terminal nesta feature |
| Token de compartilhamento de ingresso | Feature seguinte |
| Coluna com o código assinado | Derivável; armazenar só cria divergência possível |
| Provedor de pagamento, webhook, conciliação | A cobrança é simulada, sem serviço externo (FR-005) |
| Rotina que marque reservas vencidas | A liberação continua por consulta, como na 007 |
