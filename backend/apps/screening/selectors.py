"""Consultas de leitura de sessão, assento e reserva.

Ficam fora das views para serem testáveis sem HTTP — mesmo padrão de
`apps/catalog/selectors.py`.
"""

from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.db.models.functions import Now

from apps.screening.models import (
    Reservation,
    ReservedSeat,
    Screening,
    Seat,
    Ticket,
    TicketShareLink,
)


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


# --- Ingressos do cliente e compartilhamento (feature 009) -----------------
#
# NENHUMA consulta desta seção pode usar `sellable()` nem
# `get_sellable_screening`. A regra vale para as três, e o motivo está escrito
# por extenso em `ingressos_do_cliente`.


def _ingressos_completos():
    """A base das três consultas de ingresso, com a cadeia já resolvida.

    O serializer toca filme, sala, sessão e assento de CADA linha. Sem o
    `select_related`, doze ingressos viram dezenas de consultas — o mesmo
    caminho ingênuo que a 007 evitou no mapa de assentos com `EXISTS`.

    `test_my_tickets_api.py` fixa a contagem com `django_assert_num_queries`,
    para que remover isto quebre alguma coisa em vez de só ficar lento.
    """
    return Ticket.objects.select_related(
        "reserved_seat__seat",
        "reserved_seat__screening__movie",
        "reserved_seat__screening__room",
    )


def ingressos_do_cliente(cliente):
    """Os ingressos de um cliente, em dois grupos já ordenados.

    Devolve `(futuros, passados)`.

    NÃO USA `sellable()`, E NÃO PODE USAR. Toda consulta de sessão escrita da
    001 até a 008 passa por lá, então a linha errada aqui é mais parecida com
    o resto do projeto do que a certa. `sellable()` é `published()` E
    `starts_at > now()` — filtro de ESTOQUE, o que ainda dá para comprar.
    Ingresso emitido é HISTÓRICO, e os dois se comportam ao contrário:

      - toda sessão que já começou deixa de ser vendável → o grupo dos
        passados ficaria permanentemente vazio (FR-009);
      - toda sessão cancelada deixa de ser vendável → sumiria justamente o
        ingresso sobre o qual o cliente precisa de explicação (FR-011).

    Nenhuma constraint pega isso. A guarda é `test_my_tickets_api.py`, e ela
    é a primeira coisa daquele arquivo.

    O único filtro é o dono.

    A ORDENAÇÃO É DECLARADA, e não herdada. `Ticket.Meta.ordering` é por
    fileira e número — a ordenação certa dentro de UMA compra, e errada aqui:
    daria uma lista ordenada por poltrona em vez de por horário de sessão.
    Plausível, e errada.

    `Now()` é a função do BANCO, não `timezone.now()`: a fronteira entre
    futuro e passado é decisão do servidor (FR-010), e o relógio de
    referência tem de ser um só. É a mesma escolha que `Reservation.OCUPANDO`
    já registra.
    """
    base = _ingressos_completos().filter(
        reserved_seat__reservation__customer=cliente
    )
    inicio = "reserved_seat__screening__starts_at"

    futuros = base.filter(**{f"{inicio}__gt": Now()}).order_by(inicio)
    passados = base.filter(**{f"{inicio}__lte": Now()}).order_by(f"-{inicio}")

    return futuros, passados


def ingresso_do_dono(cliente, public_id):
    """O ingresso, se for daquele cliente. `None` em qualquer outro caso.

    Posse e identidade na MESMA consulta, de propósito: buscar primeiro e
    conferir o dono depois deixaria uma linha entre as duas em que alguém
    pode usar o objeto errado.

    Ingresso de outro cliente devolve `None`, e a view responde `404` — nunca
    `403`. Um `403` confirmaria que aquele `public_id` existe, e `public_id` é
    exatamente o valor que vai dentro do código assinado do QR.
    """
    return (
        _ingressos_completos()
        .filter(public_id=public_id, reserved_seat__reservation__customer=cliente)
        .first()
    )


def ingresso_por_token(token):
    """O link ATIVO daquele token, ou `None`.

    Token inexistente, revogado e substituído convergem para o mesmo `None`
    AQUI, na consulta — não num `if` da view (FR-043). É a mesma técnica de
    `get_sellable_screening`, que faz rascunho, cancelada, iniciada e
    inexistente saírem iguais: quando os casos convergem cedo, não sobra
    caminho por onde a distinção vaze depois.

    Distinguir entregaria a quem está adivinhando a informação de que um
    palpite chegou perto.
    """
    if not token:
        return None

    return (
        TicketShareLink.objects.filter(token=token, revoked_at__isnull=True)
        .select_related(
            "ticket__reserved_seat__seat",
            "ticket__reserved_seat__screening__movie",
            "ticket__reserved_seat__screening__room",
        )
        .first()
    )


def link_ativo(ingresso):
    """O link ativo de um ingresso, ou `None`."""
    return ingresso.share_links.filter(revoked_at__isnull=True).first()


# --- Portaria (feature 010) -----------------------------------------------


def sessoes_da_portaria():
    """As sessões que um posto de portaria pode receber hoje.

    NÃO USA `sellable()`, E NÃO PODE USAR — segunda vez no projeto que este
    filtro é o erro natural. A 009 registrou a primeira, com o histórico de
    ingressos; aqui é pior, porque some justamente a sessão que a porta está
    recebendo NESTE MOMENTO.

    `sellable()` é `published()` E `starts_at > now()`. A porta precisa
    exatamente do que o segundo termo exclui: **a sessão em andamento**. Gente
    chega atrasada, e a portaria valida durante a sessão inteira. Uma lista
    que some com a sessão em curso é uma lista que não serve à porta.

    A regra que emerge das duas aparições, e que vale para a próxima:

        `sellable()` responde "dá para comprar?", e nenhuma outra pergunta.

    Canceladas ficam fora — não há entrada a receber, e `published()` já as
    exclui. O ingresso de uma sessão cancelada continua alcançando a portaria
    pelo código e sai como "sessão errada", com o aviso do cancelamento.

    AS SESSÕES DO DIA, e não uma janela em horas: uma janela teria duas pontas
    para explicar e mudaria de resultado conforme o instante em que a tela foi
    aberta. O dia é a unidade que o operador tem na cabeça.
    """
    hoje = timezone.localdate()

    return (
        Screening.objects.published()
        .filter(starts_at__date=hoje)
        .select_related("movie", "room")
        .order_by("starts_at")
    )
