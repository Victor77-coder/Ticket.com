"""O valor de um lugar — e o dono único dessa regra.

ESTE MÓDULO EXISTE PORQUE A REGRA JÁ ESTAVA ESCRITA TRÊS VEZES. Antes da 014,
`preço × quantidade` vivia em `services/pagamentos.total_da_reserva`, de novo em
`ReservationSerializer.get_total` e uma terceira vez no navegador, em
`SeatSelection.tsx`. Ensinar meia-entrada a três cópias é como a divergência
entra: alguém corrige duas.

A saída não foi ensinar as três — foi tirar o cálculo do caminho. Com o valor
GRAVADO por lugar (`ReservedSeat.unit_price`), o total vira **soma de uma
coluna**, e as duas cópias do back-end deixam de precisar saber que tipos
existem. É o mesmo movimento da 013 com a geometria da sala.

DUAS REGRAS MORAM AQUI, E SÓ AQUI:

1. **A derivação** — meia é metade da inteira, arredondada PARA BAIXO em
   centavos. Para baixo em favor de quem compra, e determinística: o
   `ROUND_HALF_EVEN` que o `Decimal` usa por padrão faria 25,01 e 25,03
   arredondarem para lados diferentes — correto estatisticamente, incompreensível
   numa tabela de preços exibida ao cliente.

2. **O total** — soma dos valores gravados, nunca preço vezes quantidade.

O ARREDONDAMENTO ACONTECE ANTES DE GRAVAR, e é isso que faz "exibido" e
"cobrado" serem o mesmo número por construção, não por coincidência: o valor
que a tela mostra é o que foi para a coluna.

`frontend/lib/meia.ts` espelha a derivação para a prévia antes de reservar. Os
dois lados concordarem é VERIFICADO, não presumido — `test_precos.py` e
`meia.test.ts` compartilham a mesma tabela de casos.
"""

from decimal import ROUND_DOWN, Decimal

from django.db import models


class TipoDeIngresso(models.TextChoices):
    """Fechado de propósito: dois valores não são um catálogo.

    Uma tabela de tipos nasce quando existir preço por assento (VIP) ou
    categoria de meia (estudante, idoso) — ambos fora do escopo da 014.
    """

    INTEIRA = "inteira", "Inteira"
    MEIA = "meia", "Meia"


CENTAVO = Decimal("0.01")


def valor_do_lugar(preco_da_sessao, tipo):
    """Quanto custa UM lugar daquela sessão, naquele tipo.

    `ROUND_DOWN` e não o padrão do `Decimal`: `ROUND_HALF_EVEN` faria 12,505
    virar 12,50 e 12,515 virar 12,52 — dois ímpares vizinhos indo para lados
    diferentes. Correto estatisticamente, incompreensível numa tabela de preços.
    Para baixo é determinístico e é em favor de quem compra.

    Sempre com duas casas exatas, porque é este valor que vai para a coluna: um
    decimal com mais casas seria arredondado pelo banco, e aí "exibido" e
    "cobrado" divergiriam sem ninguém ter decidido isso.
    """
    if tipo == TipoDeIngresso.INTEIRA:
        return Decimal(preco_da_sessao).quantize(CENTAVO, rounding=ROUND_DOWN)

    if tipo == TipoDeIngresso.MEIA:
        return (Decimal(preco_da_sessao) / 2).quantize(CENTAVO, rounding=ROUND_DOWN)

    # Alto, e não silencioso: um tipo desconhecido caindo no ramo da meia seria
    # desconto concedido por engano de digitação.
    raise ValueError(f"Tipo de ingresso desconhecido: {tipo!r}")


def total_da_reserva(reserva):
    """A soma do que foi gravado — nunca preço vezes quantidade.

    ESTA FUNÇÃO SUBSTITUIU DUAS CÓPIAS da mesma multiplicação, uma em
    `pagamentos.py` e outra no `ReservationSerializer`. Depois da 014 nenhuma das
    duas precisa saber que tipos existem: o valor já está decidido na linha.

    Soma em Python e não `aggregate(Sum(...))` de propósito — os lugares já vêm
    carregados no caminho da reserva e do pagamento, e uma agregação faria uma
    ida ao banco a mais para somar o que está na memória. Onde não estiverem,
    `seats.all()` é o mesmo `prefetch` que o serializer já usa.
    """
    return sum(
        (lugar.unit_price for lugar in reserva.seats.all()),
        Decimal("0.00"),
    )
