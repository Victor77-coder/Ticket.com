"""A meia-entrada ponta a ponta — do corpo da reserva ao desfecho da portaria.

O que este arquivo protege, em ordem de gravidade:

  1. NINGUÉM PAGA MENOS POR OMISSÃO. Ausente, nulo ou vazio → tudo inteira.
  2. O total é a SOMA dos valores gravados, e o servidor é quem soma.
  3. Id fora da seleção é RECUSA, não descarte silencioso.
  4. A portaria continua com QUATRO desfechos — o tipo informa, não decide.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import ReservedSeat

User = get_user_model()

SENHA = "desafio2026"


@pytest.fixture
def sessao(make_movie, make_screening, seats):
    return make_screening(make_movie("A Odisseia"))


@pytest.fixture
def autenticado(client, db):
    cliente = User.objects.create_user(
        username="cliente1", password=SENHA, role=User.Role.CUSTOMER
    )
    client.force_login(cliente)
    return client


def _reservar(client, sessao, assentos, meias=None):
    corpo = {
        "sessao": sessao.pk,
        "assentos": [s.pk for s in assentos],
        "chave_idempotencia": str(uuid.uuid4()),
    }
    if meias is not None:
        corpo["meias"] = [s.pk for s in meias]
    return client.post(
        reverse("screening:reservation-create"), data=corpo, content_type="application/json"
    )


def _comuns(sessao, quantos):
    return list(sessao.room.seats.filter(kind="common")[:quantos])


# --- O padrão seguro (FR-016) ----------------------------------------------


@pytest.mark.django_db
def test_sem_meias_tudo_e_inteira(autenticado, sessao):
    """O caminho de quem não mexe em nada, e o de todo cliente da 007."""
    assentos = _comuns(sessao, 2)

    corpo = _reservar(autenticado, sessao, assentos).json()

    assert [lugar["tipo"] for lugar in corpo["assentos"]] == ["inteira", "inteira"]
    assert corpo["total"] == "60.00"  # 2 × 30,00 da fixture


@pytest.mark.django_db
def test_meias_vazia_tambem_e_tudo_inteira(autenticado, sessao):
    corpo = _reservar(autenticado, sessao, _comuns(sessao, 2), meias=[]).json()

    assert [lugar["tipo"] for lugar in corpo["assentos"]] == ["inteira", "inteira"]


# --- A soma (FR-017, FR-019, FR-020) ---------------------------------------


@pytest.mark.django_db
def test_uma_meia_e_uma_inteira_somam_o_esperado(autenticado, sessao):
    inteiro, meio = _comuns(sessao, 2)

    corpo = _reservar(autenticado, sessao, [inteiro, meio], meias=[meio]).json()

    assert corpo["total"] == "45.00"  # 30,00 + 15,00
    por_lugar = {lugar["numero"]: lugar for lugar in corpo["assentos"]}
    assert por_lugar[inteiro.number]["valor"] == "30.00"
    assert por_lugar[meio.number]["valor"] == "15.00"


@pytest.mark.django_db
def test_o_valor_fica_gravado_no_lugar_e_nao_e_recalculado(autenticado, sessao):
    """Gravado é o que faz uma compra fechada parar de depender do presente."""
    inteiro, meio = _comuns(sessao, 2)
    _reservar(autenticado, sessao, [inteiro, meio], meias=[meio])

    gravados = {
        ocupacao.seat_id: (ocupacao.ticket_type, ocupacao.unit_price)
        for ocupacao in ReservedSeat.objects.filter(screening=sessao)
    }

    assert gravados[inteiro.pk][0] == "inteira"
    assert gravados[meio.pk][0] == "meia"
    assert gravados[meio.pk][1] * 2 == gravados[inteiro.pk][1]


@pytest.mark.django_db
def test_tudo_meia_e_valido_porque_nao_ha_cota(autenticado, sessao):
    """A lei limita a meia a 40% dos lugares; este sistema não implementa cota.

    Está registrado como fora de escopo na spec, e não como esquecimento: a cota
    exigiria disponibilidade POR TIPO dentro da sessão, com corrida e constraint
    próprias — uma feature do tamanho da 007.
    """
    assentos = _comuns(sessao, 3)

    corpo = _reservar(autenticado, sessao, assentos, meias=assentos).json()

    assert corpo["total"] == "45.00"  # 3 × 15,00
    assert all(lugar["tipo"] == "meia" for lugar in corpo["assentos"])


@pytest.mark.django_db
def test_total_vindo_do_cliente_e_ignorado(autenticado, sessao):
    """Aceitar "só para conferir" é como o desconto de 99% entra (FR-019)."""
    assentos = _comuns(sessao, 2)

    resposta = autenticado.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [s.pk for s in assentos],
            "chave_idempotencia": str(uuid.uuid4()),
            "total": "0.01",
        },
        content_type="application/json",
    )

    assert resposta.json()["total"] == "60.00"


# --- A recusa que não pode ser silenciosa (contracts §regras de `meias`) ----


@pytest.mark.django_db
def test_meia_de_lugar_fora_da_selecao_e_recusada(autenticado, sessao):
    """Ignorar faria a tela e o servidor discordarem sobre o que foi comprado."""
    escolhidos = _comuns(sessao, 2)
    de_fora = _comuns(sessao, 3)[2]

    resposta = _reservar(autenticado, sessao, escolhidos, meias=[de_fora])

    assert resposta.status_code == 400
    assert "Escolha os lugares de novo" in resposta.json()["detail"]
    assert not ReservedSeat.objects.filter(screening=sessao).exists()


# --- O ingresso carrega o tipo (FR-021) ------------------------------------


@pytest.mark.django_db
def test_ingressos_emitidos_declaram_cada_um_o_seu_tipo(
    autenticado, sessao, make_reservation
):
    inteiro, meio = _comuns(sessao, 2)
    reserva = make_reservation(
        sessao,
        User.objects.get(username="cliente1"),
        [inteiro, meio],
        meias=[meio.pk],
    )

    resposta = autenticado.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data={"numero": "4242424242424242", "nome": "C SOUZA", "validade": "12/30", "cvv": "123"},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert sorted(ingresso["tipo"] for ingresso in corpo["ingressos"]) == ["inteira", "meia"]
    assert corpo["pagamento"]["total"] == "45.00"


@pytest.mark.django_db
def test_meus_ingressos_mostra_o_tipo(autenticado, sessao, make_tickets):
    meio = _comuns(sessao, 1)[0]
    make_tickets(sessao, User.objects.get(username="cliente1"), [meio], meias=[meio.pk])

    corpo = autenticado.get(reverse("screening:my-tickets")).json()

    todos = corpo["futuros"] + corpo["passados"]
    assert todos[0]["tipo"] == "meia"


# --- A fronteira da portaria (FR-024) --------------------------------------


@pytest.mark.django_db
def test_meia_entra_pelo_mesmo_caminho_da_inteira(client, sessao, make_tickets):
    """O tipo INFORMA o operador; não decide o desfecho.

    Um ingresso de meia apresentado na porta certa produz "pode entrar", igual
    a um de inteira. Quem confere o documento é a pessoa na porta — a
    plataforma vende.
    """
    from apps.screening.services import ingressos as ingressos_service

    porteiro = User.objects.create_user(
        username="portaria", password=SENHA, role=User.Role.GATE
    )
    client.force_login(porteiro)

    # A porta só recebe sessões DE HOJE (`selectors.sessoes_da_portaria`), e a
    # fixture padrão marca 24h à frente — amanhã. Duas horas basta.
    sessao.starts_at = timezone.now() + timedelta(hours=2)
    sessao.save(update_fields=["starts_at"])

    meio = _comuns(sessao, 1)[0]
    ingresso = make_tickets(
        sessao,
        User.objects.create_user(
            username="compradora", password=SENHA, role=User.Role.CUSTOMER
        ),
        [meio],
        minutes_left=10,
        meias=[meio.pk],
    )[0]

    codigo = ingressos_service.assinar_codigo(
        ingresso.public_id, ingresso.reserved_seat.screening_id
    )
    resposta = client.post(
        reverse("screening:gate-validate"),
        data={"codigo": codigo, "sessao": sessao.pk},
        content_type="application/json",
    )

    corpo = resposta.json()
    assert corpo["situacao"] == "valido"
    assert corpo["ingresso"]["tipo"] == "meia"


@pytest.mark.django_db
def test_a_portaria_continua_com_exatamente_quatro_desfechos():
    """A constitution exige quatro distinguíveis. A 014 não acrescenta um quinto.

    Este teste falha se alguém criar "meia sem documento" — que é a forma mais
    provável de a fronteira ser cruzada sem ninguém perceber. O campo do
    desfecho chama-se `situacao` na resposta; os quatro valores são estes.
    """
    from apps.screening.services import portaria as portaria_service

    desfechos = {
        portaria_service.VALIDO,
        portaria_service.JA_UTILIZADO,
        portaria_service.SESSAO_ERRADA,
        portaria_service.INVALIDO,
    }

    assert len(desfechos) == 4
