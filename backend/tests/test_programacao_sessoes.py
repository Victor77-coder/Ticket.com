"""A grade e o ciclo de vida da sessão — US1, US2 e US5.

O que este arquivo protege, em uma frase: a programação é a ÚNICA superfície
que enxerga a grade inteira, e mexer nela nunca toca no que já foi vendido.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.screening.models import Screening

GRADE = "/api/v1/programacao/sessoes/"


def _horario(horas):
    return (timezone.now() + timedelta(hours=horas)).isoformat()


# --- A grade (US1) --------------------------------------------------------


@pytest.mark.django_db
def test_grade_vazia_devolve_200_e_nao_404(painel):
    """FR-007 — "nada programado" é uma tela, não a ausência de um recurso."""
    resposta = painel.get(GRADE)

    assert resposta.status_code == 200
    assert resposta.json() == {"count": 0, "results": []}


@pytest.mark.django_db
def test_grade_lista_os_tres_estados(painel, make_movie, make_screening, make_seats, room):
    """FR-029 — a única superfície do sistema que expõe estado de sessão."""
    make_seats(room)
    filme = make_movie()
    for horas, situacao in (
        (10, Screening.Status.DRAFT),
        (20, Screening.Status.PUBLISHED),
        (30, Screening.Status.CANCELLED),
    ):
        make_screening(filme, hours_from_now=horas, status=situacao)

    corpo = painel.get(GRADE).json()

    assert corpo["count"] == 3
    estados = {linha["estado"] for linha in corpo["results"]}
    assert estados == {"draft", "published", "cancelled"}

    # Rótulo em português junto do valor fixo: a interface distingue por
    # rótulo + forma, e o valor é o que ela usa para escolher a forma.
    rotulos = {linha["estado"]: linha["estado_rotulo"] for linha in corpo["results"]}
    assert rotulos == {
        "draft": "Rascunho",
        "published": "Publicada",
        "cancelled": "Cancelada",
    }


@pytest.mark.django_db
def test_a_linha_da_grade_traz_filme_sala_ocupacao_e_venda(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """O contrato da linha, campo a campo (contracts/programacao-api.md)."""
    lugares = make_seats(room)
    sessao = make_screening(make_movie(title="A Odisseia"))
    make_reservation(sessao, make_user(), lugares[:2])

    linha = painel.get(GRADE).json()["results"][0]

    assert linha["filme"]["titulo"] == "A Odisseia"
    assert linha["sala"]["nome"] == room.name
    assert linha["sala"]["lugares"] == len(lugares)
    assert linha["ocupacao"] == 2
    assert linha["a_venda"] is True
    assert linha["pode_editar"] is False
    assert linha["pode_cancelar"] is True


@pytest.mark.django_db
def test_ocupacao_da_grade_nao_conta_reserva_vencida(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """A regra é `Reservation.OCUPANDO`, consumida — não uma segunda leitura.

    Reserva vencida e não paga NÃO ocupa: o lugar voltou ao estoque. Se esta
    contagem divergisse do mapa de assentos, o painel mostraria uma sessão
    cheia que o cliente vê vazia.
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:3], minutes_left=-5)

    assert painel.get(GRADE).json()["results"][0]["ocupacao"] == 0


@pytest.mark.django_db
def test_a_grade_nao_faz_uma_consulta_por_sessao(
    painel, make_movie, make_screening, make_seats, room, django_assert_max_num_queries
):
    """R6 — o N+1 que `seats_taken` por linha causaria.

    O teto é fixado em consultas, e não em tempo: doze sessões que passam e
    trinta que não passariam é o tipo de regressão que só aparece na revisão
    final, quando não dá mais tempo de consertar.
    """
    make_seats(room)
    filme = make_movie()
    for horas in range(1, 13):
        make_screening(filme, hours_from_now=horas)

    # Sessão do Django, usuário, e a consulta da grade. Uma folga pequena
    # absorve o que a autenticação faz, e nunca uma consulta por linha.
    with django_assert_max_num_queries(6):
        assert painel.get(GRADE).json()["count"] == 12


@pytest.mark.django_db
def test_a_grade_nao_expoe_o_comprador(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """Gestão de grade não é lista de clientes.

    A ocupação é NÚMERO. Quem reservou é dado de outra tela, e o painel não
    tem motivo para conhecê-lo — expor aqui seria crescer por acúmulo.
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    cliente = make_user(username="fulano")
    make_reservation(sessao, cliente, lugares[:1])

    assert "fulano" not in painel.get(GRADE).content.decode()
