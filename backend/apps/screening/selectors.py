"""Consultas de leitura de sessão, assento e reserva.

Ficam fora das views para serem testáveis sem HTTP — mesmo padrão de
`apps/catalog/selectors.py`.
"""

from django.db.models import Exists, OuterRef

from apps.screening.models import Reservation, ReservedSeat, Screening, Seat


def get_sellable_screening(pk):
    """A sessão do mapa, ou None.

    Rascunho, cancelada, já iniciada e inexistente convergem para o mesmo
    None de propósito: a view devolve uma 404 só para os quatro casos, porque
    distinguir revelaria a grade interna de programação (FR-003).
    """
    return (
        Screening.objects.select_related("movie", "room")
        .sellable()
        .filter(pk=pk)
        .first()
    )


def ocupacoes_vivas(screening=None):
    """Ocupações que tiram o lugar do estoque.

    Duas coisas tiram: a reserva estar **paga**, ou o prazo dela ainda não
    ter vencido. A regra mora em `Reservation.OCUPANDO` e é **consumida**
    daqui, nunca copiada — antes da 008 ela estava escrita em três lugares, e
    ganhar um segundo termo em duas cópias e não na terceira era o modo mais
    provável de esta feature vender o mesmo lugar duas vezes.

    O vencimento continua sendo lido do relógio a cada consulta. Não há
    rotina agendada marcando reservas como expiradas — se houvesse, existiria
    uma janela entre o vencimento e a passagem da rotina, e nessa janela o
    lugar apareceria tomado sem estar.
    """
    consulta = ReservedSeat.objects.filter(
        reservation__in=Reservation.objects.filter(Reservation.OCUPANDO)
    )
    if screening is not None:
        consulta = consulta.filter(screening=screening)
    return consulta


def get_seat_map(screening):
    """Os assentos da sala, anotados com a ocupação daquela sessão.

    **Uma** consulta, não uma por assento: a anotação é feita por subconsulta
    `EXISTS`, que o PostgreSQL resolve dentro do mesmo plano. Sessenta lugares
    dariam sessenta consultas no caminho ingênuo (R8).
    """
    ocupado = Exists(ocupacoes_vivas(screening).filter(seat=OuterRef("pk")))

    return (
        Seat.objects.filter(room=screening.room)
        .annotate(is_taken=ocupado)
        .order_by("row", "number")
    )


def get_seats_for_reservation(screening, seat_ids):
    """Os assentos pedidos que realmente pertencem à sala da sessão.

    A conferência é do servidor: um identificador de assento de outra sala
    chegando pela requisição não pode virar ocupação, e devolver menos do que
    foi pedido é como a camada de cima descobre isso.
    """
    return list(
        Seat.objects.filter(room=screening.room, pk__in=seat_ids).order_by("row", "number")
    )
