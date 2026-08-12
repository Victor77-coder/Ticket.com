"""Contrato da API de pagamento.

Cobre o que a corrida não cobre: as recusas, as mensagens, os estados que não
podem ser pagos e a autorização. A prova de concorrência mora em
`test_payment_concurrency.py` — aqui o banco é de teste comum, com transação
envolvente, e é adequado porque nenhum destes casos depende de duas conexões.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import Payment, Reservation, ReservedSeat, Screening, Ticket

User = get_user_model()

SENHA = "desafio2026"

APROVADO = {
    "numero": "4242424242424242",
    "nome": "MARIA DE SOUZA",
    "validade": "12/2030",
    "cvv": "123",
}
SEM_SALDO = {**APROVADO, "numero": "4000000000009995"}
EXPIRADO = {**APROVADO, "numero": "4000000000000069"}
RECUSADO_EMISSOR = {**APROVADO, "numero": "4000000000000002"}


@pytest.fixture
def sessao(make_movie, make_screening, seats):
    return make_screening(make_movie("A Odisseia"))


@pytest.fixture
def cliente(db):
    return User.objects.create_user(
        username="cliente1", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def outro_cliente(db):
    return User.objects.create_user(
        username="cliente2", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def lugares(sessao):
    return list(sessao.room.seats.filter(kind="common")[:3])


@pytest.fixture
def reserva(make_reservation, sessao, cliente, lugares):
    return make_reservation(sessao, cliente, lugares)


@pytest.fixture
def autenticado(client, cliente):
    client.force_login(cliente)
    return client


def _pagar(client, reserva, cartao=None):
    return client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=cartao or APROVADO,
        content_type="application/json",
    )


# --- US1: pagar e receber o ingresso ---------------------------------------


@pytest.mark.django_db
def test_reserva_de_tres_lugares_emite_tres_ingressos(autenticado, reserva, lugares):
    """Um ingresso por LUGAR, não por reserva (FR-014, SC-003)."""
    resposta = _pagar(autenticado, reserva)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["situacao"] == "paga"
    assert len(corpo["ingressos"]) == len(lugares) == 3

    assentos = [(i["assento"]["fileira"], i["assento"]["numero"]) for i in corpo["ingressos"]]
    assert sorted(assentos) == sorted((s.row, s.number) for s in lugares)


@pytest.mark.django_db
def test_cada_ingresso_tem_codigo_distinto(autenticado, reserva):
    """FR-037 — e um código não pode permitir deduzir o outro."""
    corpo = _pagar(autenticado, reserva).json()

    codigos = [i["codigo"] for i in corpo["ingressos"]]
    assert len(set(codigos)) == len(codigos)
    assert all(codigos)


@pytest.mark.django_db
def test_ingresso_traz_qr_e_o_codigo_em_texto(autenticado, reserva):
    """FR-038 — o texto é o que a portaria digita quando a câmera falha."""
    corpo = _pagar(autenticado, reserva).json()

    for ingresso in corpo["ingressos"]:
        assert ingresso["qr_svg"].startswith("data:image/svg+xml;base64,")
        assert isinstance(ingresso["codigo"], str) and len(ingresso["codigo"]) > 20
        assert ingresso["filme"] and ingresso["sala"] and ingresso["sessao"]


@pytest.mark.django_db
def test_total_e_calculado_pelo_servidor(autenticado, reserva, sessao, lugares):
    """FR-003 — valor vindo do cliente não é aceito nem para conferência."""
    resposta = autenticado.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data={**APROVADO, "total": "0.01", "amount": "0.01"},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    esperado = f"{sessao.price * len(lugares):.2f}"
    assert resposta.json()["pagamento"]["total"] == esperado
    assert str(Payment.objects.get(reservation=reserva).amount) == esperado


@pytest.mark.django_db
def test_resposta_nao_vaza_dado_de_cartao_nem_id_interno(autenticado, reserva):
    """Gate do Princípio IV — contrato, "campos proibidos"."""
    bruto = _pagar(autenticado, reserva).content.decode()

    assert APROVADO["numero"] not in bruto
    assert APROVADO["cvv"] not in bruto or bruto.count(APROVADO["cvv"]) == 0
    assert "4242424242424242" not in bruto
    assert "public_id" not in bruto
    assert "reserved_seat" not in bruto
    assert "idempotency_key" not in bruto

    from django.conf import settings

    # SC-011: a chave de assinatura não pode aparecer em nenhuma resposta,
    # nem derivada. Se aparecesse, o QR seria forjável por quem comprou uma vez.
    assert settings.TICKET_SIGNING_KEY not in bruto


@pytest.mark.django_db
def test_so_os_quatro_ultimos_digitos_sao_guardados(autenticado, reserva):
    """FR-011, R10 — não há cobrança real, guardar o número é risco puro."""
    _pagar(autenticado, reserva)

    pagamento = Payment.objects.get(reservation=reserva)
    assert pagamento.card_last4 == "4242"
    assert pagamento.card_brand == "visa"

    for campo in pagamento._meta.get_fields():
        valor = getattr(pagamento, campo.name, None)
        assert valor != APROVADO["numero"], f"o número inteiro vazou em {campo.name}"


@pytest.mark.django_db
def test_reserva_paga_devolve_ingressos_ao_ser_consultada(autenticado, reserva):
    """FR-022, US1-6 — a confirmação sobrevive a um recarregamento."""
    _pagar(autenticado, reserva)

    resposta = autenticado.get(reverse("screening:reservation-detail", args=[reserva.pk]))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["situacao"] == "paga"
    assert len(corpo["ingressos"]) == 3
    assert corpo["pagamento"]["cartao_final"] == "4242"


@pytest.mark.django_db
def test_reserva_paga_e_vencida_no_relogio_nao_diz_que_expirou(autenticado, reserva):
    """Dez minutos depois da compra, a reserva não pode virar "expirada"."""
    _pagar(autenticado, reserva)
    Reservation.objects.filter(pk=reserva.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    corpo = autenticado.get(
        reverse("screening:reservation-detail", args=[reserva.pk])
    ).json()

    assert corpo["situacao"] == "paga"
    assert "expirou" not in corpo.get("detail", "")


@pytest.mark.django_db
def test_lugares_pagos_seguem_tomados_no_mapa(autenticado, client, reserva, sessao, lugares):
    """FR-018 — a partir da aprovação, o lugar está vendido."""
    _pagar(autenticado, reserva)

    corpo = client.get(reverse("screening:seat-map", args=[sessao.pk])).json()
    situacoes = {
        (f["letra"], a["numero"]): a["situacao"]
        for f in corpo["fileiras"]
        for a in f["assentos"]
    }
    for lugar in lugares:
        assert situacoes[(lugar.row, lugar.number)] == "tomado"


# --- US2: a recusa ----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cartao,motivo",
    [
        (SEM_SALDO, "saldo_insuficiente"),
        (EXPIRADO, "cartao_expirado"),
        (RECUSADO_EMISSOR, "recusado_pelo_emissor"),
    ],
)
def test_os_tres_cartoes_de_recusa_devolvem_402_com_seu_motivo(
    autenticado, reserva, cartao, motivo
):
    """FR-006, FR-008 — determinístico, escolhido por quem testa."""
    resposta = _pagar(autenticado, reserva, cartao)

    assert resposta.status_code == 402
    corpo = resposta.json()
    assert corpo["situacao"] == "recusada"
    assert corpo["motivo"] == motivo
    assert corpo["detail"]


@pytest.mark.django_db
def test_as_tres_recusas_tem_frases_diferentes(autenticado, sessao, cliente, make_reservation):
    """SC-006.

    Se duas frases fossem iguais, a tabela do README teria sido
    silenciosamente reduzida a um caminho só — e o avaliador acharia que
    exercitou três caminhos tendo exercitado dois.
    """
    frases = set()
    for cartao in (SEM_SALDO, EXPIRADO, RECUSADO_EMISSOR):
        lugar = sessao.room.seats.filter(kind="common").order_by("?").first()
        reserva = make_reservation(sessao, cliente, [lugar])
        corpo = _pagar_com_login(cliente, reserva, cartao)
        frases.add(corpo["detail"])

    assert len(frases) == 3, f"esperava três frases distintas, veio {frases}"
    assert all("erro" not in f.lower() for f in frases)


def _pagar_com_login(cliente, reserva, cartao):
    from django.test import Client

    c = Client()
    c.force_login(cliente)
    return c.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=cartao,
        content_type="application/json",
    ).json()


@pytest.mark.django_db
def test_recusa_nao_altera_a_reserva(autenticado, reserva):
    """FR-026, FR-027 — o lugar continua com dono e com o prazo original."""
    antes_status = reserva.status
    antes_prazo = reserva.expires_at

    resposta = _pagar(autenticado, reserva, SEM_SALDO)

    reserva.refresh_from_db()
    assert reserva.status == antes_status == Reservation.Status.HELD
    assert reserva.expires_at == antes_prazo
    # O prazo volta no corpo justamente para que a ausência de mudança seja
    # observável de fora.
    assert resposta.json()["expira_em"][:19] == antes_prazo.isoformat()[:19]


@pytest.mark.django_db
def test_recusa_nao_libera_o_lugar(autenticado, client, reserva, sessao, lugares):
    """SC-007 — a leitura do Princípio II depende disto ser verdade."""
    _pagar(autenticado, reserva, SEM_SALDO)

    corpo = client.get(reverse("screening:seat-map", args=[sessao.pk])).json()
    situacoes = {
        (f["letra"], a["numero"]): a["situacao"]
        for f in corpo["fileiras"]
        for a in f["assentos"]
    }
    for lugar in lugares:
        assert situacoes[(lugar.row, lugar.number)] == "tomado"


@pytest.mark.django_db
def test_recusa_nao_emite_ingresso(autenticado, reserva):
    _pagar(autenticado, reserva, EXPIRADO)

    assert not Ticket.objects.filter(reserved_seat__reservation=reserva).exists()
    assert not Payment.objects.filter(
        reservation=reserva, status=Payment.Status.APPROVED
    ).exists()


@pytest.mark.django_db
def test_toda_tentativa_recusada_fica_gravada(autenticado, reserva):
    """FR-012, R8 — e é o que prova que a recusa não sobe como exceção.

    Se a recusa fosse levantada dentro de `transaction.atomic()`, o rollback
    desfaria o INSERT deste mesmo registro, e o rastro sumiria justamente no
    caso que ele existe para registrar.
    """
    _pagar(autenticado, reserva, SEM_SALDO)
    _pagar(autenticado, reserva, EXPIRADO)
    _pagar(autenticado, reserva, RECUSADO_EMISSOR)

    recusas = Payment.objects.filter(reservation=reserva, status=Payment.Status.DECLINED)
    assert recusas.count() == 3
    assert set(recusas.values_list("decline_reason", flat=True)) == {
        "saldo_insuficiente",
        "cartao_expirado",
        "recusado_pelo_emissor",
    }


@pytest.mark.django_db
def test_depois_de_recusas_uma_aprovacao_emite_um_conjunto_so(autenticado, reserva):
    """FR-028, US2-6."""
    _pagar(autenticado, reserva, SEM_SALDO)
    _pagar(autenticado, reserva, RECUSADO_EMISSOR)

    resposta = _pagar(autenticado, reserva, APROVADO)

    assert resposta.status_code == 201
    assert Ticket.objects.filter(reserved_seat__reservation=reserva).count() == 3
    assert (
        Payment.objects.filter(
            reservation=reserva, status=Payment.Status.APPROVED
        ).count()
        == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "numero", ["1234", "4242424242424241", "abcd", "", "424242424242424242424"]
)
def test_numero_mal_formado_e_400_nao_402(autenticado, reserva, numero):
    """FR-010 — numa a pessoa corrige, na outra troca de cartão."""
    resposta = _pagar(autenticado, reserva, {**APROVADO, "numero": numero})

    assert resposta.status_code == 400, resposta.content
    assert resposta.json()["detail"]


@pytest.mark.django_db
def test_preenchimento_invalido_nao_grava_tentativa(autenticado, reserva):
    _pagar(autenticado, reserva, {**APROVADO, "numero": "1234"})

    assert not Payment.objects.filter(reservation=reserva).exists()


@pytest.mark.django_db
def test_recusa_do_serializer_tambem_sai_em_portugues(autenticado, reserva):
    """FR-045, FR-046 — o caminho que nenhuma revisão de texto alcança.

    Encontrado ao rodar a suíte: um campo vazio era recusado pelo próprio DRF,
    ANTES do serviço, e a resposta saía `{"numero": ["This field may not be
    blank."]}` — inglês, nome de campo de framework, e ecoando a entrada. Os
    limites de tamanho e tipo ainda passam por lá, então a tradução vale para
    todos eles, não só para o campo vazio.
    """
    resposta = _pagar(autenticado, reserva, {**APROVADO, "numero": "4" * 200})

    assert resposta.status_code == 400
    corpo = resposta.json()
    assert list(corpo) == ["detail"], f"vazou formato de erro do DRF: {corpo}"
    assert "This field" not in corpo["detail"]
    assert corpo["detail"] == "Confira os dados do cartão."


@pytest.mark.django_db
def test_erro_de_preenchimento_nao_ecoa_o_numero(autenticado, reserva):
    """FR-011 — é assim que um número de cartão acaba em log de servidor."""
    numero = "4242424242424241"
    resposta = _pagar(autenticado, reserva, {**APROVADO, "numero": numero})

    assert numero not in resposta.content.decode()


# --- US3: estados que não podem ser pagos -----------------------------------


@pytest.mark.django_db
def test_reserva_vencida_nao_pode_ser_paga(autenticado, reserva):
    """FR-023."""
    Reservation.objects.filter(pk=reserva.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    resposta = _pagar(autenticado, reserva)

    assert resposta.status_code == 409
    assert resposta.json()["situacao"] == "expirada"
    assert not Ticket.objects.filter(reserved_seat__reservation=reserva).exists()
    assert not Payment.objects.filter(
        reservation=reserva, status=Payment.Status.APPROVED
    ).exists()


@pytest.mark.django_db
def test_pagar_duas_vezes_nao_emite_dois_conjuntos(autenticado, reserva):
    """FR-022, US3-4."""
    primeira = _pagar(autenticado, reserva)
    assert primeira.status_code == 201
    codigos = sorted(i["codigo"] for i in primeira.json()["ingressos"])

    segunda = _pagar(autenticado, reserva)

    assert segunda.status_code == 409
    corpo = segunda.json()
    assert corpo["situacao"] == "paga"
    # Leva aos ingressos que já existem, em vez de só negar.
    assert sorted(i["codigo"] for i in corpo["ingressos"]) == codigos
    assert Ticket.objects.filter(reserved_seat__reservation=reserva).count() == 3


@pytest.mark.django_db
def test_reserva_cancelada_nao_pode_ser_paga(autenticado, reserva):
    """FR-024."""
    Reservation.objects.filter(pk=reserva.pk).update(
        status=Reservation.Status.CANCELLED
    )

    resposta = _pagar(autenticado, reserva)

    assert resposta.status_code == 409
    assert resposta.json()["situacao"] == "cancelada"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mudanca",
    [
        {"status": Screening.Status.CANCELLED},
        {"starts_at": timezone.now() - timedelta(minutes=5)},
    ],
)
def test_sessao_indisponivel_nao_pode_ser_paga(autenticado, reserva, sessao, mudanca):
    """FR-025."""
    Screening.objects.filter(pk=sessao.pk).update(**mudanca)

    resposta = _pagar(autenticado, reserva)

    assert resposta.status_code == 409
    assert resposta.json()["situacao"] == "indisponivel"
    assert not Ticket.objects.filter(reserved_seat__reservation=reserva).exists()


@pytest.mark.django_db
def test_a_recusa_por_vencimento_vem_do_servidor(client, cliente, reserva):
    """FR-029 — sem front-end no caminho, a recusa continua."""
    Reservation.objects.filter(pk=reserva.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    client.force_login(cliente)

    resposta = client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 409


# --- US4: papéis e propriedade ----------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("papel", ["ORGANIZER", "GATE"])
def test_papel_que_nao_compra_recebe_403(client, reserva, papel):
    """FR-041, FR-042, SC-012 — e a recusa é do servidor."""
    usuario = User.objects.create_user(
        username=f"nao_cliente_{papel}", password=SENHA, role=getattr(User.Role, papel)
    )
    client.force_login(usuario)

    resposta = client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 403
    assert "pagar" in resposta.json()["detail"].lower()
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_cliente_nao_paga_reserva_de_outro(client, outro_cliente, reserva):
    """FR-040 — 404 e não 403: um 403 confirmaria que ela existe."""
    client.force_login(outro_cliente)

    resposta = client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 404
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_sem_sessao_ativa_e_401_e_nada_e_cobrado(client, reserva):
    """FR-044."""
    resposta = client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 401
    assert "Entre" in resposta.json()["detail"]
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_cliente_nao_alcanca_ingressos_de_outro(autenticado, client, outro_cliente, reserva):
    """FR-043."""
    _pagar(autenticado, reserva)

    client.force_login(outro_cliente)
    resposta = client.get(reverse("screening:reservation-detail", args=[reserva.pk]))

    assert resposta.status_code == 404
    assert "codigo" not in resposta.content.decode()


@pytest.mark.django_db
def test_pagamento_funciona_com_a_checagem_de_csrf_ligada(cliente, reserva):
    """A falha que a caminhada manual da 007 pegou e a suíte não pegava.

    O `Client()` padrão marca a requisição com `_dont_enforce_csrf_checks`, e
    a `SessionAuthentication` do DRF respeita a marca — então uma rota que
    recusa o proxy do Next em produção passa nos testes. Com
    `enforce_csrf_checks=True` o cenário do proxy é reproduzido de verdade.
    """
    from django.test import Client

    c = Client(enforce_csrf_checks=True)
    c.force_login(cliente)

    resposta = c.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 201, (
        "o autenticador padrão voltou: o proxy do Next receberia 403"
    )


@pytest.mark.django_db
def test_reserva_inexistente_devolve_404(autenticado):
    resposta = autenticado.post(
        reverse("screening:payment-create", args=[999999]),
        data=APROVADO,
        content_type="application/json",
    )

    assert resposta.status_code == 404


@pytest.mark.django_db
def test_ocupacoes_da_reserva_paga_recebem_um_ingresso_cada(autenticado, reserva):
    """FR-014, no banco e não só na resposta."""
    _pagar(autenticado, reserva)

    ocupacoes = ReservedSeat.objects.filter(reservation=reserva)
    for ocupacao in ocupacoes:
        assert Ticket.objects.filter(reserved_seat=ocupacao).count() == 1
    assert Ticket.objects.filter(reserved_seat__reservation=reserva).count() == ocupacoes.count()
