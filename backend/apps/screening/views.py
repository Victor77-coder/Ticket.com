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
from apps.screening.permissions import IsCustomer, IsCustomerParaPagar
from apps.screening.serializers import (
    PaymentInputSerializer,
    PaymentSerializer,
    ReservationInputSerializer,
    ReservationSerializer,
    SeatMapSerializer,
    TicketSerializer,
)
from apps.screening.services import pagamentos, reservas

SESSAO_NAO_ENCONTRADA = {"detail": "Sessão não encontrada."}
RESERVA_NAO_ENCONTRADA = {"detail": "Reserva não encontrada."}
ENTRE_PARA_RESERVAR = {"detail": "Entre para reservar."}
ENTRE_PARA_PAGAR = {"detail": "Entre para concluir o pagamento."}
RESERVA_EXPIRADA = "Esta reserva expirou. Escolha os lugares de novo."
RESERVA_JA_PAGA = "Esta reserva já foi paga. Seus ingressos estão logo abaixo."
RESERVA_CANCELADA = "Esta reserva foi cancelada. Escolha os lugares de novo."
SESSAO_INDISPONIVEL = "Esta sessão não está mais disponível."
CARTAO_ILEGIVEL = {"detail": "Confira os dados do cartão."}

# As frases da recusa de cartão, escritas para quem está comprando.
#
# Cada motivo tem a sua, e as três são diferentes — se duas fossem iguais, a
# tabela do README teria sido silenciosamente reduzida a um caminho só
# (FR-008, FR-009). Toda uma diz o que houve E qual a próxima ação: "recusado"
# sozinho deixa a pessoa sem saber se insiste ou troca de cartão.
MOTIVOS_DE_RECUSA = {
    "saldo_insuficiente": (
        "Não havia saldo suficiente neste cartão. Tente outro cartão."
    ),
    "cartao_expirado": (
        "Este cartão está expirado. Use um cartão com validade em dia."
    ),
    "recusado_pelo_emissor": (
        "O banco emissor recusou a cobrança. Tente outro cartão ou fale com o banco."
    ),
}


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
        if reserva.is_expired and reserva.status != Reservation.Status.PAID:
            # A frase própria impede o front de usar a reserva vencida como
            # se ainda valesse para o pagamento (FR-022, FR-030).
            #
            # Reserva PAGA é excluída: o prazo dela passou e não significa
            # nada, porque a compra foi concluída. Sem esta condição, o
            # comprador veria "esta reserva expirou" dez minutos depois de
            # receber os ingressos.
            dados["detail"] = RESERVA_EXPIRADA
        return Response(dados)


class PaymentCreateView(ReservationViewBase):
    """POST /api/v1/reservas/<id>/pagamento/ — cobra e emite.

    Herda de `ReservationViewBase` a autenticação sem CSRF — o mesmo par que a
    007 precisou, pelo mesmo motivo: quem chama é o Next, servidor a servidor.

    A reserva é buscada FILTRANDO PELO DONO. Reserva de outro cliente devolve
    `404`, não `403`: um `403` confirmaria que ela existe (FR-040, FR-043).
    """

    permission_classes = [IsAuthenticated, IsCustomerParaPagar]

    def handle_exception(self, exc):
        """A frase do 401 é a do pagamento, não a da reserva.

        Mesma tradução da base — o DRF converteria "não autenticado" em `403`
        porque a sessão não oferece `WWW-Authenticate` —, mas com o texto da
        tela em que a pessoa está (FR-044).
        """
        if isinstance(exc, NotAuthenticated):
            return Response(ENTRE_PARA_PAGAR, status=401)
        return super().handle_exception(exc)

    def post(self, request, pk):
        entrada = PaymentInputSerializer(data=request.data)
        if not entrada.is_valid():
            # O que sobra para o serializer são limites de tamanho e tipo. A
            # recusa do DRF sairia em inglês e com o nome do campo — texto de
            # framework no meio de uma compra, que o Princípio V proíbe —, e
            # ecoaria o valor enviado, que é como um número de cartão acaba em
            # log. Vira uma frase nossa, e o corpo não é devolvido (FR-011).
            return Response(CARTAO_ILEGIVEL, status=400)

        reserva = (
            Reservation.objects.filter(pk=pk, customer=request.user)
            .select_related("screening")
            .first()
        )
        if reserva is None:
            return Response(RESERVA_NAO_ENCONTRADA, status=404)

        try:
            resultado = pagamentos.pagar(
                cliente=request.user,
                reserva=reserva,
                cartao=pagamentos.Cartao(**entrada.validated_data),
            )
        except pagamentos.CartaoInvalido as recusa:
            # 400: a pessoa corrige o que digitou. Diferente do 402, em que
            # ela troca de cartão (FR-010).
            #
            # A resposta carrega só a frase — nunca o que foi enviado. Ecoar
            # o corpo aqui devolveria o número do cartão numa mensagem de
            # erro, que é como ele acaba em log de servidor (FR-011).
            return Response({"detail": recusa.mensagem}, status=400)
        except pagamentos.ReservaJaPaga:
            return self._conflito(reserva, "paga", RESERVA_JA_PAGA)
        except pagamentos.ReservaVencida:
            return self._conflito(reserva, "expirada", RESERVA_EXPIRADA)
        except pagamentos.ReservaCancelada:
            return self._conflito(reserva, "cancelada", RESERVA_CANCELADA)
        except pagamentos.SessaoIndisponivel:
            return self._conflito(reserva, "indisponivel", SESSAO_INDISPONIVEL)

        if not resultado.aprovado:
            # 402, não 400 e não 409: a requisição estava correta, a cobrança
            # é que não passou. É o que permite ao front distinguir "corrija o
            # formulário" de "troque de cartão" sem interpretar texto (R8).
            return Response(
                {
                    "situacao": "recusada",
                    "motivo": resultado.pagamento.decline_reason,
                    "detail": MOTIVOS_DE_RECUSA[resultado.pagamento.decline_reason],
                    # Volta de propósito: é a prova observável de que a recusa
                    # NÃO mexeu no prazo da reserva (FR-027).
                    "expira_em": reserva.expires_at,
                },
                status=402,
            )

        return Response(
            {
                "situacao": "paga",
                "pagamento": PaymentSerializer(resultado.pagamento).data,
                "ingressos": TicketSerializer(resultado.ingressos, many=True).data,
            },
            status=201,
        )

    def _conflito(self, reserva, situacao, frase):
        """409 para os quatro estados que impedem cobrar.

        `paga` é o desfecho da corrida perdida e também o do clique duplo. Vem
        de duas origens indistinguíveis para o cliente — a revalidação sob
        bloqueio, ou a constraint — e nenhuma delas é erro de sistema.
        """
        corpo = {"situacao": situacao, "detail": frase}
        if situacao == "paga":
            # Levar aos ingressos que já existem é mais útil do que só negar.
            corpo.update(ReservationSerializer(reserva).data)
            corpo["situacao"] = "paga"
            corpo["detail"] = frase
        return Response(corpo, status=409)
