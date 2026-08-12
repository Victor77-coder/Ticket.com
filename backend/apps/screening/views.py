"""Views de sessão e reserva.

O mapa é público e declara `AllowAny` explicitamente — o padrão do projeto é
`IsAuthenticated` (ver REST_FRAMEWORK em config/settings/base.py), então o
acesso público é decisão registrada aqui, não herança silenciosa.
"""

from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import SessionAuthenticationSemCsrf
from apps.screening import selectors
from apps.screening.models import Reservation, Screening
from apps.screening.permissions import (
    IsCustomer,
    IsCustomerParaIngressos,
    IsCustomerParaPagar,
    IsGate,
)
from apps.screening.serializers import (
    estado_do_link,
    SessaoDaPortaSerializer,
    ValidacaoInputSerializer,
    ValidacaoSerializer,
    MeuIngressoSerializer,
    PaymentInputSerializer,
    PaymentSerializer,
    ReservationInputSerializer,
    ReservationSerializer,
    SeatMapSerializer,
    TicketSerializer,
)
from apps.screening.services import compartilhamento, pagamentos, portaria, reservas

SESSAO_NAO_ENCONTRADA = {"detail": "Sessão não encontrada."}
RESERVA_NAO_ENCONTRADA = {"detail": "Reserva não encontrada."}
ENTRE_PARA_RESERVAR = {"detail": "Entre para reservar."}
ENTRE_PARA_PAGAR = {"detail": "Entre para concluir o pagamento."}
ENTRE_PARA_VER_INGRESSOS = {"detail": "Entre para ver seus ingressos."}
INGRESSO_NAO_ENCONTRADO = {"detail": "Ingresso não encontrado."}
# A MESMA frase para token inexistente, revogado e substituído (FR-043).
# Distinguir entregaria a quem está adivinhando a informação de que um palpite
# chegou perto. E é uma frase, não "Não encontrado": quem recebeu o ingresso
# de um amigo concluiria que o site quebrou.
LINK_MORTO = {"detail": "Este link não vale mais. Peça um novo a quem enviou o ingresso."}
ENTRE_PARA_PORTARIA = {"detail": "Entre para usar a portaria."}
CODIGO_AUSENTE = {"detail": "Apresente ou digite um código."}
SESSAO_DA_PORTA_AUSENTE = {
    "detail": "Escolha a sessão que esta porta está recebendo."
}
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


# --- Ingressos do cliente e compartilhamento (feature 009) -----------------


class TicketViewBase(APIView):
    """O que as rotas de ingresso do DONO compartilham.

    Mesma autenticação sem CSRF de 007 e 008 — quem chama é o Next, servidor
    a servidor — e a mesma tradução do `401`, com a frase desta tela.

    A tradução existe porque o DRF converte "não autenticado" em `403` quando
    o autenticador não oferece `WWW-Authenticate`, que é o caso da sessão. Sem
    ela o front não distingue "conduza à entrada" (visitante) de "seu papel
    não tem ingressos" (organizador, portaria) — e conduzir um organizador à
    entrada é caminho sem saída, porque entrar de novo não muda o papel.
    """

    authentication_classes = [SessionAuthenticationSemCsrf]
    permission_classes = [IsAuthenticated, IsCustomerParaIngressos]

    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return Response(ENTRE_PARA_VER_INGRESSOS, status=401)
        return super().handle_exception(exc)


class MyTicketsView(TicketViewBase):
    """GET /api/v1/meus-ingressos/ — a lista do cliente.

    Devolve DOIS GRUPOS já separados e já ordenados, e não uma lista com um
    instante para o front comparar: a fronteira entre futuro e passado é
    decisão do servidor (FR-010), e o relógio do navegador não participa dela.

    Cliente sem ingresso nenhum recebe `200` com os dois grupos vazios —
    nunca `404` nem `204`. O estado vazio é uma TELA escrita para gente, não a
    ausência de um recurso; um `404` faria o front tratar "nunca comprou" como
    erro.
    """

    def get(self, request):
        futuros, passados = selectors.ingressos_do_cliente(request.user)

        return Response(
            {
                "futuros": MeuIngressoSerializer(
                    futuros, many=True, context={"grupo": "futuro"}
                ).data,
                "passados": MeuIngressoSerializer(
                    passados, many=True, context={"grupo": "passado"}
                ).data,
            }
        )


class TicketDetailView(TicketViewBase):
    """GET /api/v1/ingressos/<public_id>/ — o ingresso do dono.

    `404` para ingresso inexistente E para ingresso de outro cliente, nunca
    `403`: um `403` confirmaria que aquele `public_id` existe — e `public_id`
    é exatamente o valor que vai dentro do código assinado do QR. Mesma regra
    que 007 e 008 já aplicam a reservas.
    """

    def get(self, request, public_id):
        ingresso = selectors.ingresso_do_dono(request.user, public_id)
        if ingresso is None:
            return Response(INGRESSO_NAO_ENCONTRADO, status=404)

        dados = MeuIngressoSerializer(
            ingresso, context={"grupo": _grupo_de(ingresso)}
        ).data
        dados["link"] = estado_do_link(selectors.link_ativo(ingresso))
        return Response(dados)


class TicketShareLinkView(TicketViewBase):
    """POST e DELETE em /api/v1/ingressos/<public_id>/link/.

    Dois verbos num endereço só, e não `/gerar-link/` e `/revogar-link/`:
    gerar e revogar são criar e apagar o MESMO recurso. Endereço que descreve
    ação em vez de recurso é o que faz uma API crescer por acúmulo.
    """

    def post(self, request, public_id):
        """Gera o link. `201` quando cria, `200` quando já existia.

        A distinção segue o padrão que a 007 fixou em `POST /reservas/`: é o
        que permite ao front dizer "gerei agora" ou "já era seu" sem
        interpretar texto.

        NUNCA `409`. Não há conflito a reportar — pediram um link e receberam
        um link. É o mesmo desfecho da corrida perdida, e ela também não é
        erro (FR-028).
        """
        ingresso = selectors.ingresso_do_dono(request.user, public_id)
        if ingresso is None:
            return Response(INGRESSO_NAO_ENCONTRADO, status=404)

        link, criou = compartilhamento.gerar_link(ingresso)
        return Response(estado_do_link(link), status=201 if criou else 200)

    def delete(self, request, public_id):
        """Revoga. `200` também quando não havia link ativo.

        Um `404` na segunda chamada faria o front exibir erro por uma ação que
        produziu exatamente o resultado desejado.
        """
        ingresso = selectors.ingresso_do_dono(request.user, public_id)
        if ingresso is None:
            return Response(INGRESSO_NAO_ENCONTRADO, status=404)

        compartilhamento.revogar_link(ingresso)
        return Response(estado_do_link(None))


class SharedTicketView(APIView):
    """GET /api/v1/ingressos-compartilhados/<token>/ — **público**.

    O único endereço da API que entrega um ingresso a quem não se identificou.

    `authentication_classes = []` é a metade que importa, e não é redundância
    com `AllowAny`. Sem autenticador não existe caminho pelo qual esta view
    enxergue um usuário — então não existe caminho pelo qual ela decida algo
    com base em quem está olhando, nem por engano nem numa refatoração
    futura. É o que faz "não pede conta e não conduz a entrada" ser ESTRUTURA
    em vez de comportamento (FR-036).

    O padrão do projeto é `IsAuthenticated` por default no `REST_FRAMEWORK`;
    acesso público é sempre declarado com o motivo, como `SeatMapView` faz.

    RESPONDE COM O `TicketSerializer` DA 008, SEM ALTERAÇÃO. Ele já expõe
    exatamente o recorte que FR-037 autoriza — filme, sessão, sala, lugar,
    código e QR — e não pode ganhar campo nenhum: os campos da área do dono
    vivem em `MeuIngressoSerializer` justamente para que a pressão de
    crescimento aponte para o lado que não é público.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        link = selectors.ingresso_por_token(token)
        if link is None:
            # Inexistente, revogado e substituído saem IGUAIS — a convergência
            # acontece na consulta, não aqui (FR-043). Distinguir entregaria a
            # quem adivinha a informação de que um palpite chegou perto.
            return Response(LINK_MORTO, status=404)

        return Response(TicketSerializer(link.ticket).data)


# --- Portaria (feature 010) -----------------------------------------------


class GateViewBase(APIView):
    """O que as duas rotas da portaria compartilham.

    Mesma autenticação sem CSRF de 007, 008 e 009 — quem chama é o Next — e a
    mesma tradução do `401`, com a frase desta tela. Sem ela o DRF devolveria
    `403` para quem não entrou, e o front não distinguiria "conduza à entrada"
    de "seu papel não valida" — e conduzir um cliente à entrada é caminho sem
    saída, porque entrar de novo não muda o papel.
    """

    authentication_classes = [SessionAuthenticationSemCsrf]
    permission_classes = [IsAuthenticated, IsGate]

    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return Response(ENTRE_PARA_PORTARIA, status=401)
        return super().handle_exception(exc)


class GateScreeningsView(GateViewBase):
    """GET /api/v1/portaria/sessoes/ — as sessões que este posto pode receber.

    Lista vazia devolve `200`, nunca `404`: "hoje não tem sessão" é um estado
    da portaria, não a ausência de um recurso, e a tela tem frase própria para
    ele.
    """

    def get(self, request):
        sessoes = selectors.sessoes_da_portaria()
        return Response({"sessoes": SessaoDaPortaSerializer(sessoes, many=True).data})


class GateValidateView(GateViewBase):
    """POST /api/v1/portaria/validar/ — a única escrita da feature.

    OS QUATRO DESFECHOS RESPONDEM `200`, e a escolha tem motivo: nenhum deles é
    erro DA REQUISIÇÃO. A portaria perguntou "posso deixar entrar?" e recebeu
    resposta; "não" é uma resposta. Mapear "já utilizado" para `409` ou
    "inválido" para `422` faria o front distinguir desfecho de negócio por
    semântica de HTTP, e qualquer camada que trate `4xx` como erro esconderia
    um desfecho legítimo.

    É divergência deliberada em relação à 008, onde a recusa de cartão é `402`:
    lá os códigos separam CAMINHOS DE RECUPERAÇÃO diferentes — "corrija o
    formulário" e "troque de cartão". Aqui os quatro vão para a mesma tela, e
    o front escolhe a apresentação pelo campo `situacao`.

    `400` fica só para o que a portaria não chegou a apresentar.
    """

    def post(self, request):
        entrada = ValidacaoInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(CODIGO_AUSENTE, status=400)

        dados = entrada.validated_data
        codigo = (dados.get("codigo") or "").strip()

        # Campo vazio NÃO é "inválido" (FR-014): nada foi apresentado, e não há
        # o que julgar. Dizer "ingresso não reconhecido" para um campo em
        # branco faria o operador procurar defeito no ingresso da pessoa.
        if not codigo:
            return Response(CODIGO_AUSENTE, status=400)

        sessao_id = dados.get("sessao")
        if sessao_id is None or not selectors.sessoes_da_portaria().filter(
            pk=sessao_id
        ).exists():
            return Response(SESSAO_DA_PORTA_AUSENTE, status=400)

        resultado = portaria.validar(codigo=codigo, sessao_id=sessao_id)

        corpo = ValidacaoSerializer(resultado).data
        corpo["detail"] = _frase_do_desfecho(resultado)
        return Response(corpo)


def _frase_do_desfecho(resultado):
    """A frase que o operador lê, em português, dizendo a próxima ação.

    Mora na camada de apresentação, e não no serviço: o serviço devolve um
    valor fixo (`situacao`), e é ele que a tela usa para escolher símbolo e
    título. A frase muda numa revisão de redação sem que nada mais mude.
    """
    if resultado.situacao == portaria.VALIDO:
        lugar = resultado.ingresso.reserved_seat.seat
        sala = resultado.sessao_do_ingresso.room.name
        return f"Pode entrar. {sala}, lugar {lugar.row}{lugar.number}."

    if resultado.situacao == portaria.JA_UTILIZADO:
        quando = timezone.localtime(resultado.utilizado_em).strftime("%H:%M")
        return f"Este ingresso já foi usado às {quando}. Não libere a entrada."

    if resultado.situacao == portaria.SESSAO_ERRADA:
        sessao = resultado.sessao_do_ingresso
        if sessao.status == Screening.Status.CANCELLED:
            return (
                "Este ingresso é de uma sessão que foi cancelada. "
                "Encaminhe a pessoa à bilheteria."
            )
        quando = timezone.localtime(sessao.starts_at).strftime("%H:%M")
        return (
            f"Este ingresso é da sessão das {quando}, {sessao.room.name}. "
            "Não é esta porta."
        )

    return "Ingresso não reconhecido. Não libere a entrada."


def _grupo_de(ingresso):
    """A mesma fronteira do selector, para um ingresso só.

    A lista separa os grupos na consulta, com o relógio do banco. Aqui há uma
    linha só e nenhuma consulta para carregar a informação, então a regra é
    reaplicada — e é a MESMA regra: o início da sessão.
    """
    inicio = ingresso.reserved_seat.screening.starts_at
    return "futuro" if inicio > timezone.now() else "passado"
