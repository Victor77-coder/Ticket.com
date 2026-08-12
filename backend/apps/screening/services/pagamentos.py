"""A transação de pagamento — o coração da feature 008.

Fica fora da view pelo mesmo motivo que `reservas.py`: é lógica de negócio com
regra de concorrência, não serialização nem roteamento. Na view seria
intestável sem HTTP, justo onde o teste precisa de threads (ver
tests/test_payment_concurrency.py).

A ORDEM DAS OPERAÇÕES NÃO É ESTILO. Trocar duas delas quebra a garantia:

    1. BLOQUEIA a reserva                     (SELECT ... FOR UPDATE)
    2. revalida SOB o bloqueio:
           é do cliente · não vencida · não paga · sessão ainda vendável
    3. autoriza (determinístico, pelo número do cartão)
    4. RECUSADO → grava Payment(declined) e RETORNA
                  a reserva não muda: nem status, nem expires_at
    5. APROVADO → grava Payment(approved)
                → marca a reserva como paga
                → cria um Ticket por ReservedSeat

A revalidação vem DEPOIS do bloqueio. Ler o estado antes de travar é o padrão
que a concorrência quebra: duas requisições leem "não paga", ambas seguem.

Aprovação e emissão estão dentro da MESMA transação, e isso é literalmente o
Princípio II: "pagamento aprovado DEVE emitir o ingresso; não existe estado
intermediário durável em que o assento esteja preso sem dono". Uma reserva
`paid` sem ingresso é esse estado.

DIFERENÇA A FAVOR EM RELAÇÃO À 007: lá, um assento nunca ocupado não tinha
linha para o `SELECT FOR UPDATE` travar, e a constraint era o único árbitro
(R3 da 007). Aqui a linha da reserva SEMPRE existe, então o bloqueio serializa
de verdade. A constraint continua obrigatória — é a garantia que a
constitution exige do banco, e o teste de concorrência precisa falhar sem ela.
"""

from dataclasses import dataclass, field

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.screening.models import Payment, Reservation, Screening, Ticket


# --- Entrada e saída --------------------------------------------------------


@dataclass(frozen=True)
class Cartao:
    """Os dados digitados. NADA disto é persistido além dos 4 últimos.

    Não há cobrança real, então guardar o número não tem nem a desculpa de
    recobrança — seria risco puro sem contrapartida (FR-011).
    """

    numero: str
    nome: str = ""
    validade: str = ""
    cvv: str = ""


@dataclass(frozen=True)
class Resultado:
    pagamento: Payment
    aprovado: bool
    ingressos: list = field(default_factory=list)


# --- Recusas que NÃO são recusa de cartão -----------------------------------


class PagamentoRecusado(Exception):
    """Raiz dos estados que impedem cobrar. Nenhum é erro de sistema."""


class CartaoInvalido(PagamentoRecusado):
    """Preenchimento inválido — vira 400, não 402.

    É coisa diferente de uma recusa de cobrança: aqui a pessoa corrige o que
    digitou, lá ela troca de cartão (FR-010).
    """

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


class ReservaVencida(PagamentoRecusado):
    """O prazo acabou. Nada é cobrado e nada é emitido (FR-023)."""


class ReservaJaPaga(PagamentoRecusado):
    """Segunda tentativa sobre reserva já paga — ou a corrida perdida.

    Vem de duas origens indistinguíveis para o cliente: a revalidação sob
    bloqueio encontrou a reserva já paga, ou a constraint
    `um_pagamento_aprovado_por_reserva` estourou na inserção. A segunda NÃO é
    erro de sistema — é a rede pegando o que o bloqueio deixou passar.
    """


class ReservaCancelada(PagamentoRecusado):
    """Reserva cancelada não vira compra (FR-024)."""


class SessaoIndisponivel(PagamentoRecusado):
    """A sessão foi cancelada ou já começou (FR-025)."""


# --- A cobrança simulada ----------------------------------------------------


def _apenas_digitos(valor):
    return "".join(c for c in str(valor or "") if c.isdigit())


def _luhn_valido(numero):
    """O dígito verificador que todo cartão real tem.

    Serve para separar "digitou errado" de "o banco recusou" — sem ele, um
    número truncado viraria aprovação, porque não está na tabela de recusa.
    """
    if len(numero) != 16:
        return False

    total = 0
    for indice, digito in enumerate(reversed(numero)):
        n = int(digito)
        if indice % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _bandeira(numero):
    if numero.startswith("4"):
        return "visa"
    if numero[:2] in {"51", "52", "53", "54", "55"}:
        return "mastercard"
    if numero.startswith(("34", "37")):
        return "amex"
    return "outro"


def _validar_cartao(cartao):
    """Forma, não desfecho. Devolve o número normalizado.

    Validade e CVV são conferidos quanto à forma e **não participam** da
    decisão de aprovar ou recusar — essa é do número (R9). Isso mantém a
    tabela do README como única fonte do desfecho.
    """
    numero = _apenas_digitos(cartao.numero)

    if not numero:
        raise CartaoInvalido("Informe o número do cartão.")
    if not _luhn_valido(numero):
        raise CartaoInvalido("Confira o número do cartão.")

    if not (cartao.nome or "").strip():
        raise CartaoInvalido("Informe o nome impresso no cartão.")

    validade = _apenas_digitos(cartao.validade)
    if len(validade) not in (4, 6):
        raise CartaoInvalido("Confira a validade do cartão, no formato MM/AAAA.")
    mes = int(validade[:2])
    if not 1 <= mes <= 12:
        raise CartaoInvalido("Confira a validade do cartão, no formato MM/AAAA.")

    if len(_apenas_digitos(cartao.cvv)) not in (3, 4):
        raise CartaoInvalido("Confira o código de segurança.")

    return numero


def autorizar(numero):
    """A decisão. Determinística, pela tabela do README.

    Devolve o motivo da recusa, ou `None` quando aprova.
    """
    return settings.PAYMENT_DECLINE_CARDS.get(numero)


# --- A transação ------------------------------------------------------------


def total_da_reserva(reserva):
    """Calculado pelo SERVIDOR, sempre.

    Valor vindo do cliente não é aceito em nenhuma forma, nem para
    conferência — aceitar "só para conferir" é como o desconto de 99% entra
    (FR-003).
    """
    return reserva.screening.price * reserva.seats.count()


def _revalidar(reserva, cliente):
    """Passo 2 — sob o bloqueio, nunca antes dele."""
    if reserva.customer_id != cliente.pk:
        # A view já filtra pelo dono; esta é a segunda tranca, para o caso de
        # o serviço ser chamado de outro lugar (comando, teste, futura fila).
        raise ReservaVencida()

    if reserva.status == Reservation.Status.PAID:
        raise ReservaJaPaga()
    if reserva.status == Reservation.Status.CANCELLED:
        raise ReservaCancelada()
    if reserva.is_expired:
        raise ReservaVencida()

    sessao = reserva.screening
    if sessao.status != Screening.Status.PUBLISHED or sessao.starts_at <= timezone.now():
        raise SessaoIndisponivel()


def pagar(cliente, reserva, cartao):
    """Cobra e — se aprovar — emite. Nunca uma coisa sem a outra."""
    numero = _validar_cartao(cartao)

    with transaction.atomic():
        # Passo 1: BLOQUEIA. A partir daqui a outra tentativa espera.
        travada = (
            Reservation.objects.select_for_update()
            .select_related("screening")
            .get(pk=reserva.pk)
        )

        # Passo 2: só agora o estado é confiável.
        _revalidar(travada, cliente)

        # Passo 3: a decisão simulada.
        motivo = autorizar(numero)
        valor = total_da_reserva(travada)

        if motivo:
            # Passo 4: RECUSA — e ela RETORNA, não levanta.
            #
            # Como exceção, o `raise` desfaria o INSERT deste mesmo Payment no
            # rollback da transação, e o rastro que FR-012 exige sumiria
            # justamente no caso que ele existe para registrar. A recusa é
            # desfecho normal do negócio, não ausência de operação (R8).
            #
            # E ela NÃO toca a reserva: nem `status`, nem `expires_at`. O lugar
            # continua com dono e com prazo correndo, e é o vencimento que o
            # devolve ao estoque — a leitura do Princípio II registrada na
            # spec depende disto ser verdade (FR-026, FR-027).
            recusado = Payment.objects.create(
                reservation=travada,
                status=Payment.Status.DECLINED,
                decline_reason=motivo,
                amount=valor,
                card_last4=numero[-4:],
                card_brand=_bandeira(numero),
            )
            return Resultado(pagamento=recusado, aprovado=False, ingressos=[])

        # Passo 5: APROVA e EMITE, juntos e aqui dentro.
        try:
            aprovado = Payment.objects.create(
                reservation=travada,
                status=Payment.Status.APPROVED,
                amount=valor,
                card_last4=numero[-4:],
                card_brand=_bandeira(numero),
            )
        except IntegrityError as erro:
            # `um_pagamento_aprovado_por_reserva`. Resultado ESPERADO: é a
            # constraint pegando o que o bloqueio deixou passar. Traduzi-la em
            # 500 esconderia o mecanismo que mais importa no sistema.
            raise ReservaJaPaga() from erro

        travada.status = Reservation.Status.PAID
        travada.save(update_fields=["status"])

        ocupacoes = list(travada.seats.select_related("seat").order_by("seat__row", "seat__number"))
        Ticket.objects.bulk_create(
            [Ticket(reserved_seat=ocupacao, payment=aprovado) for ocupacao in ocupacoes]
        )
        emitidos = list(
            Ticket.objects.filter(payment=aprovado)
            .select_related("reserved_seat__seat")
            .order_by("reserved_seat__seat__row", "reserved_seat__seat__number")
        )

    return Resultado(pagamento=aprovado, aprovado=True, ingressos=emitidos)
