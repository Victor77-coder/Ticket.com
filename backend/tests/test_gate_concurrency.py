"""A prova do Princípio III: uma validação por ingresso.

ESTE É O ÚNICO TESTE DA SÉRIE QUE NÃO TEM UMA CONSTRAINT ATRÁS DELE, e a
diferença muda o que ele significa.

Nas features 007, 008 e 009 a garantia de unicidade era um índice. Se alguém
escrevesse o código errado, o BANCO recusava a segunda escrita e o teste via a
recusa — o teste confirmava uma garantia que existia sem ele.

Aqui não há índice. O invariante é de transição — "esta coluna só sai de nulo
uma vez" —, e nenhum índice o expressa. A garantia é a FORMA DA ESCRITA:

    UPDATE ... SET used_at = now() WHERE id = %s AND used_at IS NULL

Se essa forma for trocada pelo código que qualquer pessoa escreve primeiro —

    if ingresso.used_at is not None: return JA_UTILIZADO
    ingresso.used_at = timezone.now(); ingresso.save()

— o banco aceita as duas escritas em silêncio, e duas pessoas entram com o
mesmo ingresso. Nada mais no sistema pega isso. ESTE ARQUIVO É A ÚNICA
DEFESA.

AS MESMAS DUAS ARMADILHAS de 007, 008 e 009, e aqui elas são fatais:

1. **Transação de teste.** `pytest-django` envolve cada teste numa transação.
   Duas threads nesse modo compartilham conexão — não há corrida, não há
   bloqueio de linha, e o teste passa COM O CÓDIGO ERRADO. Daí
   `django_db(transaction=True)`.

2. **Conexão herdada.** `connection.close()` no início de cada thread força
   cada uma a abrir a sua.

A verificação de que este arquivo testa alguma coisa está em T070 do
tasks.md: trocar a escrita condicional pelo `if` e conferir que ele FALHA.
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
)
from apps.screening.services import ingressos as ingressos_service
from apps.screening.services import portaria

User = get_user_model()

QUANTAS_THREADS = 5


@pytest.fixture
def cenario_isolado(django_db_setup, django_db_blocker):
    """Um ingresso emitido, criado FORA da transação de teste.

    Com `transaction=True` o banco é real e não há rollback automático, então
    o cenário é montado e desmontado à mão.
    """
    from apps.catalog.models import Movie

    with django_db_blocker.unblock():
        filme = Movie.objects.create(
            tmdb_id=999010,
            title="Filme da portaria",
            synopsis="…",
            backdrop_path="/b.jpg",
            poster_path="/p.jpg",
            runtime_minutes=100,
            certification_br="14",
        )
        sala = Room.objects.create(name="Sala da corrida da portaria", capacity=1)
        assento = Seat.objects.create(room=sala, row="A", number=1)
        sessao = Screening.objects.create(
            movie=filme,
            room=sala,
            starts_at=timezone.now() + timezone.timedelta(hours=2),
            price=Decimal("30.00"),
            status=Screening.Status.PUBLISHED,
        )
        cliente = User.objects.create_user(
            username="dono_da_portaria", password="x", role=User.Role.CUSTOMER
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
        codigo = ingressos_service.assinar_codigo(ingresso.public_id, sessao.pk)

    yield {"ingresso": ingresso, "codigo": codigo, "sessao": sessao.pk}

    with django_db_blocker.unblock():
        Ticket.objects.filter(pk=ingresso.pk).delete()
        Payment.objects.filter(pk=pagamento.pk).delete()
        ReservedSeat.objects.filter(pk=ocupacao.pk).delete()
        Reservation.objects.filter(pk=reserva.pk).delete()
        Screening.objects.filter(pk=sessao.pk).delete()
        Seat.objects.filter(pk=assento.pk).delete()
        Room.objects.filter(pk=sala.pk).delete()
        cliente.delete()
        filme.delete()


def _validar_em_thread(codigo, sessao_id, barreira, saida, indice):
    """Abre conexão própria, espera as outras, e só então valida."""
    connection.close()
    try:
        barreira.wait(timeout=10)
        resultado = portaria.validar(codigo=codigo, sessao_id=sessao_id)
        saida[indice] = {"situacao": resultado.situacao, "erro": None}
    except Exception as erro:  # noqa: BLE001 — a thread não pode morrer calada
        saida[indice] = {"situacao": None, "erro": repr(erro)}
    finally:
        connection.close()


def _correr(cenario):
    barreira = threading.Barrier(QUANTAS_THREADS)
    saida = [None] * QUANTAS_THREADS

    threads = [
        threading.Thread(
            target=_validar_em_thread,
            args=(cenario["codigo"], cenario["sessao"], barreira, saida, i),
        )
        for i in range(QUANTAS_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    return saida


@pytest.mark.django_db(transaction=True)
def test_validacoes_simultaneas_produzem_um_unico_valido(cenario_isolado):
    """FR-036, SC-007 — a prova.

    Falha se a escrita condicional virar leitura seguida de escrita (T070).
    """
    saida = _correr(cenario_isolado)

    assert [s["erro"] for s in saida] == [None] * QUANTAS_THREADS

    situacoes = [s["situacao"] for s in saida]
    assert situacoes.count("valido") == 1
    assert situacoes.count("ja_utilizado") == QUANTAS_THREADS - 1


@pytest.mark.django_db(transaction=True)
def test_o_instante_gravado_e_de_uma_validacao_so(cenario_isolado):
    """O vencedor grava; os perdedores não sobrescrevem.

    Sem esta asserção, uma implementação que gravasse em todas as threads mas
    respondesse "já utilizado" para as últimas passaria no teste acima — o
    desfecho estaria certo e o dado, corrompido.
    """
    _correr(cenario_isolado)

    ingresso = Ticket.objects.get(pk=cenario_isolado["ingresso"].pk)
    primeiro = ingresso.used_at
    assert primeiro is not None

    # Uma sexta validação, agora sequencial: nada pode mudar.
    resultado = portaria.validar(
        codigo=cenario_isolado["codigo"], sessao_id=cenario_isolado["sessao"]
    )

    assert resultado.situacao == "ja_utilizado"
    ingresso.refresh_from_db()
    assert ingresso.used_at == primeiro
