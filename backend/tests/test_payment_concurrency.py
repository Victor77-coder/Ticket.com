"""A prova do Princípio II na feature 008.

O Princípio II diz que "pagamento aprovado DEVE emitir o ingresso; não existe
estado intermediário durável em que o assento esteja preso sem dono". Este
arquivo prova as duas metades disso sob concorrência real:

  - uma reserva nunca gera dois conjuntos de ingressos;
  - uma reserva paga nunca fica sem ingresso.

AS MESMAS DUAS ARMADILHAS da 007, e pelos mesmos motivos:

1. **Transação de teste.** `pytest-django` envolve cada teste numa transação e
   faz rollback ao fim. Duas threads nesse modo compartilham conexão e
   transação — não há corrida, não há bloqueio, e o teste passa até com as
   constraints removidas. Daí `django_db(transaction=True)` em tudo aqui.

2. **Conexão herdada.** `connection.close()` no início e no fim de cada thread
   força cada uma a abrir a sua.

A verificação de que este arquivo testa alguma coisa está em T071 e T072 do
tasks.md: remover cada uma das duas garantias e conferir que ele FALHA.
"""

import threading
import uuid
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.screening.models import Payment, Reservation, ReservedSeat, Ticket
from apps.screening.services import pagamentos

CARTAO_APROVADO = {
    "numero": "4242424242424242",
    "nome": "MARIA DE SOUZA",
    "validade": "12/2030",
    "cvv": "123",
}


def _pagar_em_thread(reserva_id, barreira, saida, indice):
    """Corpo de uma das threads da corrida.

    Abre conexão própria, espera a outra chegar à barreira, e só então tenta
    pagar. A barreira é o que transforma duas chamadas sequenciais numa
    corrida de verdade.
    """
    connection.close()
    try:
        reserva = Reservation.objects.select_related("screening", "customer").get(
            pk=reserva_id
        )

        barreira.wait(timeout=10)

        resultado = pagamentos.pagar(
            cliente=reserva.customer,
            reserva=reserva,
            cartao=pagamentos.Cartao(**CARTAO_APROVADO),
        )
        saida[indice] = ("ok", resultado.aprovado, len(resultado.ingressos))
    except pagamentos.ReservaJaPaga:
        # A derrota esperada, e vem de duas origens indistinguíveis para
        # quem chama: a revalidação sob bloqueio encontrou a reserva já paga,
        # ou a constraint estourou na inserção. As duas contam igual.
        saida[indice] = ("ja_paga", None, None)
    except Exception as erro:  # pragma: no cover - só aparece quando quebra
        saida[indice] = ("erro", f"{type(erro).__name__}: {erro}", None)
    finally:
        connection.close()


def _correr(reserva_a, reserva_b):
    barreira = threading.Barrier(2)
    saida = [None, None]

    threads = [
        threading.Thread(target=_pagar_em_thread, args=(r.pk, barreira, saida, i))
        for i, r in enumerate([reserva_a, reserva_b])
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    return saida


@pytest.fixture
def cenario(db, make_movie, make_screening, make_seats, room, make_user):
    """Sessão vendável com mapa, um cliente e uma reserva de três lugares.

    Criado fora das threads e commitado, porque com `transaction=True` cada
    thread enxerga só o que já está no banco.

    Três lugares, não um: é o que torna observável a diferença entre "um
    conjunto de ingressos" e "um ingresso".
    """
    make_seats(room)
    sessao = make_screening(make_movie("A Odisseia"))
    cliente = make_user(username="pagador1")
    lugares = list(sessao.room.seats.filter(kind="common")[:3])

    reserva = Reservation.objects.create(
        screening=sessao,
        customer=cliente,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    ReservedSeat.objects.bulk_create(
        [ReservedSeat(reservation=reserva, screening=sessao, seat=s) for s in lugares]
    )

    return {"sessao": sessao, "cliente": cliente, "reserva": reserva, "lugares": lugares}


# --- A corrida (SC-004, SC-005) --------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_dois_pagamentos_simultaneos_da_mesma_reserva_um_so_vence(cenario):
    reserva = cenario["reserva"]

    saida = _correr(reserva, reserva)

    vitorias = [r for r in saida if r and r[0] == "ok"]
    ja_pagas = [r for r in saida if r and r[0] == "ja_paga"]
    erros = [r for r in saida if r and r[0] == "erro"]

    assert not erros, f"a corrida estourou fora do caminho previsto: {erros}"
    assert len(vitorias) == 1, f"esperava exatamente uma aprovação, veio {saida}"
    assert len(ja_pagas) == 1, f"esperava exatamente uma recusa por já paga, veio {saida}"
    # A vencedora emitiu o conjunto INTEIRO, não um pedaço dele.
    assert vitorias[0][2] == 3


@pytest.mark.django_db(transaction=True)
def test_a_corrida_deixa_um_pagamento_aprovado_so(cenario):
    """A prova que não depende do retorno do serviço.

    Mesmo que a aplicação inteira estivesse errada, esta asserção teria de
    valer — é a constraint parcial que a sustenta, não o código acima dela.
    """
    reserva = cenario["reserva"]

    _correr(reserva, reserva)

    aprovados = Payment.objects.filter(
        reservation=reserva, status=Payment.Status.APPROVED
    ).count()

    assert aprovados == 1


@pytest.mark.django_db(transaction=True)
def test_a_corrida_deixa_um_conjunto_de_ingressos_so(cenario):
    """Um ingresso por assento, e nenhum assento com dois."""
    reserva = cenario["reserva"]

    _correr(reserva, reserva)

    ingressos = Ticket.objects.filter(reserved_seat__reservation=reserva)
    assert ingressos.count() == 3

    ocupacoes = list(ingressos.values_list("reserved_seat_id", flat=True))
    assert len(set(ocupacoes)) == len(ocupacoes), "duas linhas de ingresso no mesmo lugar"


@pytest.mark.django_db(transaction=True)
def test_nenhuma_reserva_paga_fica_sem_ingresso(cenario):
    """O estado que o Princípio II proíbe **pelo nome**.

    "Não existe estado intermediário durável em que o assento esteja preso
    sem dono" — uma reserva `paid` sem ingresso é literalmente isso, e é o
    que aconteceria se a aprovação e a emissão não estivessem na mesma
    transação.
    """
    reserva = cenario["reserva"]

    _correr(reserva, reserva)

    pagas_sem_ingresso = [
        r.pk
        for r in Reservation.objects.filter(status=Reservation.Status.PAID)
        if not Ticket.objects.filter(reserved_seat__reservation=r).exists()
    ]

    assert pagas_sem_ingresso == [], (
        f"reserva paga sem ingresso emitido: {pagas_sem_ingresso}"
    )


@pytest.mark.django_db(transaction=True)
def test_reservas_diferentes_nao_se_atrapalham(cenario, make_user):
    """A garantia não pode virar serialização da sessão inteira.

    Se o bloqueio fosse da sessão em vez da reserva, este teste falharia — e
    o anterior continuaria verde. É ele que impede "resolver" a concorrência
    transformando o cinema numa fila de um.
    """
    sessao = cenario["sessao"]
    outro = make_user(username="pagador2")
    outros_lugares = list(sessao.room.seats.filter(kind="common")[3:5])

    segunda = Reservation.objects.create(
        screening=sessao,
        customer=outro,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    ReservedSeat.objects.bulk_create(
        [
            ReservedSeat(reservation=segunda, screening=sessao, seat=s)
            for s in outros_lugares
        ]
    )

    saida = _correr(cenario["reserva"], segunda)

    assert [r[0] for r in saida] == ["ok", "ok"], saida
    assert Payment.objects.filter(status=Payment.Status.APPROVED).count() == 2
    assert Ticket.objects.count() == 5


# --- Guarda contra o teste que não testa -----------------------------------


@pytest.mark.django_db(transaction=True)
def test_as_duas_garantias_existem_no_banco_com_esta_forma():
    """Se qualquer uma sumir, os testes acima perdem o que provam.

    Não substitui T071 e T072 — remover cada garantia e ver a corrida falhar
    é a verificação de verdade. Este é o aviso barato: pega a remoção
    acidental sem precisar de duas migrações e uma rodada manual.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename IN ('screening_payment', 'screening_ticket')
            """
        )
        indices = {nome: definicao.lower() for nome, definicao in cursor.fetchall()}

    parcial = indices.get("um_pagamento_aprovado_por_reserva")
    assert parcial is not None, "a constraint do pagamento aprovado sumiu"
    assert "unique" in parcial
    # COM predicado, e aqui isso é possível porque `status = 'approved'` é
    # imutável — ao contrário do `now()` que a 007 não pôde usar (R1).
    assert "where" in parcial, f"o índice deixou de ser parcial: {parcial}"
    assert "approved" in parcial

    do_ingresso = [
        d
        for n, d in indices.items()
        if "reserved_seat" in d and "unique" in d and n != "um_pagamento_aprovado_por_reserva"
    ]
    assert do_ingresso, "a unicidade de Ticket.reserved_seat sumiu — virou ForeignKey?"
    # SEM predicado: absoluta, como a da 007.
    assert all(" where " not in d for d in do_ingresso), (
        f"a unicidade do ingresso ganhou predicado: {do_ingresso}"
    )


@pytest.mark.django_db(transaction=True)
def test_insercao_direta_de_segundo_aprovado_e_recusada_pelo_banco(cenario):
    """Sem passar pelo serviço, sem bloqueio, sem aplicação.

    É a diferença entre "a aplicação evita" e "o banco impede" — que é
    exatamente o que o Princípio II exige (FR-019).
    """
    from django.db import IntegrityError

    reserva = cenario["reserva"]
    comum = {
        "reservation": reserva,
        "status": Payment.Status.APPROVED,
        "amount": reserva.screening.price,
        "card_last4": "4242",
        "card_brand": "visa",
    }
    Payment.objects.create(**comum)

    with pytest.raises(IntegrityError):
        Payment.objects.create(**comum)


@pytest.mark.django_db(transaction=True)
def test_recusas_repetidas_nao_esbarram_na_constraint(cenario):
    """O outro lado do índice parcial.

    Uma `UNIQUE(reservation)` sem condição proibiria a segunda tentativa, que
    é o que a US2 promete ao cliente. Guardar todas as recusas (FR-012) só é
    possível porque o predicado existe.
    """
    reserva = cenario["reserva"]

    for _ in range(3):
        Payment.objects.create(
            reservation=reserva,
            status=Payment.Status.DECLINED,
            decline_reason=Payment.DeclineReason.INSUFFICIENT_FUNDS,
            amount=reserva.screening.price,
            card_last4="9995",
            card_brand="visa",
        )

    assert Payment.objects.filter(reservation=reserva).count() == 3


@pytest.mark.django_db(transaction=True)
def test_dois_ingressos_no_mesmo_assento_sao_recusados_pelo_banco(cenario):
    """A segunda garantia, testada diretamente contra o banco."""
    from django.db import IntegrityError

    reserva = cenario["reserva"]
    ocupacao = reserva.seats.first()
    pagamento = Payment.objects.create(
        reservation=reserva,
        status=Payment.Status.APPROVED,
        amount=reserva.screening.price,
        card_last4="4242",
        card_brand="visa",
    )

    Ticket.objects.create(reserved_seat=ocupacao, payment=pagamento)

    with pytest.raises(IntegrityError):
        Ticket.objects.create(
            reserved_seat=ocupacao, payment=pagamento, public_id=uuid.uuid4()
        )
