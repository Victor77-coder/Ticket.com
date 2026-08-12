"""Consultas de leitura de sessão, assento e reserva.

Ficam fora das views para serem testáveis sem HTTP — mesmo padrão de
`apps/catalog/selectors.py`.
"""

from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Q,
)
from django.utils import timezone
from django.db.models.functions import Now

from apps.screening.models import (
    Reservation,
    ReservedSeat,
    Room,
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


# --- Programação do organizador (feature 013) -----------------------------
#
# ESTA É A ÚNICA SEÇÃO DO ARQUIVO QUE EXPÕE GESTÃO: estado da sessão,
# capacidade da sala e ocupação NUMÉRICA. Tudo acima serve superfície pública
# ou do dono, e nada daqui pode migrar para lá — a fronteira está escrita em
# `data-model.md` §fronteira entre painel e público.


def _ocupacao_viva_em(caminho):
    """A condição de ocupação viva, alcançada por um caminho de relação.

    CONSOME `Reservation.OCUPANDO` — não a reescreve. O `Q` de lá tem dois
    termos (paga OU não vencida) e o comentário do modelo explica por que
    nenhum basta sozinho; repeti-los aqui seria a quarta cópia de uma regra
    que a 008 consolidou justamente por já ter sido corrigida em duas de três
    cópias.

    A subconsulta `__in` é a mesma técnica de `Screening.seats_taken` e de
    `ocupacoes_vivas`, e é o que permite prefixar a regra sem transcrevê-la.
    """
    return Q(**{f"{caminho}__reservation__in": Reservation.objects.filter(Reservation.OCUPANDO)})


def grade_do_organizador():
    """A grade inteira — os três estados —, pronta para serializar.

    UMA CONSULTA, e é o ponto inteiro desta função. `Screening.seats_taken` é
    uma property que consulta o banco POR INSTÂNCIA: correta para uma sessão,
    que é como o mapa a usa, e desastrosa para uma grade de dezenas. O mesmo
    vale para contar os lugares da sala e para perguntar se a sessão está à
    venda (R6).

    `distinct=True` nos dois `Count` não é zelo: são duas junções
    multivaloradas na mesma consulta, e sem ele cada linha de uma multiplicaria
    a contagem da outra.

    `a_venda` reusa `sellable()` LITERALMENTE, por `Exists`. Reescrever
    "publicada e no futuro" aqui criaria a segunda definição de vendável — e a
    regra é de outro dono: `sellable()` responde "dá para comprar?" e nenhuma
    outra pergunta (FR-033).

    `no_futuro` usa `Now()`, a função do BANCO, pelo mesmo motivo que
    `Reservation.OCUPANDO` e `ingressos_do_cliente`: a fronteira entre futuro e
    passado é decisão do servidor, com um relógio só.
    """
    return (
        Screening.objects.select_related("movie", "room")
        .annotate(
            ocupacao=Count(
                "reserved_seats",
                filter=_ocupacao_viva_em("reserved_seats"),
                distinct=True,
            ),
            sala_lugares=Count("room__seats", distinct=True),
            a_venda=Exists(Screening.objects.sellable().filter(pk=OuterRef("pk"))),
            no_futuro=ExpressionWrapper(
                Q(starts_at__gt=Now()), output_field=BooleanField()
            ),
        )
        .order_by("starts_at", "room__name")
    )


def salas_do_organizador():
    """As salas com lugares, acessíveis e ocupação viva — também em uma consulta.

    `lugares` pode divergir de `capacity`, e a divergência é legítima: a
    geometria trunca no teto de 26 fileiras, e uma sala do seed criada acima
    disso tem menos lugares do que a capacidade declara. Por isso o número
    exibido é CONTADO, nunca lido de `capacity` (R1).

    `ocupacao_viva` atravessa todas as sessões da sala, e não uma: a pergunta
    que ela responde é "esta sala pode mudar de capacidade?", e um lugar
    vendido em qualquer sessão já responde não (FR-020).
    """
    return Room.objects.annotate(
        lugares=Count("seats", distinct=True),
        acessiveis=Count(
            "seats", filter=Q(seats__kind=Seat.Kind.ACCESSIBLE), distinct=True
        ),
        ocupacao_viva=Count(
            "screenings__reserved_seats",
            filter=_ocupacao_viva_em("screenings__reserved_seats"),
            distinct=True,
        ),
    ).order_by("name")


def ocupacao_viva_da_sala(room):
    """Quantos lugares desta sala estão ocupados, agora.

    Consumida por `services/salas.alterar_capacidade` para RECUSAR COM FRASE.
    A garantia continua sendo o PROTECT de `Seat` em `ReservedSeat.seat` — se
    esta leitura errar, o banco recusa de qualquer forma (R5).
    """
    return ocupacoes_vivas().filter(screening__room=room).count()
