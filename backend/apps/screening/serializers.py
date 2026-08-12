"""Serializers de sessão, assento e reserva.

GATE DO PRINCÍPIO IV — o mapa é público. Nenhum campo abaixo pode dizer
**quem** ocupou um lugar, nem expor dado de gestão: status da sessão,
identificador de reserva, prazo de reserva alheia, custo ou capacidade.
`contracts/reservation-api.md` lista as proibições e
`tests/test_seat_map_api.py` as verifica.
"""

from django.conf import settings
from rest_framework import serializers

from apps.screening.models import Payment, Reservation, Seat, Ticket
from apps.screening.services import ingressos as ingressos_service


class SeatSerializer(serializers.Serializer):
    """Um lugar do mapa.

    `tipo` e `situacao` são campos distintos de propósito. Um lugar de
    acessibilidade pode estar livre ou tomado como qualquer outro, e
    "selecionado" é estado do navegador — não existe no banco até virar
    reserva. Fundir os quatro estados num campo só obrigaria o front a
    desfazer a fusão.
    """

    id = serializers.IntegerField()
    numero = serializers.IntegerField(source="number")
    tipo = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()

    def get_tipo(self, seat):
        return "acessibilidade" if seat.kind == Seat.Kind.ACCESSIBLE else "comum"

    def get_situacao(self, seat):
        return "tomado" if seat.is_taken else "livre"


class SeatMapSerializer(serializers.Serializer):
    """O mapa completo de uma sessão, agrupado por fileira.

    O agrupamento é do servidor. Entregar uma lista plana faria o cliente
    reagrupar, e a ordem de leitura da sala passaria a depender de código de
    apresentação.

    A capacidade da sala **não** entra: é dado de gestão, pela mesma regra
    que `ScreeningSerializer` do catálogo já aplica. O cliente recebe todos
    os lugares e não precisa do número.
    """

    id = serializers.IntegerField()
    filme = serializers.SerializerMethodField()
    sala = serializers.SerializerMethodField()
    inicio = serializers.DateTimeField(source="starts_at")
    preco = serializers.DecimalField(source="price", max_digits=8, decimal_places=2)
    esgotada = serializers.SerializerMethodField()
    limite_por_reserva = serializers.SerializerMethodField()
    fileiras = serializers.SerializerMethodField()

    def get_filme(self, screening):
        return {"titulo": screening.movie.title, "slug": screening.movie.slug}

    def get_sala(self, screening):
        return {"nome": screening.room.name}

    def get_limite_por_reserva(self, screening):
        return settings.MAX_SEATS_PER_RESERVATION

    def get_esgotada(self, screening):
        """Derivado, para o front escolher o estado explicativo sem varrer.

        Só os lugares comuns contam: os de acessibilidade estão fora da venda
        comum, então uma sala com eles livres e todo o resto tomado está
        esgotada para quem compra pelo fluxo normal.
        """
        comuns = [s for s in self.context["seats"] if s.kind != Seat.Kind.ACCESSIBLE]
        return bool(comuns) and all(s.is_taken for s in comuns)

    def get_fileiras(self, screening):
        fileiras = []
        for seat in self.context["seats"]:
            if not fileiras or fileiras[-1]["letra"] != seat.row:
                fileiras.append({"letra": seat.row, "assentos": []})
            fileiras[-1]["assentos"].append(SeatSerializer(seat).data)
        return fileiras


class ReservationInputSerializer(serializers.Serializer):
    """O que a requisição de reserva pode trazer.

    A chave de idempotência é obrigatória: sem ela, uma requisição repetida
    por instabilidade de rede vira reserva duplicada, e desabilitar o botão
    no navegador não cobre esse caso.
    """

    sessao = serializers.IntegerField()
    assentos = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    chave_idempotencia = serializers.UUIDField()


class LugarSerializer(serializers.Serializer):
    fileira = serializers.CharField(source="row")
    numero = serializers.IntegerField(source="number")


class ReservationSerializer(serializers.Serializer):
    """A reserva como o cliente dono a vê.

    Não traz `idempotency_key` nem identificação do cliente: a primeira é
    segredo do envio e a segunda não acrescenta nada a quem já sabe quem é.
    """

    id = serializers.IntegerField()
    sessao = serializers.IntegerField(source="screening_id")
    assentos = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    # Instante absoluto, nunca "faltam N segundos": o relógio do navegador
    # pode estar errado, e a contagem regressiva precisa de um alvo fixo para
    # não derivar.
    expira_em = serializers.DateTimeField(source="expires_at")
    situacao = serializers.SerializerMethodField()

    def _assentos(self, reserva):
        return [o.seat for o in reserva.seats.all()]

    def get_assentos(self, reserva):
        return LugarSerializer(self._assentos(reserva), many=True).data

    def get_total(self, reserva):
        return f"{reserva.screening.price * len(self._assentos(reserva)):.2f}"

    def to_representation(self, reserva):
        """AMPLIA a resposta da 007, nunca a altera.

        Todo campo que a 007 entregava continua com o mesmo nome e o mesmo
        significado (FR-050); `pagamento` e `ingressos` só APARECEM quando a
        reserva está paga. É isto que faz a confirmação sobreviver a um
        recarregamento e que permite a `/pagamento/[id]` mostrar os ingressos
        em vez de um formulário inútil (R13).

        `expira_em` continua presente numa reserva paga, com o valor original
        e sem significado de prazo — reserva paga não vence. Quem decide não
        exibir contagem regressiva é o front, olhando `situacao`.
        """
        dados = super().to_representation(reserva)

        if reserva.status != Reservation.Status.PAID:
            return dados

        aprovado = reserva.payments.filter(status=Payment.Status.APPROVED).first()
        if aprovado is None:
            # Estado que o Princípio II proíbe e as constraints impedem. Se
            # aparecer, é sintoma de corrupção — e a resposta não inventa
            # ingresso para disfarçar.
            return dados

        dados["pagamento"] = PaymentSerializer(aprovado).data
        dados["ingressos"] = TicketSerializer(
            Ticket.objects.filter(payment=aprovado)
            .select_related(
                "reserved_seat__seat",
                "reserved_seat__screening__movie",
                "reserved_seat__screening__room",
            )
            .order_by("reserved_seat__seat__row", "reserved_seat__seat__number"),
            many=True,
        ).data
        return dados

    def get_situacao(self, reserva):
        """`paga` vem ANTES de `expirada`, e a ordem não é arbitrária.

        Uma reserva paga cujo prazo original já passou continua respondendo
        `True` em `is_expired` — a pergunta "o prazo venceu?" tem mesmo essa
        resposta. Perguntar primeiro se está paga é o que impede a compra
        concluída de aparecer como expirada dez minutos depois. É a mesma
        precedência que `Reservation.OCUPANDO` aplica no banco.
        """
        if reserva.status == Reservation.Status.PAID:
            return "paga"
        return "expirada" if reserva.is_expired else "reservada"


class PaymentInputSerializer(serializers.Serializer):
    """Os dados digitados do cartão.

    Nenhum destes campos é persistido: só os quatro últimos dígitos e a
    bandeira sobrevivem à requisição (FR-011). O serializer não é ecoado em
    resposta de erro — `tests/test_payment_api.py` fixa a ausência.

    A validação de forma (Luhn, mês válido) fica no serviço, junto da decisão,
    para que a fronteira entre "preenchimento inválido" e "cartão recusado"
    tenha um dono só.
    """

    # Todos aceitam vazio DE PROPÓSITO. O campo obrigatório de verdade é
    # conferido no serviço, que responde em português dizendo qual é — se a
    # obrigatoriedade morasse aqui, o DRF recusaria antes com a frase dele,
    # em inglês, e o Princípio V seria violado por um caminho que nenhuma
    # revisão de texto alcança.
    numero = serializers.CharField(max_length=32, allow_blank=True, default="")
    nome = serializers.CharField(max_length=80, allow_blank=True, default="")
    validade = serializers.CharField(max_length=10, allow_blank=True, default="")
    cvv = serializers.CharField(max_length=4, allow_blank=True, default="")


class PaymentSerializer(serializers.Serializer):
    """A cobrança aprovada, como o comprador a vê.

    Sem `id`: a identidade interna do pagamento não serve a nada no cliente e
    só amplia a superfície.
    """

    cartao_final = serializers.CharField(source="card_last4")
    bandeira = serializers.CharField(source="card_brand")
    total = serializers.SerializerMethodField()
    pago_em = serializers.DateTimeField(source="created_at")

    def get_total(self, pagamento):
        return f"{pagamento.amount:.2f}"


class TicketSerializer(serializers.Serializer):
    """Um ingresso — um por LUGAR, nunca um por reserva.

    `codigo` e `qr_svg` andam juntos de propósito: o código é a verdade
    assinada, o QR é uma representação dele. O texto aparece na tela junto da
    imagem porque a portaria exige digitação manual como alternativa sempre
    disponível, e um QR que não carrega não pode deixar a pessoa sem nada
    (FR-038).

    Sem `id` interno: a identidade pública já vai dentro do código assinado.
    """

    codigo = serializers.SerializerMethodField()
    qr_svg = serializers.SerializerMethodField()
    filme = serializers.SerializerMethodField()
    sessao = serializers.SerializerMethodField()
    sala = serializers.SerializerMethodField()
    assento = serializers.SerializerMethodField()

    def _codigo(self, ingresso):
        # Derivado, nunca armazenado: guardá-lo numa coluna criaria a chance
        # de a coluna e a chave discordarem depois de uma rotação.
        return ingressos_service.assinar_codigo(
            ingresso.public_id, ingresso.reserved_seat.screening_id
        )

    def get_codigo(self, ingresso):
        return self._codigo(ingresso)

    def get_qr_svg(self, ingresso):
        return ingressos_service.qr_data_uri(self._codigo(ingresso))

    def get_filme(self, ingresso):
        return ingresso.reserved_seat.screening.movie.title

    def get_sessao(self, ingresso):
        return ingresso.reserved_seat.screening.starts_at

    def get_sala(self, ingresso):
        return ingresso.reserved_seat.screening.room.name

    def get_assento(self, ingresso):
        return LugarSerializer(ingresso.reserved_seat.seat).data
