"""A geometria da sala — o ÚNICO lugar onde ela vive.

Até a 013 esta regra morava dentro de `seed_demo._seed_seats` e
`_posicoes_da_sala`. O painel do organizador precisa dela, e copiá-la seria
criar duas verdades sobre onde ficam os lugares de acessibilidade — que
divergem na primeira correção, porque a correção mais provável é justamente a
mais sutil: o que fazer quando a última fileira é menor que a cota.

A regra foi EXTRAÍDA, não duplicada (FR-017). `seed_demo` passou a chamar
daqui, e `test_sala_paridade_seed.py` compara lugar a lugar o que os dois
caminhos produzem.

A FRONTEIRA QUE A EXTRAÇÃO NÃO PODE APAGAR: `posicoes_da_sala` é geometria
pura e continua TRUNCANDO capacidade acima do teto, que é o comportamento que
o seed sempre teve. A RECUSA de capacidade fora dos limites (FR-018) é
validação de entrada e mora no serializer, antes de chegar aqui. Confundir as
duas faria o seed estourar por um valor que ele hoje aceita.
"""

from django.conf import settings
from django.db import transaction

from apps.screening.models import Seat

# 26 é o alfabeto. O corte é EXPLÍCITO para não gerar identificação de fileira
# ilegível em silêncio se a capacidade crescer — "AA12" não é um lugar que
# alguém procura numa sala.
FILEIRAS_MAXIMAS = 26


def teto_de_capacidade(por_fileira=None):
    """O maior número de lugares que a geometria sabe identificar.

    CALCULADO, nunca digitado: a frase de recusa do serializer usa este valor,
    então mudar `SEATS_PER_ROW` muda a mensagem junto. Um "260" literal na
    string passaria a mentir no dia em que a fileira mudasse de tamanho.
    """
    return FILEIRAS_MAXIMAS * (por_fileira or settings.SEATS_PER_ROW)


def posicoes_da_sala(capacity, por_fileira=None):
    """As posições (letra, número) de uma sala, na ordem de leitura.

    GEOMETRIA PURA, e ela TRUNCA no teto — não levanta exceção. É o
    comportamento que o `seed_demo` sempre teve, e mantê-lo é o que impede a
    extração de virar regressão: uma sala do cenário criada acima do teto
    continua sendo criada, com menos lugares do que a capacidade declara.

    A RECUSA de capacidade fora dos limites é outra coisa, mora no serializer e
    acontece ANTES daqui (FR-018). Confundir as duas faria o seed estourar por
    um valor que ele hoje aceita, numa feature que declara não mexer nele.

    Capacidade que não fecha a fileira deixa a última incompleta — nenhum lugar
    é inventado para completá-la.
    """
    por_fileira = por_fileira or settings.SEATS_PER_ROW
    total = min(capacity, teto_de_capacidade(por_fileira))

    return [
        (chr(ord("A") + indice // por_fileira), indice % por_fileira + 1)
        for indice in range(total)
    ]


def lugares_acessiveis(posicoes, cota=None):
    """Os últimos lugares da ÚLTIMA fileira.

    É a convenção de sala real: é onde há espaço para cadeira de rodas sem
    obstruir a passagem (R7 da 007).

    O `min` protege a sala cuja última fileira tem menos lugares que a cota —
    nesse caso todos eles viram acessíveis, e a criação **não** falha. Era uma
    linha só dentro do seed, e é exatamente o tipo de sutileza que uma segunda
    cópia da regra perderia (R1).
    """
    cota = settings.ACCESSIBLE_SEATS_PER_ROOM if cota is None else cota

    # Guarda explícita: `lista[-0:]` é a LISTA INTEIRA, então sem isto uma cota
    # zero marcaria a última fileira toda como acessibilidade — o oposto do
    # pedido.
    if cota <= 0 or not posicoes:
        return set()

    ultima_letra = posicoes[-1][0]
    na_ultima = [p for p in posicoes if p[0] == ultima_letra]

    return set(na_ultima[-min(cota, len(na_ultima)) :])


def gerar_assentos(room, por_fileira=None, cota_acessivel=None):
    """Refaz o mapa físico da sala a partir da capacidade dela.

    APAGA E RECRIA, e só é seguro com zero ocupação: `ReservedSeat.seat` é
    PROTECT, então com um lugar vendido o próprio banco recusa. Os dois
    chamadores garantem isso de formas diferentes — o seed apaga a grade antes,
    e `alterar_capacidade` lê a ocupação e recusa com frase.
    """
    room.seats.all().delete()

    posicoes = posicoes_da_sala(room.capacity, por_fileira)
    acessiveis = lugares_acessiveis(posicoes, cota_acessivel)

    return Seat.objects.bulk_create(
        [
            Seat(
                room=room,
                row=letra,
                number=numero,
                kind=(
                    Seat.Kind.ACCESSIBLE
                    if (letra, numero) in acessiveis
                    else Seat.Kind.COMMON
                ),
            )
            for letra, numero in posicoes
        ]
    )


class CapacidadeComOcupacao(Exception):
    """A sala tem lugar ocupado, e mudar a capacidade apagaria o mapa.

    A frase diz O QUE está acontecendo e O QUE fazer: só o número de lugares
    ocupados explica por que a operação foi recusada, e sem "sem ocupação" a
    pessoa não sabe se algum dia poderá.
    """

    def __init__(self, ocupacao):
        self.ocupacao = ocupacao
        super().__init__(self.mensagem)

    @property
    def mensagem(self):
        # A concordância é escrita por extenso, e não com "(s)": a pessoa lê
        # isto no meio de uma operação, e "lugar(es) ocupado(s)" parece
        # formulário de repartição. Mesma disciplina de `_frase_do_conflito`
        # na 007.
        quantos = (
            f"{self.ocupacao} lugares ocupados"
            if self.ocupacao > 1
            else "1 lugar ocupado"
        )
        return (
            f"Esta sala tem {quantos} por reservas ou ingressos. "
            "Só é possível mudar a capacidade de uma sala sem ocupação."
        )


def alterar_capacidade(room, nova_capacidade):
    """Troca a capacidade e refaz os lugares. Recusa se houver ocupação viva.

    A ordem importa e é esta: ler a ocupação, recusar, e só então apagar.

    A GARANTIA NÃO É A LEITURA — é o PROTECT de `Seat` em `ReservedSeat.seat`.
    Se esta leitura errasse, o banco recusaria de qualquer forma, e o passo 2
    falharia sozinho. A recusa explícita existe para dar FRASE: um
    `ProtectedError` cru na tela viola o Princípio V (R5).

    "Ocupação viva" é lida por `selectors.ocupacao_viva_da_sala`, que consome
    `Reservation.OCUPANDO`. Reserva vencida e não paga não bloqueia: o lugar
    não está ocupado, e é a mesma leitura que o mapa de assentos usa.

    O PASSO DO MEIO — apagar as ocupações MORTAS — não é zelo, é o que faz a
    promessa acima ser verdade. A linha de uma reserva vencida continua no
    banco até alguém reservar aquele lugar de novo: é assim que a 007 concilia
    a constraint absoluta com a expiração, sem rotina agendada. Só que
    `ReservedSeat.seat` é PROTECT, então essas linhas mortas impediriam
    `gerar_assentos` de apagar os lugares — e a sala "sem ocupação" recusaria
    a troca com um `ProtectedError` cru, contradizendo FR-019.

    É a mesma reciclagem que `reservas._liberar_ou_recusar` faz sob bloqueio, e
    aqui ela é segura pelo passo anterior: com ocupação viva zero, TODA linha
    restante é morta por definição. Uma reserva paga — a única que carrega
    ingresso — está sempre em `OCUPANDO`, então nunca chega neste ponto.
    """
    from apps.screening import selectors
    from apps.screening.models import Reservation, ReservedSeat

    with transaction.atomic():
        ocupacao = selectors.ocupacao_viva_da_sala(room)
        if ocupacao:
            raise CapacidadeComOcupacao(ocupacao)

        ReservedSeat.objects.filter(screening__room=room).exclude(
            reservation__in=Reservation.objects.filter(Reservation.OCUPANDO)
        ).delete()

        room.capacity = nova_capacidade
        room.save(update_fields=["capacity"])

        return gerar_assentos(room)
