"""Contrato da portaria: as sessões, os quatro desfechos e quem pode validar.

A prova de concorrência mora em `test_gate_concurrency.py` e a de assinatura em
`test_gate_signature.py`. Aqui ficam os desfechos que uma conexão só demonstra
— e, na frente de tudo, a guarda contra a armadilha herdada.

É a SEGUNDA vez que `sellable()` seria o erro natural: a 009 registrou a
primeira, com o histórico de ingressos. Aqui é pior, porque some justamente a
sessão que a porta está recebendo neste momento.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import Room, Screening, Ticket
from apps.screening.services import ingressos as ingressos_service

User = get_user_model()

SENHA = "desafio2026"


@pytest.fixture
def porteiro(db):
    return User.objects.create_user(
        username="portaria", password=SENHA, role=User.Role.GATE
    )


@pytest.fixture
def cliente(db):
    return User.objects.create_user(
        username="cliente1", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def sessao_de_hoje(make_movie, make_screening, seats, room):
    """Uma sessão daqui a duas horas — hoje, e ainda não começada."""
    return make_screening(make_movie("A Odisseia"), hours_from_now=2)


@pytest.fixture
def ingresso(sessao_de_hoje, room, cliente, make_tickets):
    lugares = list(room.seats.filter(kind="common")[:1])
    return make_tickets(sessao_de_hoje, cliente, lugares, minutes_left=10)[0]


def _codigo(ingresso):
    return ingressos_service.assinar_codigo(
        ingresso.public_id, ingresso.reserved_seat.screening_id
    )


def _listar(client):
    return client.get(reverse("screening:gate-screenings"))


def _validar(client, codigo, sessao):
    return client.post(
        reverse("screening:gate-validate"),
        data={"codigo": codigo, "sessao": sessao},
        content_type="application/json",
    )


# --- US1: a armadilha herdada e a lista de sessões ------------------------


@pytest.mark.django_db
def test_lista_inclui_sessao_que_ja_comecou(
    client, porteiro, make_movie, make_screening, make_seats
):
    """A porta precisa exatamente do que `sellable()` exclui.

    Gente chega atrasada, e a portaria valida durante a sessão inteira. Se
    este teste falhar com a sessão ausente, alguma consulta está usando o
    filtro de vendabilidade.
    """
    sala = Room.objects.create(name="Sala em andamento", capacity=5)
    make_seats(sala, acessiveis=0)
    make_screening(
        make_movie("Já começou"), hours_from_now=-1, room_obj=sala
    )
    client.force_login(porteiro)

    titulos = [s["filme"] for s in _listar(client).json()["sessoes"]]

    assert "Já começou" in titulos


@pytest.mark.django_db
def test_lista_exclui_sessao_cancelada(
    client, porteiro, make_movie, make_screening, make_seats
):
    """Não há entrada a receber numa sessão cancelada."""
    sala = Room.objects.create(name="Sala cancelada", capacity=5)
    make_seats(sala, acessiveis=0)
    make_screening(
        make_movie("Cancelada"),
        hours_from_now=3,
        status=Screening.Status.CANCELLED,
        room_obj=sala,
    )
    client.force_login(porteiro)

    titulos = [s["filme"] for s in _listar(client).json()["sessoes"]]

    assert "Cancelada" not in titulos


@pytest.mark.django_db
def test_lista_traz_filme_horario_e_sala_e_ordena_por_horario(
    client, porteiro, sessao_de_hoje, make_movie, make_screening, make_seats
):
    sala = Room.objects.create(name="Sala tardia", capacity=5)
    make_seats(sala, acessiveis=0)
    make_screening(make_movie("Mais tarde"), hours_from_now=6, room_obj=sala)
    client.force_login(porteiro)

    sessoes = _listar(client).json()["sessoes"]

    assert all({"id", "filme", "inicio", "sala"} == set(s) for s in sessoes)
    assert [s["inicio"] for s in sessoes] == sorted(s["inicio"] for s in sessoes)


@pytest.mark.django_db
def test_sem_sessao_hoje_devolve_200_com_lista_vazia(client, porteiro):
    """Não é `404`: é um estado da portaria, não a ausência de um recurso."""
    client.force_login(porteiro)

    resposta = _listar(client)

    assert resposta.status_code == 200
    assert resposta.json() == {"sessoes": []}


# --- US2: válido ----------------------------------------------------------


@pytest.mark.django_db
def test_primeira_validacao_e_valida_e_traz_o_lugar(
    client, porteiro, ingresso, sessao_de_hoje
):
    """FR-020 — o lugar é o que o operador diz à pessoa."""
    client.force_login(porteiro)

    resposta = _validar(client, _codigo(ingresso), sessao_de_hoje.pk)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["situacao"] == "valido"
    assert corpo["ingresso"]["assento"]["fileira"]
    assert "Pode entrar" in corpo["detail"]


@pytest.mark.django_db
def test_codigo_vazio_e_400_distinto_de_invalido(client, porteiro, sessao_de_hoje):
    """FR-014 — nada foi apresentado; não há o que julgar."""
    client.force_login(porteiro)

    resposta = _validar(client, "   ", sessao_de_hoje.pk)

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Apresente ou digite um código."


@pytest.mark.django_db
def test_sessao_da_porta_ausente_ou_inexistente_e_400(client, porteiro, ingresso):
    client.force_login(porteiro)

    sem_sessao = _validar(client, _codigo(ingresso), None)
    inexistente = _validar(client, _codigo(ingresso), 999999)

    for resposta in (sem_sessao, inexistente):
        assert resposta.status_code == 400
        assert "Escolha a sessão" in resposta.json()["detail"]


@pytest.mark.django_db
def test_espacos_e_quebras_de_linha_sao_tolerados(
    client, porteiro, ingresso, sessao_de_hoje
):
    """FR-013 — copiar de um aplicativo de mensagens traz isso junto."""
    client.force_login(porteiro)

    resposta = _validar(client, f"  \n{_codigo(ingresso)}\n  ", sessao_de_hoje.pk)

    assert resposta.json()["situacao"] == "valido"


# --- US4: já utilizado ----------------------------------------------------


@pytest.mark.django_db
def test_segunda_apresentacao_e_ja_utilizado_com_o_instante(
    client, porteiro, ingresso, sessao_de_hoje
):
    """FR-021 — o instante é o que permite julgar quem está apresentando."""
    client.force_login(porteiro)
    codigo = _codigo(ingresso)

    _validar(client, codigo, sessao_de_hoje.pk)
    resposta = _validar(client, codigo, sessao_de_hoje.pk)

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["situacao"] == "ja_utilizado"
    assert corpo["utilizado_em"]
    assert "já foi usado às" in corpo["detail"]


@pytest.mark.django_db
def test_o_instante_do_primeiro_uso_nunca_muda(
    client, porteiro, ingresso, sessao_de_hoje
):
    """FR-033, SC-006."""
    client.force_login(porteiro)
    codigo = _codigo(ingresso)

    primeiro = _validar(client, codigo, sessao_de_hoje.pk)
    ingresso.refresh_from_db()
    instante = ingresso.used_at

    for _ in range(3):
        repetida = _validar(client, codigo, sessao_de_hoje.pk)
        assert repetida.json()["situacao"] == "ja_utilizado"

    ingresso.refresh_from_db()
    assert ingresso.used_at == instante
    assert primeiro.json()["situacao"] == "valido"


# --- US6: sessão errada ---------------------------------------------------


@pytest.fixture
def outra_sessao(make_movie, make_screening, make_seats):
    sala = Room.objects.create(name="Sala vizinha", capacity=5)
    make_seats(sala, acessiveis=0)
    return make_screening(make_movie("Filme vizinho"), hours_from_now=5, room_obj=sala)


@pytest.mark.django_db
def test_ingresso_de_outra_sessao_e_sessao_errada(
    client, porteiro, ingresso, outra_sessao
):
    """FR-022 — e informa a qual sessão o ingresso pertence."""
    client.force_login(porteiro)

    corpo = _validar(client, _codigo(ingresso), outra_sessao.pk).json()

    assert corpo["situacao"] == "sessao_errada"
    assert corpo["sessao_do_ingresso"]["filme"] == "A Odisseia"
    assert corpo["sessao_do_ingresso"]["sala"]
    assert corpo["sessao_do_ingresso"]["cancelada"] is False


@pytest.mark.django_db
def test_sessao_errada_nao_consome_o_ingresso(
    client, porteiro, ingresso, sessao_de_hoje, outra_sessao
):
    """FR-031 — o teste que pega o dia em que a checagem passar a escrever.

    Queimar um ingresso legítimo na porta errada é irreversível.
    """
    client.force_login(porteiro)
    codigo = _codigo(ingresso)

    _validar(client, codigo, outra_sessao.pk)

    ingresso.refresh_from_db()
    assert ingresso.used_at is None

    # E na porta certa continua valendo.
    assert _validar(client, codigo, sessao_de_hoje.pk).json()["situacao"] == "valido"


@pytest.mark.django_db
def test_ja_utilizado_e_de_outra_sessao_responde_sessao_errada(
    client, porteiro, ingresso, sessao_de_hoje, outra_sessao
):
    """FR-030 — a ordem entre as duas checagens.

    É essa a informação que muda a ação do operador: a pessoa está na porta
    errada, e é isso que ele precisa dizer a ela.
    """
    client.force_login(porteiro)
    codigo = _codigo(ingresso)
    _validar(client, codigo, sessao_de_hoje.pk)  # consome

    corpo = _validar(client, codigo, outra_sessao.pk).json()

    assert corpo["situacao"] == "sessao_errada"


@pytest.mark.django_db
def test_ingresso_de_sessao_cancelada_avisa_dentro_do_mesmo_desfecho(
    client, porteiro, sessao_de_hoje, ingresso, outra_sessao
):
    """FR-023, FR-024 — informação DENTRO do desfecho, nunca um quinto."""
    sessao_de_hoje.status = Screening.Status.CANCELLED
    sessao_de_hoje.save(update_fields=["status"])
    client.force_login(porteiro)

    corpo = _validar(client, _codigo(ingresso), outra_sessao.pk).json()

    assert corpo["situacao"] == "sessao_errada"
    assert corpo["sessao_do_ingresso"]["cancelada"] is True
    assert "cancelada" in corpo["detail"]


@pytest.mark.django_db
def test_existem_exatamente_quatro_situacoes(
    client, porteiro, ingresso, sessao_de_hoje, outra_sessao
):
    """FR-016, FR-024 — nenhum quinto desfecho pode nascer."""
    client.force_login(porteiro)
    codigo = _codigo(ingresso)

    vistos = {
        _validar(client, "forjado:demais", sessao_de_hoje.pk).json()["situacao"],
        _validar(client, codigo, outra_sessao.pk).json()["situacao"],
        _validar(client, codigo, sessao_de_hoje.pk).json()["situacao"],
        _validar(client, codigo, sessao_de_hoje.pk).json()["situacao"],
    }

    assert vistos == {"invalido", "sessao_errada", "valido", "ja_utilizado"}


# --- US7: papéis ----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("papel", ["customer", "organizer"])
def test_cliente_e_organizador_recebem_403_nos_dois_enderecos(
    client, ingresso, sessao_de_hoje, papel
):
    """FR-040 — `403`, não `401`: eles entraram, só não validam."""
    usuario = User.objects.create_user(
        username=f"user_{papel}", password=SENHA, role=papel
    )
    client.force_login(usuario)

    for resposta in (_listar(client), _validar(client, _codigo(ingresso), sessao_de_hoje.pk)):
        assert resposta.status_code == 403
        assert resposta.json()["detail"] == "Apenas a portaria valida ingressos."


@pytest.mark.django_db
def test_cliente_nao_consegue_marcar_o_proprio_ingresso(
    client, cliente, ingresso, sessao_de_hoje
):
    """A falha que esta recusa previne.

    Sem ela, um cliente marca o próprio ingresso como utilizado e ninguém
    entra com ele depois — nem ele.
    """
    client.force_login(cliente)

    _validar(client, _codigo(ingresso), sessao_de_hoje.pk)

    ingresso.refresh_from_db()
    assert ingresso.used_at is None


@pytest.mark.django_db
def test_visitante_recebe_401_nos_dois_enderecos(client, ingresso, sessao_de_hoje):
    """FR-042."""
    for resposta in (_listar(client), _validar(client, _codigo(ingresso), sessao_de_hoje.pk)):
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "Entre para usar a portaria."


@pytest.mark.django_db
def test_portaria_continua_sem_reservar_e_sem_pagar(client, porteiro, sessao_de_hoje):
    """FR-044 — nenhuma asserção de 007 e 008 enfraquecida."""
    client.force_login(porteiro)

    reserva = client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao_de_hoje.pk,
            "assentos": [],
            "chave_idempotencia": "11111111-1111-1111-1111-111111111111",
        },
        content_type="application/json",
    )

    assert reserva.status_code == 403


# --- A resposta não vaza nada da compra -----------------------------------


@pytest.mark.django_db
def test_resposta_nao_traz_comprador_valor_nem_identificadores(
    client, porteiro, ingresso, sessao_de_hoje
):
    """A portaria confere o ingresso, não a identidade de quem comprou."""
    client.force_login(porteiro)

    corpo = _validar(client, _codigo(ingresso), sessao_de_hoje.pk).content.decode()

    for proibido in (
        "cliente1",
        str(ingresso.public_id),
        "cartao_final",
        "bandeira",
        str(ingresso.reserved_seat.reservation_id),
    ):
        assert proibido not in corpo
