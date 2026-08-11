"""Serializers de sessão, assento e reserva.

GATE DO PRINCÍPIO IV — o mapa é público. Nenhum campo abaixo pode dizer
**quem** ocupou um lugar, nem expor dado de gestão: status da sessão,
identificador de reserva, prazo de reserva alheia, custo ou capacidade.
`contracts/reservation-api.md` lista as proibições e
`tests/test_seat_map_api.py` as verifica.
"""

from django.conf import settings
from rest_framework import serializers

from apps.screening.models import Seat


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

    def get_situacao(self, reserva):
        return "expirada" if reserva.is_expired else "reservada"
