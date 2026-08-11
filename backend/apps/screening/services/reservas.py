"""A transação de reserva — o coração da feature 007.

Fica fora da view de propósito: é lógica de negócio com regra de
concorrência, não serialização nem roteamento. Na view seria intestável sem
HTTP, justo onde o teste precisa de threads (ver tests/test_reservation_concurrency.py).

A ORDEM DAS OPERAÇÕES NÃO É ESTILO. Trocar duas delas quebra a garantia:

    1. valida que a sessão é vendável
    2. BLOQUEIA as ocupações daqueles assentos      (SELECT ... FOR UPDATE)
    3. para cada linha bloqueada:
           reserva vencida → apaga
           reserva viva    → recusa a reserva INTEIRA
    4. cria a Reservation
    5. cria as ReservedSeat

O bloqueio vem ANTES de apagar. Apagar primeiro deixaria duas transações
removerem a mesma linha vencida e ambas seguirem para inserir (R2).

E a violação de unicidade no passo 5 é RESULTADO ESPERADO, não falha de
sistema: é a rede pegando o que o bloqueio não cobriu. Assento nunca antes
ocupado não tem linha para bloquear, então o passo 2 não trava nada e a
constraint é a única coisa entre duas inserções simultâneas (R3).
"""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.screening.models import Reservation, ReservedSeat, Screening, Seat


class ReservaRecusada(Exception):
    """Raiz das recusas de negócio. Nenhuma delas é erro de sistema."""


class SessaoIndisponivel(ReservaRecusada):
    """Sessão inexistente, em rascunho, cancelada ou já iniciada."""


class SelecaoInvalida(ReservaRecusada):
    """A seleção não pode virar reserva como está."""

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


class AssentoIndisponivel(ReservaRecusada):
    """Algum lugar da seleção deixou de estar livre.

    Carrega quais foram, porque "escolha outro" sem dizer qual obriga a
    pessoa a tentar de novo às cegas (FR-019).
    """

    def __init__(self, assentos):
        self.assentos = list(assentos)
        nomes = ", ".join(f"{s.row}{s.number}" for s in self.assentos)
        plural = "os lugares" if len(self.assentos) > 1 else "o lugar"
        super().__init__(f"{plural} {nomes} acabou de ser reservado")


def prazo_da_reserva():
    return timezone.now() + timedelta(minutes=settings.RESERVATION_HOLD_MINUTES)


def _validar_selecao(sessao, seat_ids):
    """Confere a seleção contra a sala, antes de qualquer escrita.

    A conferência é do servidor: identificadores chegam pela requisição e
    não podem ser tomados por verdadeiros. Esconder um lugar na interface
    não impede ninguém de pedi-lo pela API.
    """
    ids = list(dict.fromkeys(seat_ids))  # remove repetição preservando a ordem

    if not ids:
        raise SelecaoInvalida("Escolha ao menos um lugar.")

    limite = settings.MAX_SEATS_PER_RESERVATION
    if len(ids) > limite:
        raise SelecaoInvalida(f"São no máximo {limite} lugares por reserva.")

    assentos = list(Seat.objects.filter(room=sessao.room, pk__in=ids).order_by("row", "number"))

    if len(assentos) != len(ids):
        raise SelecaoInvalida("Algum lugar escolhido não existe nesta sala.")

    acessiveis = [s for s in assentos if s.kind == Seat.Kind.ACCESSIBLE]
    if acessiveis:
        nomes = ", ".join(f"{s.row}{s.number}" for s in acessiveis)
        raise SelecaoInvalida(
            f"O lugar {nomes} é reservado para acessibilidade e não está na venda comum."
        )

    return assentos


def _liberar_ou_recusar(sessao, assentos):
    """Passos 2 e 3 — o bloqueio e a reciclagem.

    `select_for_update()` trava as linhas de ocupação **daqueles** assentos,
    não a sessão inteira: duas pessoas escolhendo lugares distintos da mesma
    sessão precisam conseguir as duas.

    Quando não existe linha nenhuma — assento nunca ocupado — não há o que
    travar, e é a constraint que arbitra lá no passo 5. Isso não é falha do
    bloqueio: é a divisão de trabalho entre os dois mecanismos.
    """
    ocupacoes = list(
        ReservedSeat.objects.select_for_update()
        .filter(screening=sessao, seat__in=assentos)
        .select_related("reservation", "seat")
    )

    agora = timezone.now()
    vencidas = []
    vivas = []

    for ocupacao in ocupacoes:
        if ocupacao.reservation.expires_at <= agora:
            vencidas.append(ocupacao)
        else:
            vivas.append(ocupacao.seat)

    if vivas:
        # A reserva inteira é recusada, nunca parcial: reservar "o que
        # sobrou" entrega algo diferente do que a pessoa escolheu (FR-019).
        raise AssentoIndisponivel(vivas)

    if vencidas:
        # A linha morta só é removida aqui, sob o bloqueio. É o que concilia
        # a constraint absoluta com a expiração, sem rotina agendada (R2).
        ReservedSeat.objects.filter(pk__in=[o.pk for o in vencidas]).delete()


def criar_reserva(cliente, sessao, seat_ids, chave):
    """Cria a reserva, ou recusa por inteiro.

    Devolve `(reserva, criada)`. `criada` é False quando a chave de
    idempotência já tinha sido usada — o envio duplo devolve a reserva
    existente em vez de criar outra.
    """
    if sessao.status != Screening.Status.PUBLISHED or sessao.starts_at <= timezone.now():
        raise SessaoIndisponivel()

    # A idempotência é conferida ANTES da disponibilidade, e a ordem não é
    # arbitrária: na segunda tentativa os lugares estão ocupados — pela
    # primeira tentativa, da mesma pessoa. Conferir disponibilidade primeiro
    # faria o reenvio bater em "acabou de ser reservado", acusando a pessoa
    # de ter perdido o lugar para si mesma.
    #
    # Isto refina o R9, que dizia "nunca por consulta prévia". A consulta
    # prévia resolve o reenvio SEQUENCIAL; ela não resolve — e não substitui
    # — o envio SIMULTÂNEO, onde duas requisições consultam ao mesmo tempo,
    # nenhuma encontra, e ambas criam. Esse caso continua sendo resolvido
    # pela UNIQUE(idempotency_key) lá em `_traduzir_violacao`, e tem teste
    # próprio com threads. Os dois mecanismos são necessários; nenhum basta.
    existente = Reservation.objects.filter(idempotency_key=chave).first()
    if existente is not None:
        if existente.customer_id != cliente.pk:
            raise SelecaoInvalida(
                "Não foi possível registrar esta reserva. Tente de novo."
            )
        return existente, False

    assentos = _validar_selecao(sessao, seat_ids)

    try:
        with transaction.atomic():
            _liberar_ou_recusar(sessao, assentos)

            reserva = Reservation.objects.create(
                screening=sessao,
                customer=cliente,
                expires_at=prazo_da_reserva(),
                idempotency_key=chave,
            )

            ReservedSeat.objects.bulk_create(
                [
                    # `screening` é copiado de `sessao` AQUI, no único ponto
                    # do código que cria ocupação, e nunca é editado depois.
                    # É o que mantém a denormalização honesta.
                    ReservedSeat(reservation=reserva, screening=sessao, seat=assento)
                    for assento in assentos
                ]
            )
    except IntegrityError as erro:
        return _traduzir_violacao(erro, cliente, sessao, assentos, chave)

    return reserva, True


def _traduzir_violacao(erro, cliente, sessao, assentos, chave):
    """A violação de unicidade é resultado esperado, não erro de sistema.

    Duas constraints podem estourar aqui, e cada uma quer dizer uma coisa
    diferente para quem está comprando:

      - `unico_assento_por_sessao` → outra pessoa levou o lugar entre o
        bloqueio e a inserção. Vira recusa com o nome do lugar.
      - `idempotency_key`          → é a mesma pessoa mandando de novo. Vira
        a reserva que já existe.

    Tratar qualquer uma delas como 500 esconderia justamente o mecanismo que
    mais importa no sistema.

    A distinção é pelo nome da constraint no texto do erro. É o que o
    PostgreSQL oferece, e por isso os nomes das constraints são estáveis e
    têm teste fixando-os (test_reservation_concurrency.py).
    """
    texto = str(erro)

    if "idempotency_key" in texto:
        existente = Reservation.objects.filter(idempotency_key=chave).first()
        if existente is not None and existente.customer_id == cliente.pk:
            return existente, False
        # Chave de outra pessoa: não devolvemos a reserva alheia nem
        # confirmamos que ela existe.
        raise SelecaoInvalida("Não foi possível registrar esta reserva. Tente de novo.")

    if "unico_assento_por_sessao" in texto:
        vivos = ReservedSeat.objects.filter(
            screening=sessao, seat__in=assentos
        ).values_list("seat_id", flat=True)
        perdidos = [s for s in assentos if s.pk in set(vivos)] or assentos
        raise AssentoIndisponivel(perdidos)

    raise
