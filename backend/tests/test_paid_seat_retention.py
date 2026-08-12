"""A armadilha que a 007 deixou — o lugar vendido não volta ao estoque.

Este arquivo prova a correção de R3, e é o único da feature 008 que cobre uma
falha que **nenhuma constraint pega**.

A 007 decide ocupação por `expires_at > now()`. Uma reserva PAGA não mexe em
`expires_at`: dez minutos depois da compra ela vira, para essa regra,
indistinguível de uma reserva abandonada. Três consequências, em cascata:

  1. o mapa volta a mostrar o lugar VENDIDO como livre;
  2. `Screening.seats_taken` para de contar, e a sessão parece ter vaga;
  3. pior de todas: `_liberar_ou_recusar` APAGA a ocupação paga, sob bloqueio,
     e entrega o lugar a outro cliente — enquanto o primeiro tem um ingresso
     emitido com aquele assento impresso.

A terceira não dispara `unico_assento_por_sessao`: a linha antiga é apagada
ANTES de a nova entrar, e apagar antes de inserir é operação perfeitamente
legal para o banco. A garantia da 007 é verdadeira e não protege contra isto.

Por isso estes testes existem, e por isso foram escritos ANTES do conserto —
todos precisam falhar contra a regra de um termo só.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import Reservation, ReservedSeat

User = get_user_model()

SENHA = "desafio2026"


@pytest.fixture
def sessao(make_movie, make_screening, seats):
    return make_screening(make_movie("A Odisseia"))


@pytest.fixture
def comprador(db):
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
    return list(sessao.room.seats.order_by("row", "number")[:2])


@pytest.fixture
def reserva_paga_e_vencida(make_paid_reservation, sessao, comprador, lugares):
    """O cenário que interessa: PAGA, com o prazo original já no passado.

    É o instante a partir do qual a regra da 007, sozinha, erra.
    """
    return make_paid_reservation(sessao, comprador, lugares, minutes_left=-1)


def test_o_cenario_e_mesmo_o_que_engana_a_regra_antiga(reserva_paga_e_vencida):
    """Guarda do próprio cenário.

    Se esta asserção falhar, os testes abaixo podem passar por engano — não
    por a regra estar certa, mas por a reserva nem estar vencida no relógio.
    """
    assert reserva_paga_e_vencida.status == Reservation.Status.PAID
    assert reserva_paga_e_vencida.is_expired is True


@pytest.mark.django_db
def test_lugar_vendido_continua_tomado_no_mapa(client, sessao, reserva_paga_e_vencida, lugares):
    """R3, consequência 1 — FR-018."""
    resposta = client.get(reverse("screening:seat-map", args=[sessao.pk]))
    assert resposta.status_code == 200

    vendidos = {(s.row, s.number) for s in lugares}
    situacoes = {
        (fileira["letra"], assento["numero"]): assento["situacao"]
        for fileira in resposta.json()["fileiras"]
        for assento in fileira["assentos"]
    }

    for posicao in vendidos:
        assert situacoes[posicao] == "tomado", (
            f"o lugar {posicao} foi VENDIDO e voltou ao mapa como livre"
        )


@pytest.mark.django_db
def test_lugar_vendido_continua_contando_na_ocupacao(sessao, reserva_paga_e_vencida, lugares):
    """R3, consequência 2 — `seats_taken` não pode zerar depois da venda."""
    assert sessao.seats_taken == len(lugares)


@pytest.mark.django_db
def test_outro_cliente_nao_reserva_lugar_vendido(
    client, outro_cliente, sessao, reserva_paga_e_vencida, lugares
):
    """R3, consequência 3 — a recusa que impede a venda dupla (FR-018)."""
    client.force_login(outro_cliente)

    resposta = client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [lugares[0].pk],
            "chave_idempotencia": str(uuid.uuid4()),
        },
        content_type="application/json",
    )

    assert resposta.status_code == 409, (
        "um lugar já vendido foi reservado por outra pessoa — venda dupla"
    )


@pytest.mark.django_db
def test_a_ocupacao_paga_nao_e_apagada(
    client, outro_cliente, sessao, reserva_paga_e_vencida, lugares
):
    """O caminho que NENHUMA constraint pega.

    Apagar a linha antiga antes de inserir a nova não viola
    `unico_assento_por_sessao` — o banco aceita sem reclamar. A única prova
    possível é olhar se a linha continua lá depois da tentativa alheia.
    """
    antes = set(
        ReservedSeat.objects.filter(reservation=reserva_paga_e_vencida).values_list(
            "pk", flat=True
        )
    )
    assert antes, "cenário mal montado: a reserva paga não tem ocupação"

    client.force_login(outro_cliente)
    client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [lugares[0].pk],
            "chave_idempotencia": str(uuid.uuid4()),
        },
        content_type="application/json",
    )

    depois = set(
        ReservedSeat.objects.filter(reservation=reserva_paga_e_vencida).values_list(
            "pk", flat=True
        )
    )
    assert depois == antes, (
        "a ocupação de uma reserva PAGA foi apagada como se fosse linha morta"
    )


@pytest.mark.django_db
def test_reserva_abandonada_continua_liberando_o_lugar(
    client, outro_cliente, sessao, comprador, lugares, make_reservation
):
    """O outro lado da regra, e a razão de os dois termos serem necessários.

    A correção de R3 não pode transformar toda reserva vencida em permanente.
    Uma reserva NÃO paga cujo prazo passou continua devolvendo o lugar — que
    é o comportamento que a 007 entregou e que a 008 não pode quebrar.
    """
    abandonada = make_reservation(sessao, comprador, lugares, minutes_left=-1)
    assert abandonada.status == Reservation.Status.HELD

    client.force_login(outro_cliente)
    resposta = client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [lugares[0].pk],
            "chave_idempotencia": str(uuid.uuid4()),
        },
        content_type="application/json",
    )

    assert resposta.status_code == 201, (
        "reserva abandonada deixou de liberar o lugar — a 007 foi quebrada"
    )
    assert not ReservedSeat.objects.filter(
        reservation=abandonada, seat=lugares[0]
    ).exists()


@pytest.mark.django_db
def test_reserva_paga_dentro_do_prazo_tambem_bloqueia(
    client, outro_cliente, sessao, comprador, lugares, make_paid_reservation
):
    """Paga e ainda no prazo: os dois termos verdadeiros ao mesmo tempo."""
    make_paid_reservation(sessao, comprador, lugares, minutes_left=5)

    client.force_login(outro_cliente)
    resposta = client.post(
        reverse("screening:reservation-create"),
        data={
            "sessao": sessao.pk,
            "assentos": [lugares[0].pk],
            "chave_idempotencia": str(uuid.uuid4()),
        },
        content_type="application/json",
    )

    assert resposta.status_code == 409
