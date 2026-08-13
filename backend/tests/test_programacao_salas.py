"""Criar sala, trocar capacidade, e o que a ocupação impede — US4.

A regra de geometria em si tem arquivo próprio (`test_sala_paridade_seed.py`).
Aqui é a superfície: o que a API aceita, o que ela recusa, e com qual frase.
"""

import pytest
from django.conf import settings

from apps.screening.models import Seat
from apps.screening.services import salas

SALAS = "/api/v1/programacao/salas/"


@pytest.mark.django_db
def test_lista_vazia_devolve_200(painel):
    """FR-007 — "nenhuma sala" convida a criar a primeira, não é um 404."""
    assert painel.get(SALAS).json() == {"count": 0, "results": []}


@pytest.mark.django_db
def test_cria_a_sala_e_os_lugares_juntos(painel):
    """US4 cenário 1 — a sala nasce com o mapa, nunca vazia."""
    resposta = painel.post(
        SALAS,
        data={"nome": "Sala 3", "capacidade": 45},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Sala 3"
    assert corpo["capacidade"] == 45
    assert corpo["lugares"] == 45
    assert corpo["acessiveis"] == settings.ACCESSIBLE_SEATS_PER_ROOM
    assert corpo["ocupacao_viva"] == 0
    assert corpo["pode_trocar_capacidade"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("capacidade", [0, -5, None, "muitos"])
def test_capacidade_ausente_zero_negativa_ou_ilegivel_e_recusada(painel, capacidade):
    """FR-018 — os quatro casos são o mesmo problema: não há capacidade."""
    corpo = {"nome": "Sala X", "capacidade": capacidade}
    if capacidade is None:
        corpo.pop("capacidade")

    resposta = painel.post(SALAS, data=corpo, content_type="application/json")

    assert resposta.status_code == 400
    assert "capacidade maior que zero" in str(resposta.json()["capacidade"])


@pytest.mark.django_db
def test_capacidade_acima_do_teto_informa_o_limite(painel):
    """A frase diz o teto, e o teto é CALCULADO de `SEATS_PER_ROW`."""
    teto = salas.teto_de_capacidade()

    resposta = painel.post(
        SALAS,
        data={"nome": "Sala gigante", "capacidade": teto + 1},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert str(teto) in str(resposta.json()["capacidade"])


@pytest.mark.django_db
def test_capacidade_exatamente_no_teto_e_aceita(painel):
    """Edge case da spec: o teto é o último valor válido, não o primeiro
    inválido."""
    resposta = painel.post(
        SALAS,
        data={"nome": "Sala cheia", "capacidade": salas.teto_de_capacidade()},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert resposta.json()["lugares"] == salas.teto_de_capacidade()


@pytest.mark.django_db
def test_nome_vazio_e_recusado(painel):
    resposta = painel.post(
        SALAS, data={"nome": "  ", "capacidade": 20}, content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "nome à sala" in str(resposta.json()["nome"])


# --- Trocar capacidade ----------------------------------------------------


@pytest.mark.django_db
def test_troca_de_capacidade_refaz_o_mapa(painel, room):
    """FR-019 — sem ocupação, o mapa é refeito para a capacidade nova."""
    salas.gerar_assentos(room)

    resposta = painel.patch(
        f"{SALAS}{room.pk}/",
        data={"capacidade": 20},
        content_type="application/json",
    )

    assert resposta.status_code == 200
    assert resposta.json()["lugares"] == 20
    assert room.seats.count() == 20


@pytest.mark.django_db
def test_renomear_e_sempre_permitido(painel, room, make_movie, make_screening, make_seats, make_reservation, make_user):
    """O nome não afeta lugar nem venda — nem com a sala lotada."""
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:2])

    resposta = painel.patch(
        f"{SALAS}{room.pk}/",
        data={"nome": "Sala rebatizada"},
        content_type="application/json",
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Sala rebatizada"
    assert room.seats.count() == len(lugares)


@pytest.mark.django_db
def test_troca_com_reserva_viva_e_recusada_sem_apagar_lugar(
    painel, room, make_movie, make_screening, make_seats, make_reservation, make_user
):
    """FR-020 — a frase diz quantos lugares estão ocupados e o que fazer."""
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:4])

    resposta = painel.patch(
        f"{SALAS}{room.pk}/", data={"capacidade": 20}, content_type="application/json"
    )

    assert resposta.status_code == 409
    assert "4 lugares ocupados" in resposta.json()["detail"]
    assert "sem ocupação" in resposta.json()["detail"]
    # NADA é apagado: a sala continua com o mapa que tinha.
    assert room.seats.count() == len(lugares)
    room.refresh_from_db()
    assert room.capacity == 60


@pytest.mark.django_db
def test_troca_com_ingresso_emitido_e_recusada(
    painel, room, make_movie, make_screening, make_seats, make_tickets, make_user
):
    """Ingresso implica reserva paga, e reserva paga bloqueia para sempre."""
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_tickets(sessao, make_user(), lugares[:1])

    resposta = painel.patch(
        f"{SALAS}{room.pk}/", data={"capacidade": 20}, content_type="application/json"
    )

    assert resposta.status_code == 409
    assert room.seats.count() == len(lugares)


@pytest.mark.django_db
def test_reserva_vencida_e_nao_paga_nao_bloqueia(
    painel, room, make_movie, make_screening, make_seats, make_reservation, make_user
):
    """Edge case da spec — o lugar não está ocupado, e a leitura é a mesma
    que o mapa de assentos usa.

    Se esta troca fosse recusada, o painel estaria usando uma definição de
    ocupação diferente da do resto do sistema (FR-021).
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:3], minutes_left=-5)

    resposta = painel.patch(
        f"{SALAS}{room.pk}/", data={"capacidade": 20}, content_type="application/json"
    )

    assert resposta.status_code == 200
    assert room.seats.count() == 20


@pytest.mark.django_db
def test_pode_trocar_capacidade_reflete_a_ocupacao(
    painel, room, make_movie, make_screening, make_seats, make_reservation, make_user
):
    """A dica de interface existe para desabilitar COM EXPLICAÇÃO.

    E é só dica: o `PATCH` acima revalida, e há teste provando que ele recusa.
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:1])

    linha = painel.get(SALAS).json()["results"][0]

    assert linha["ocupacao_viva"] == 1
    assert linha["pode_trocar_capacidade"] is False


@pytest.mark.django_db
def test_sala_inexistente_devolve_404(painel):
    resposta = painel.patch(
        f"{SALAS}99999/", data={"nome": "X"}, content_type="application/json"
    )

    assert resposta.status_code == 404


@pytest.mark.django_db
def test_a_lista_de_salas_nao_faz_uma_consulta_por_sala(
    painel, django_assert_max_num_queries
):
    from apps.screening.models import Room

    for indice in range(8):
        sala = Room.objects.create(name=f"Sala {indice}", capacity=20)
        salas.gerar_assentos(sala)

    with django_assert_max_num_queries(5):
        assert painel.get(SALAS).json()["count"] == 8


@pytest.mark.django_db
def test_sala_criada_pelo_painel_serve_ao_mapa_do_cliente(painel, client, make_movie):
    """US4 Independent Test — a sala nova atravessa até o fluxo de compra."""
    sala = painel.post(
        SALAS, data={"nome": "Sala 3", "capacidade": 45}, content_type="application/json"
    ).json()

    from datetime import timedelta

    from django.utils import timezone

    sessao = painel.post(
        "/api/v1/programacao/sessoes/",
        data={
            "filme": make_movie().pk,
            "sala": sala["id"],
            "inicio": (timezone.now() + timedelta(hours=8)).isoformat(),
            "preco": "30.00",
            "publicar": True,
        },
        content_type="application/json",
    ).json()

    mapa = client.get(f"/api/v1/sessoes/{sessao['id']}/mapa/").json()

    fileiras = mapa["fileiras"]
    assert [f["letra"] for f in fileiras] == ["A", "B", "C", "D", "E"]
    assert len(fileiras[-1]["assentos"]) == 5
    assert [a["tipo"] for a in fileiras[-1]["assentos"][-3:]] == ["acessibilidade"] * 3
