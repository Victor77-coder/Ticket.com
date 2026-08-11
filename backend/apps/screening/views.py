"""Views de sessão e reserva.

O mapa é público e declara `AllowAny` explicitamente — o padrão do projeto é
`IsAuthenticated` (ver REST_FRAMEWORK em config/settings/base.py), então o
acesso público é decisão registrada aqui, não herança silenciosa.
"""

from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import SessionAuthenticationSemCsrf
from apps.screening import selectors
from apps.screening.models import Reservation
from apps.screening.permissions import IsCustomer
from apps.screening.serializers import (
    ReservationInputSerializer,
    ReservationSerializer,
    SeatMapSerializer,
)
from apps.screening.services import reservas

SESSAO_NAO_ENCONTRADA = {"detail": "Sessão não encontrada."}
RESERVA_NAO_ENCONTRADA = {"detail": "Reserva não encontrada."}
ENTRE_PARA_RESERVAR = {"detail": "Entre para reservar."}
RESERVA_EXPIRADA = "Esta reserva expirou. Escolha os lugares de novo."


def _frase_do_conflito(assentos):
    """A recusa nomeia o lugar perdido — "escolha outro" sozinho não basta.

    Sem o nome, a pessoa tem de tentar de novo às cegas até acertar qual dos
    seus lugares saiu (FR-019). A concordância é escrita por extenso porque
    "reservado(s)" numa mensagem que a pessoa lê no meio de uma compra parece
    formulário de repartição, não conversa.
    """
    nomes = ", ".join(f"{s.row}{s.number}" for s in assentos)

    if len(assentos) > 1:
        return (
            f"Os lugares {nomes} acabaram de ser reservados por outra pessoa. "
            "Escolha outros."
        )
    return f"O lugar {nomes} acabou de ser reservado por outra pessoa. Escolha outro."


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


class ReservationViewBase(APIView):
    """O que as duas rotas de reserva compartilham: quem entra e como recusa.

    A autenticação dispensa o CSRF porque quem chama é o Next, não o
    navegador (ver `apps/accounts/authentication.py`).

    E o `401` é traduzido: o DRF, quando o autenticador não oferece cabeçalho
    `WWW-Authenticate` — que é o caso da sessão —, converte "não autenticado"
    em `403`. Os dois seriam indistinguíveis para o front, que precisa saber
    quando conduzir à entrada (FR-026) e quando dizer que o papel não compra
    (FR-025). A recusa por papel continua vindo da própria permissão, com a
    frase dela: traduzir aqui também esconderia uma falha de CSRF atrás de
    "apenas clientes podem reservar".
    """

    authentication_classes = [SessionAuthenticationSemCsrf]
    permission_classes = [IsAuthenticated, IsCustomer]

    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return Response(ENTRE_PARA_RESERVAR, status=401)
        return super().handle_exception(exc)


class ReservationCreateView(ReservationViewBase):
    """POST /api/v1/reservas/ — segura os lugares escolhidos."""

    def post(self, request):
        entrada = ReservationInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data

        sessao = selectors.get_sellable_screening(dados["sessao"])
        if sessao is None:
            return Response(SESSAO_NAO_ENCONTRADA, status=404)

        try:
            reserva, criada = reservas.criar_reserva(
                cliente=request.user,
                sessao=sessao,
                seat_ids=dados["assentos"],
                chave=dados["chave_idempotencia"],
            )
        except reservas.SessaoIndisponivel:
            # A sessão virou não vendável entre a leitura e a transação.
            return Response(SESSAO_NAO_ENCONTRADA, status=404)
        except reservas.SelecaoInvalida as recusa:
            return Response({"detail": recusa.mensagem}, status=400)
        except reservas.AssentoIndisponivel as recusa:
            # 409, não 500. É a constraint ou o bloqueio fazendo o trabalho —
            # o resultado esperado do Princípio II, não uma falha (R3).
            return Response(
                {
                    "detail": _frase_do_conflito(recusa.assentos),
                    "assentos_indisponiveis": [
                        {"fileira": s.row, "numero": s.number} for s in recusa.assentos
                    ],
                },
                status=409,
            )

        dados_saida = ReservationSerializer(reserva).data
        # 201 quando criou, 200 quando a chave já era conhecida: é o que
        # permite ao front distinguir "criei" de "já era minha".
        return Response(dados_saida, status=201 if criada else 200)


class ReservationDetailView(ReservationViewBase):
    """GET /api/v1/reservas/<id>/ — só o dono.

    Reserva de outro cliente devolve `404`, não `403`: um 403 confirmaria
    que ela existe (FR-027, SC-006).
    """

    def get(self, request, pk):
        reserva = (
            Reservation.objects.filter(pk=pk, customer=request.user)
            .select_related("screening")
            .prefetch_related("seats__seat")
            .first()
        )
        if reserva is None:
            return Response(RESERVA_NAO_ENCONTRADA, status=404)

        dados = ReservationSerializer(reserva).data
        if reserva.is_expired:
            # A frase própria impede o front de usar a reserva vencida como
            # se ainda valesse para o pagamento (FR-022, FR-030).
            dados["detail"] = RESERVA_EXPIRADA
        return Response(dados)
