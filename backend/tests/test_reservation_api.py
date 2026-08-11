"""Contrato da API de reserva.

Cobre o que a corrida não cobre: as recusas, as mensagens, a autorização e a
expiração. A prova de concorrência mora em `test_reservation_concurrency.py`
— aqui o banco é de teste comum, com transação envolvente, e é adequado
porque nenhum destes casos depende de duas conexões.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import Reservation, ReservedSeat, Screening

User = get_user_model()

SENHA = "desafio2026"


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
def autenticado(client, cliente):
    client.force_login(cliente)
    return client


def _reservar(client, sessao, assentos, chave=None):
    return client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [s.pk for s in assentos],
            "chave_idempotencia": str(chave or uuid.uuid4()),
        },
        content_type="application/json",
    )


def _comuns(sessao, quantos):
    return list(sessao.room.seats.filter(kind="common")[:quantos])


# --- Caminho feliz (FR-020, FR-028) ----------------------------------------


@pytest.mark.django_db
def test_cliente_reserva_e_recebe_prazo(autenticado, sessao):
    assentos = _comuns(sessao, 2)

    resposta = _reservar(autenticado, sessao, assentos)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["situacao"] == "reservada"
    assert corpo["total"] == "60.00"  # 2 × 30,00 da fixture
    assert len(corpo["assentos"]) == 2
    assert corpo["expira_em"]


@pytest.mark.django_db
def test_expira_em_e_instante_absoluto_nao_contagem(autenticado, sessao):
    """O relógio do navegador pode estar errado.

    Mandar "600 segundos restantes" faria a contagem derivar; um alvo fixo
    não deriva.
    """
    resposta = _reservar(autenticado, sessao, _comuns(sessao, 1))

    valor = resposta.json()["expira_em"]
    assert isinstance(valor, str)
    assert "T" in valor  # ISO-8601, não um número de segundos


@pytest.mark.django_db
def test_lugares_vem_nomeados_por_fileira_e_numero(autenticado, sessao):
    assentos = _comuns(sessao, 2)

    corpo = _reservar(autenticado, sessao, assentos).json()

    assert corpo["assentos"] == [
        {"fileira": s.row, "numero": s.number} for s in assentos
    ]


@pytest.mark.django_db
def test_reserva_aparece_como_ocupacao_no_mapa(autenticado, sessao):
    assentos = _comuns(sessao, 2)
    _reservar(autenticado, sessao, assentos)

    mapa = autenticado.get(reverse("screening:seat-map", args=[sessao.pk])).json()
    tomados = {
        a["id"]
        for f in mapa["fileiras"]
        for a in f["assentos"]
        if a["situacao"] == "tomado"
    }

    assert tomados == {s.pk for s in assentos}


# --- Seleção inválida (FR-009, FR-013, FR-014) -----------------------------


@pytest.mark.django_db
def test_selecao_vazia_e_recusada(autenticado, sessao):
    resposta = _reservar(autenticado, sessao, [])

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Escolha ao menos um lugar."


@pytest.mark.django_db
def test_acima_do_limite_e_recusado(autenticado, sessao):
    resposta = _reservar(autenticado, sessao, _comuns(sessao, 7))

    assert resposta.status_code == 400
    assert "6 lugares" in resposta.json()["detail"]


@pytest.mark.django_db
def test_assento_de_outra_sala_e_recusado(autenticado, sessao, make_seats):
    from apps.screening.models import Room

    outra_sala = Room.objects.create(name="Sala Alheia", capacity=20)
    alheio = make_seats(outra_sala)[0]

    resposta = _reservar(autenticado, sessao, [alheio])

    assert resposta.status_code == 400
    assert "não existe nesta sala" in resposta.json()["detail"]


@pytest.mark.django_db
def test_assento_de_acessibilidade_fora_do_fluxo_comum(autenticado, sessao):
    """Esconder o lugar na interface não impede ninguém de pedi-lo pela API."""
    acessivel = sessao.room.seats.filter(kind="accessible").first()

    resposta = _reservar(autenticado, sessao, [acessivel])

    assert resposta.status_code == 400
    assert "acessibilidade" in resposta.json()["detail"]


# --- Atomicidade (FR-018, FR-019, SC-009) ----------------------------------


@pytest.mark.django_db
def test_selecao_com_lugar_tomado_nao_reserva_nenhum(
    autenticado, sessao, outro_cliente, make_reservation
):
    livre, disputado = _comuns(sessao, 2)
    make_reservation(sessao, outro_cliente, [disputado])

    resposta = _reservar(autenticado, sessao, [livre, disputado])

    assert resposta.status_code == 409
    # Nenhum dos dois foi reservado — nem o que estava livre.
    assert not ReservedSeat.objects.filter(screening=sessao, seat=livre).exists()
    assert ReservedSeat.objects.filter(screening=sessao).count() == 1


@pytest.mark.django_db
def test_recusa_nomeia_o_lugar_que_causou(
    autenticado, sessao, outro_cliente, make_reservation
):
    """"Escolha outro" sem dizer qual obriga a tentar de novo às cegas."""
    livre, disputado = _comuns(sessao, 2)
    make_reservation(sessao, outro_cliente, [disputado])

    corpo = _reservar(autenticado, sessao, [livre, disputado]).json()

    assert f"{disputado.row}{disputado.number}" in corpo["detail"]
    assert corpo["assentos_indisponiveis"] == [
        {"fileira": disputado.row, "numero": disputado.number}
    ]


@pytest.mark.django_db
def test_falha_nao_deixa_reserva_orfa(
    autenticado, sessao, outro_cliente, make_reservation
):
    """Ou a reserva existe por inteiro, ou não existe."""
    livre, disputado = _comuns(sessao, 2)
    make_reservation(sessao, outro_cliente, [disputado])
    antes = Reservation.objects.count()

    _reservar(autenticado, sessao, [livre, disputado])

    assert Reservation.objects.count() == antes


# --- Idempotência (FR-023) -------------------------------------------------


@pytest.mark.django_db
def test_envio_duplo_com_a_mesma_chave_cria_uma_reserva_so(autenticado, sessao):
    assentos = _comuns(sessao, 2)
    chave = uuid.uuid4()

    primeira = _reservar(autenticado, sessao, assentos, chave=chave)
    segunda = _reservar(autenticado, sessao, assentos, chave=chave)

    assert primeira.status_code == 201
    # 200, não 201: é o que permite ao front distinguir "criei" de "já era
    # minha" sem adivinhar.
    assert segunda.status_code == 200
    assert primeira.json()["id"] == segunda.json()["id"]
    assert Reservation.objects.count() == 1


@pytest.mark.django_db
def test_chaves_diferentes_criam_reservas_diferentes(autenticado, sessao):
    a, b = _comuns(sessao, 2)

    _reservar(autenticado, sessao, [a])
    _reservar(autenticado, sessao, [b])

    assert Reservation.objects.count() == 2


@pytest.mark.django_db
def test_chave_de_outro_cliente_nao_devolve_a_reserva_alheia(
    autenticado, sessao, outro_cliente
):
    chave = uuid.uuid4()
    Reservation.objects.create(
        screening=sessao,
        customer=outro_cliente,
        expires_at=timezone.now() + timedelta(minutes=10),
        idempotency_key=chave,
    )

    resposta = _reservar(autenticado, sessao, _comuns(sessao, 1), chave=chave)

    assert resposta.status_code == 400
    assert "cliente2" not in resposta.content.decode()


# --- Sessão não vendável (FR-002, FR-003) ----------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("cenario", ["rascunho", "cancelada", "ja_comecou"])
def test_sessao_nao_vendavel_recusa_a_reserva(
    autenticado, cenario, make_movie, make_screening, seats
):
    filme = make_movie()
    if cenario == "rascunho":
        alvo = make_screening(filme, status=Screening.Status.DRAFT)
    elif cenario == "cancelada":
        alvo = make_screening(filme, status=Screening.Status.CANCELLED)
    else:
        alvo = make_screening(filme, hours_from_now=-2)

    resposta = _reservar(autenticado, alvo, _comuns(alvo, 1))

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Sessão não encontrada."
    assert not Reservation.objects.exists()


@pytest.mark.django_db
def test_sessao_inexistente_recusa(autenticado):
    resposta = autenticado.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": 999999,
            "assentos": [1],
            "chave_idempotencia": str(uuid.uuid4()),
        },
        content_type="application/json",
    )

    assert resposta.status_code == 404


# --- Autorização (FR-024, FR-025, FR-026, FR-027) ---------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("papel", [User.Role.ORGANIZER, User.Role.GATE])
def test_papel_que_nao_compra_recebe_403(client, sessao, papel):
    """A recusa é do servidor — esconder o botão não conta (FR-025)."""
    usuario = User.objects.create_user(
        username=f"nao_compra_{papel}", password=SENHA, role=papel
    )
    client.force_login(usuario)

    resposta = _reservar(client, sessao, _comuns(sessao, 1))

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Apenas clientes podem reservar lugares."
    assert not Reservation.objects.exists()


@pytest.mark.django_db
def test_sem_sessao_recebe_401(client, sessao):
    resposta = _reservar(client, sessao, _comuns(sessao, 1))

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Entre para reservar."


@pytest.mark.django_db
def test_reserva_funciona_com_a_checagem_de_csrf_ligada(cliente, sessao):
    """O caminho real do Next, que o cliente de teste padrão esconde.

    `Client()` marca a requisição com `_dont_enforce_csrf_checks`, e a
    `SessionAuthentication` do DRF respeita essa marca — então todo o resto
    da suíte passa mesmo que a rota recuse o proxy em produção. Foi assim que
    o `403` "Apenas clientes podem reservar lugares." apareceu no quickstart
    com um cliente legítimo: era falha de CSRF disfarçada de falha de papel.

    O Next chama servidor-a-servidor, sem token de CSRF, e é isso que este
    teste exercita.
    """
    from django.test import Client

    com_csrf = Client(enforce_csrf_checks=True)
    com_csrf.force_login(cliente)

    resposta = _reservar(com_csrf, sessao, _comuns(sessao, 1))

    assert resposta.status_code == 201


@pytest.mark.django_db
def test_cliente_nao_ve_reserva_de_outro(
    autenticado, sessao, outro_cliente, make_reservation
):
    """404, não 403: um 403 confirmaria que a reserva existe (FR-027)."""
    reserva = make_reservation(sessao, outro_cliente, _comuns(sessao, 1))

    resposta = autenticado.get(
        reverse("screening:reservation-detail", args=[reserva.pk])
    )

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Reserva não encontrada."}
    assert "cliente2" not in resposta.content.decode()


@pytest.mark.django_db
def test_dono_consulta_a_propria_reserva(autenticado, sessao, cliente, make_reservation):
    reserva = make_reservation(sessao, cliente, _comuns(sessao, 2))

    resposta = autenticado.get(
        reverse("screening:reservation-detail", args=[reserva.pk])
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == reserva.pk
    assert resposta.json()["situacao"] == "reservada"


# --- Expiração sem rotina agendada (FR-021, FR-022) ------------------------


@pytest.mark.django_db
def test_reserva_vencida_aparece_livre_no_mapa(
    autenticado, sessao, outro_cliente, make_reservation
):
    """A liberação é por consulta — nenhuma rotina precisa ter rodado."""
    assentos = _comuns(sessao, 2)
    make_reservation(sessao, outro_cliente, assentos, minutes_left=-1)

    mapa = autenticado.get(reverse("screening:seat-map", args=[sessao.pk])).json()
    situacoes = {
        a["id"]: a["situacao"]
        for f in mapa["fileiras"]
        for a in f["assentos"]
        if a["id"] in {s.pk for s in assentos}
    }

    assert all(s == "livre" for s in situacoes.values())


@pytest.mark.django_db
def test_outro_cliente_reserva_lugares_vencidos(
    autenticado, sessao, outro_cliente, make_reservation
):
    assentos = _comuns(sessao, 2)
    antiga = make_reservation(sessao, outro_cliente, assentos, minutes_left=-1)

    resposta = _reservar(autenticado, sessao, assentos)

    assert resposta.status_code == 201
    # A linha antiga foi removida, não duplicada — a constraint absoluta
    # só tolera uma ocupação por (sessão, assento).
    assert ReservedSeat.objects.filter(screening=sessao, seat__in=assentos).count() == 2
    assert not ReservedSeat.objects.filter(reservation=antiga).exists()


@pytest.mark.django_db
def test_reserva_dentro_do_prazo_continua_bloqueando(
    autenticado, sessao, outro_cliente, make_reservation
):
    disputado = _comuns(sessao, 1)[0]
    make_reservation(sessao, outro_cliente, [disputado], minutes_left=5)

    resposta = _reservar(autenticado, sessao, [disputado])

    assert resposta.status_code == 409
    assert Reservation.objects.filter(customer__username="cliente1").count() == 0


@pytest.mark.django_db
def test_consultar_reserva_vencida_devolve_situacao_expirada(
    autenticado, sessao, cliente, make_reservation
):
    reserva = make_reservation(sessao, cliente, _comuns(sessao, 1), minutes_left=-1)

    resposta = autenticado.get(
        reverse("screening:reservation-detail", args=[reserva.pk])
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["situacao"] == "expirada"
    assert corpo["detail"] == "Esta reserva expirou. Escolha os lugares de novo."
