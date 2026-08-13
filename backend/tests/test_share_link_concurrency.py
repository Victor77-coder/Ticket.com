"""A prova de FR-029: no máximo UM link ativo por ingresso.

"Consultar se já existe link ativo e criar se não existir" é exatamente o
padrão que a concorrência quebra: duas requisições consultam, nenhuma
encontra, ambas criam. A 007 já registrou isso ao escolher uma chave de
idempotência em vez de "existe reserva parecida?".

A garantia é do BANCO — o índice parcial `um_link_ativo_por_ingresso` —, e não
de uma checagem prévia em Python. Quem perde a corrida NÃO recebe erro: recebe
o link do vencedor, que é literalmente a idempotência que FR-028 promete.

AS MESMAS DUAS ARMADILHAS da 007 e da 008, pelos mesmos motivos:

1. **Transação de teste.** `pytest-django` envolve cada teste numa transação.
   Duas threads nesse modo compartilham conexão — não há corrida, não há
   constraint sendo exercitada, e o teste passa até sem o índice. Daí
   `django_db(transaction=True)`.

2. **Conexão herdada.** `connection.close()` no início de cada thread força
   cada uma a abrir a sua.

A verificação de que este arquivo testa alguma coisa está em T079 do
tasks.md: remover o `condition` da constraint e conferir que ele FALHA.
"""

import threading
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.screening.models import (
    Payment,
    Reservation,
    ReservedSeat,
    Room,
    Screening,
    Seat,
    Ticket,
    TicketShareLink,
)
from apps.screening.services import compartilhamento

User = get_user_model()

QUANTAS_THREADS = 5


@pytest.fixture
def ingresso_isolado(django_db_setup, django_db_blocker):
    """Um ingresso emitido, criado FORA da transação de teste.

    Com `transaction=True` o banco é real e não há rollback automático, então
    o cenário é montado e desmontado à mão.
    """
    with django_db_blocker.unblock():
        sala = Room.objects.create(name="Sala corrida", capacity=1)
        assento = Seat.objects.create(room=sala, row="A", number=1)
        filme = _filme()
        sessao = Screening.objects.create(
            movie=filme,
            room=sala,
            starts_at=timezone.now() + timezone.timedelta(hours=24),
            price=Decimal("30.00"),
            status=Screening.Status.PUBLISHED,
        )
        cliente = User.objects.create_user(
            username="dono_corrida", password="x", role=User.Role.CUSTOMER
        )
        reserva = Reservation.objects.create(
            screening=sessao,
            customer=cliente,
            status=Reservation.Status.PAID,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        ocupacao = ReservedSeat.objects.create(
            reservation=reserva, screening=sessao, seat=assento, unit_price=sessao.price
        )
        pagamento = Payment.objects.create(
            reservation=reserva,
            status=Payment.Status.APPROVED,
            amount=Decimal("30.00"),
            card_last4="4242",
            card_brand="visa",
        )
        ingresso = Ticket.objects.create(reserved_seat=ocupacao, payment=pagamento)

    yield ingresso

    with django_db_blocker.unblock():
        TicketShareLink.objects.filter(ticket=ingresso).delete()
        Ticket.objects.filter(pk=ingresso.pk).delete()
        Payment.objects.filter(pk=pagamento.pk).delete()
        ReservedSeat.objects.filter(pk=ocupacao.pk).delete()
        Reservation.objects.filter(pk=reserva.pk).delete()
        Screening.objects.filter(pk=sessao.pk).delete()
        Seat.objects.filter(pk=assento.pk).delete()
        Room.objects.filter(pk=sala.pk).delete()
        filme.delete()
        cliente.delete()


def _filme():
    from apps.catalog.models import Movie

    return Movie.objects.create(
        tmdb_id=999001,
        title="Filme da corrida",
        synopsis="…",
        backdrop_path="/b.jpg",
        poster_path="/p.jpg",
        runtime_minutes=100,
        certification_br="14",
    )


def _gerar_em_thread(ingresso_id, barreira, saida, indice):
    """Abre conexão própria, espera as outras, e só então pede o link."""
    connection.close()
    try:
        ingresso = Ticket.objects.get(pk=ingresso_id)
        barreira.wait(timeout=10)
        link, criou = compartilhamento.gerar_link(ingresso)
        saida[indice] = {"token": link.token, "criou": criou, "erro": None}
    except Exception as erro:  # noqa: BLE001 — a thread não pode morrer calada
        saida[indice] = {"token": None, "criou": False, "erro": repr(erro)}
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_pedidos_simultaneos_produzem_um_unico_link_ativo(ingresso_isolado):
    """FR-029, SC-008 — a prova.

    Falha se o `condition` da constraint for removido (T079).
    """
    barreira = threading.Barrier(QUANTAS_THREADS)
    saida = [None] * QUANTAS_THREADS

    threads = [
        threading.Thread(
            target=_gerar_em_thread, args=(ingresso_isolado.pk, barreira, saida, i)
        )
        for i in range(QUANTAS_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    # Nenhuma thread pode ter estourado: a perdedora da corrida recebe o link
    # do vencedor, não uma exceção.
    assert [s["erro"] for s in saida] == [None] * QUANTAS_THREADS

    # UM link ativo no banco. É a asserção que o índice parcial sustenta.
    ativos = TicketShareLink.objects.filter(
        ticket=ingresso_isolado, revoked_at__isnull=True
    )
    assert ativos.count() == 1

    # E todas as chamadas devolveram o MESMO endereço.
    tokens = {s["token"] for s in saida}
    assert tokens == {ativos.first().token}

    # Exatamente uma criou; as demais foram idempotentes.
    assert sum(1 for s in saida if s["criou"]) == 1


@pytest.mark.django_db(transaction=True)
def test_nenhum_link_orfao_fica_para_tras(ingresso_isolado):
    """A corrida não pode deixar linha revogada nem lixo.

    A perdedora recebe `IntegrityError` na inserção. Se ela criasse a linha e
    a revogasse para "limpar", ficaria um token queimado a cada tentativa —
    e o histórico de revogados deixaria de significar "alguém revogou".
    """
    barreira = threading.Barrier(QUANTAS_THREADS)
    saida = [None] * QUANTAS_THREADS

    threads = [
        threading.Thread(
            target=_gerar_em_thread, args=(ingresso_isolado.pk, barreira, saida, i)
        )
        for i in range(QUANTAS_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert TicketShareLink.objects.filter(ticket=ingresso_isolado).count() == 1
