"""Views de sessão e reserva.

O mapa é público e declara `AllowAny` explicitamente — o padrão do projeto é
`IsAuthenticated` (ver REST_FRAMEWORK em config/settings/base.py), então o
acesso público é decisão registrada aqui, não herança silenciosa.
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.screening import selectors
from apps.screening.serializers import SeatMapSerializer

SESSAO_NAO_ENCONTRADA = {"detail": "Sessão não encontrada."}


class SeatMapView(APIView):
    """GET /api/v1/sessoes/<id>/mapa/ — a sala e o que está livre.

    Lê exclusivamente o banco local: sala, sessão e assentos são dados
    nossos. Com o TMDb fora do ar esta resposta permanece idêntica
    (Princípio VII, FR-032).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        screening = selectors.get_sellable_screening(pk)
        if screening is None:
            # Rascunho, cancelada, já iniciada e inexistente saem iguais.
            # Distinguir revelaria a grade interna de programação (FR-003).
            return Response(SESSAO_NAO_ENCONTRADA, status=404)

        seats = list(selectors.get_seat_map(screening))
        dados = SeatMapSerializer(screening, context={"seats": seats}).data
        return Response(dados)
