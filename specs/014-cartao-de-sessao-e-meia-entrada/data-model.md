# Data Model: Cartão de Sessão e Meia-Entrada

**Feature**: 014 | **Date**: 2026-08-13

## O tamanho da mudança

**Uma migração, uma tabela, duas colunas.** Nada mais do modelo é tocado.

A 013 se orgulhou de zero migrações, e vale dizer por que aqui é diferente: a 013 movia para uma
tela o que o seed já fazia — nenhum fato novo entrava no sistema. Esta feature introduz um fato
novo, "por quanto este lugar foi vendido", que não existia porque só havia um preço possível.

## `ReservedSeat` — as duas colunas novas

| Coluna | Tipo | Nulo | Padrão | Editável depois |
|---|---|---|---|---|
| `ticket_type` | texto curto, escolhas `inteira` \| `meia` | não | `inteira` | **não** |
| `unit_price` | decimal(8,2) | não | — | **não** |

### `ticket_type`

Escolhas fechadas, com o padrão em `inteira`. O padrão no **banco** é o que faz o FR-016 valer para
qualquer caminho de escrita, inclusive o `seed_demo` e o shell — não só para o endpoint que valida a
entrada.

### `unit_price`

O valor efetivamente cobrado por **este** lugar, congelado no instante da reserva.

Sem padrão de propósito: um padrão aqui significaria que existe um valor razoável a gravar quando
ninguém decidiu, e não existe. Toda escrita passa por `services/reservas.py`, que sempre sabe o
preço da sessão.

**A migração precisa preencher as linhas existentes.** As reservas já criadas foram todas vendidas
como inteira ao preço da sessão delas, então o passo de dados é:

```
UPDATE reserved_seat rs
   SET unit_price = s.price,
       ticket_type = 'inteira'
  FROM screening s
 WHERE s.id = rs.screening_id
```

Isto é retrato honesto do passado: não havia meia, e o preço da sessão não muda sob reserva viva
(a 013 não permite editar sessão publicada).

### O que NÃO ganha constraint, e por quê

Não há `CHECK` amarrando `unit_price` a `screening.price`. A tentação é escrever "meia DEVE ser
metade da inteira", e ela está errada por duas razões:

1. **A `CHECK` congelaria a regra de preço no esquema.** Preço por assento (VIP) ou promoção de
   terça — ambos fora de escopo hoje — passariam a exigir migração para existir.
2. **A coluna existe justamente para ser independente do preço atual.** Uma `CHECK` que a compara
   com `screening.price` recria a dependência que o R1 corta, e quebraria retroativamente se um
   preço mudasse.

A garantia de que o valor gravado está certo é do **serviço** (`services/precos.py`, um dono só) e
dos testes. É a mesma forma da 010: nem todo invariante é expressável como índice, e fingir que é
produz esquema errado.

## O que muda de significado sem mudar de forma

### `Payment.amount`

Continua sendo decimal, continua congelado no instante da cobrança, continua calculado pelo
servidor. **Muda a origem**: era `screening.price × quantidade`, passa a ser `SUM(unit_price)`.

O comentário atual do modelo diz "calculado pelo servidor a partir do preço da sessão e da
quantidade de lugares". Essa frase fica **incorreta** com esta feature e precisa ser atualizada
junto — comentário que descreve o que o código não faz mais é pior que comentário nenhum.

### `Ticket`

**Nenhuma coluna nova.** O tipo é lido por travessia: `ticket.reserved_seat.ticket_type`.

Duplicar o tipo no ingresso criaria duas verdades sobre o mesmo lugar. O ingresso já busca sessão,
sala e assento por travessia do `reserved_seat`; o tipo entra pela mesma porta.

### `Reservation`

Intocada. Sem coluna de total — ver R2: total gravado na reserva e valores gravados nos lugares
seriam duas verdades sobre a mesma soma.

## Transições de estado

**Nenhuma nova.** O ciclo da reserva (`held → paid | expired | cancelled`) e o do ingresso
(`emitido → utilizado`) ficam exatamente como estão.

O tipo é **imutável desde a criação**: não há caminho de "trocar para meia depois". Trocar o tipo
depois de reservado mudaria o valor devido de uma reserva com prazo correndo, e trocar depois de
pago mudaria o valor de uma cobrança fechada. Quem errou o tipo deixa a reserva vencer ou compra de
novo — o mesmo remédio que já existe para quem errou o assento.

## Consultas afetadas

| Consulta | Antes | Depois |
|---|---|---|
| Total da reserva | `price × count()` | `aggregate(Sum("unit_price"))` |
| Total no serializer | `price × len(assentos)` | consome o serviço, não recalcula |
| Ocupação viva | `Reservation.OCUPANDO` | **inalterada** |
| Mapa de assentos | `situacao` por assento | **inalterada** — o painel usa como está |

**Nenhuma consulta N+1 nova.** O total vira agregação sobre linhas que a reserva já carrega por
`prefetch`; onde os lugares já estão em memória, a soma é em Python sobre a mesma lista.

## Índices

**Nenhum novo.** `ticket_type` tem cardinalidade 2 e nunca é critério de busca — não existe tela que
liste "todas as meias". Índice sobre coluna de dois valores que ninguém filtra é custo de escrita
sem contrapartida.
