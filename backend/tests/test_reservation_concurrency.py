"""A prova do Princípio II.

Este arquivo é a razão de a feature 007 existir com o peso que tem. Se ele
passar por acidente, o sistema mais importante do projeto está sem prova.

DUAS ARMADILHAS, as duas fáceis de cair:

1. **Transação de teste.** O `pytest-django` por padrão envolve cada teste
   numa transação e faz rollback ao fim. Duas threads nesse modo compartilham
   a mesma conexão e a mesma transação — não há corrida, não há bloqueio
   entre elas, e o teste passa sem exercitar concorrência alguma. Passaria até
   com a constraint removida. Daí `django_db(transaction=True)` em tudo aqui.

2. **Conexão herdada.** Uma thread que usa a conexão da thread principal não
   tem transação própria. `connection.close()` no início e no fim de cada
   thread força cada uma a abrir a sua.

A verificação de que este arquivo testa alguma coisa está na T065 do
tasks.md: comentar a constraint e conferir que ele FALHA.
"""

import threading
import uuid
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.screening.models import Reservation, ReservedSeat
from apps.screening.services import reservas


def _reservar_em_thread(cliente_id, sessao_id, seat_ids, barreira, saida, indice):
    """Corpo de uma das threads da corrida.

    Abre conexão própria, espera a outra chegar à barreira, e só então tenta
    reservar. A barreira é o que transforma duas chamadas sequenciais numa
    corrida de verdade.
    """
    from django.contrib.auth import get_user_model

    from apps.screening.models import Screening

    connection.close()
    try:
        cliente = get_user_model().objects.get(pk=cliente_id)
        sessao = Screening.objects.get(pk=sessao_id)

        barreira.wait(timeout=10)

        reserva, _ = reservas.criar_reserva(
            cliente=cliente,
            sessao=sessao,
            seat_ids=seat_ids,
            chave=uuid.uuid4(),
        )
        saida[indice] = ("ok", reserva.pk)
    except reservas.AssentoIndisponivel as recusa:
        # As duas formas de derrota são aceitas: recusa pelo bloqueio e
        # recusa pela constraint. O que importa é que exatamente uma vença.
        saida[indice] = ("recusado", [f"{s.row}{s.number}" for s in recusa.assentos])
    except Exception as erro:  # pragma: no cover - só aparece quando quebra
        saida[indice] = ("erro", f"{type(erro).__name__}: {erro}")
    finally:
        connection.close()


def _correr(cliente_a, cliente_b, sessao, seat_ids):
    barreira = threading.Barrier(2)
    saida = [None, None]

    threads = [
        threading.Thread(
            target=_reservar_em_thread,
            args=(cliente.pk, sessao.pk, seat_ids, barreira, saida, i),
        )
        for i, cliente in enumerate([cliente_a, cliente_b])
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    return saida


@pytest.fixture
def cenario(db, make_movie, make_screening, make_seats, room, make_user):
    """Sessão vendável, mapa gerado e dois clientes.

    Criado fora das threads e commitado, porque com `transaction=True` cada
    thread enxerga só o que já está no banco.
    """
    make_seats(room)
    sessao = make_screening(make_movie("A Odisseia"))
    return {
        "sessao": sessao,
        "c1": make_user(username="corrida1"),
        "c2": make_user(username="corrida2"),
        "assento": sessao.room.seats.filter(kind="common").first(),
    }


# --- A corrida (SC-002, SC-003) --------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_duas_reservas_simultaneas_do_mesmo_lugar_uma_so_vence(cenario):
    assento = cenario["assento"]

    saida = _correr(cenario["c1"], cenario["c2"], cenario["sessao"], [assento.pk])

    vitorias = [r for r in saida if r and r[0] == "ok"]
    recusas = [r for r in saida if r and r[0] == "recusado"]
    erros = [r for r in saida if r and r[0] == "erro"]

    assert not erros, f"a corrida estourou fora do caminho previsto: {erros}"
    assert len(vitorias) == 1, f"esperava exatamente uma vitória, veio {saida}"
    assert len(recusas) == 1, f"esperava exatamente uma recusa, veio {saida}"


@pytest.mark.django_db(transaction=True)
def test_a_corrida_nao_deixa_duplicata_no_banco(cenario):
    """A prova que não depende do código de resposta.

    Mesmo que a aplicação inteira estivesse errada, esta asserção teria de
    valer — é a constraint que a sustenta, não o código acima dela.
    """
    assento = cenario["assento"]

    _correr(cenario["c1"], cenario["c2"], cenario["sessao"], [assento.pk])

    ocupacoes = ReservedSeat.objects.filter(
        screening=cenario["sessao"], seat=assento
    ).count()

    assert ocupacoes == 1


@pytest.mark.django_db(transaction=True)
def test_corrida_sobre_lugar_com_reserva_vencida(cenario, make_reservation):
    """O caminho do bloqueio, e não o da constraint.

    Com a linha vencida presente, `SELECT ... FOR UPDATE` tem o que travar, e
    a segunda transação espera em vez de bater na constraint. É o caminho que
    R2 descreve — e o que o teste anterior **não** exercita, porque assento
    virgem não tem linha para bloquear.
    """
    assento = cenario["assento"]
    make_reservation(cenario["sessao"], cenario["c1"], [assento], minutes_left=-5)

    saida = _correr(cenario["c1"], cenario["c2"], cenario["sessao"], [assento.pk])

    assert len([r for r in saida if r and r[0] == "ok"]) == 1
    assert (
        ReservedSeat.objects.filter(screening=cenario["sessao"], seat=assento).count()
        == 1
    )
    # A linha vencida foi reciclada, não acumulada.
    assert Reservation.objects.filter(screening=cenario["sessao"]).count() == 2


@pytest.mark.django_db(transaction=True)
def test_corrida_com_selecao_sobreposta_nao_reserva_pela_metade(cenario):
    """Duas seleções que compartilham um lugar.

    Quem perde não pode ficar com o lugar que sobrou: a reserva é por inteiro
    ou não é (FR-018, FR-019).
    """
    comuns = list(cenario["sessao"].room.seats.filter(kind="common")[:3])
    a, b, c = comuns

    barreira = threading.Barrier(2)
    saida = [None, None]
    threads = [
        threading.Thread(
            target=_reservar_em_thread,
            args=(cenario["c1"].pk, cenario["sessao"].pk, [a.pk, b.pk], barreira, saida, 0),
        ),
        threading.Thread(
            target=_reservar_em_thread,
            args=(cenario["c2"].pk, cenario["sessao"].pk, [b.pk, c.pk], barreira, saida, 1),
        ),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert len([r for r in saida if r and r[0] == "ok"]) == 1
    assert ReservedSeat.objects.filter(screening=cenario["sessao"]).count() == 2

    # O perdedor não ficou com o lugar que não estava em disputa.
    livres = {a.pk, c.pk} - set(
        ReservedSeat.objects.filter(screening=cenario["sessao"]).values_list(
            "seat_id", flat=True
        )
    )
    assert len(livres) == 1


@pytest.mark.django_db(transaction=True)
def test_lugares_diferentes_nao_se_atrapalham(cenario):
    """A garantia não pode virar serialização de tudo.

    Duas pessoas escolhendo lugares distintos da mesma sessão precisam
    conseguir as duas — se o bloqueio fosse da sessão inteira em vez das
    linhas envolvidas, uma esperaria a outra sem motivo.
    """
    a, b = list(cenario["sessao"].room.seats.filter(kind="common")[:2])

    barreira = threading.Barrier(2)
    saida = [None, None]
    threads = [
        threading.Thread(
            target=_reservar_em_thread,
            args=(cenario["c1"].pk, cenario["sessao"].pk, [a.pk], barreira, saida, 0),
        ),
        threading.Thread(
            target=_reservar_em_thread,
            args=(cenario["c2"].pk, cenario["sessao"].pk, [b.pk], barreira, saida, 1),
        ),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert [r[0] for r in saida] == ["ok", "ok"], saida
    assert ReservedSeat.objects.filter(screening=cenario["sessao"]).count() == 2


# --- Idempotência sob concorrência (FR-023) --------------------------------


@pytest.mark.django_db(transaction=True)
def test_mesma_chave_em_duas_threads_cria_uma_reserva_so(cenario):
    """O clique duplo que vira duas requisições simultâneas.

    Verificar "já existe reserva parecida?" antes de criar é justamente o
    padrão que a concorrência quebra: as duas verificam, nenhuma encontra,
    ambas criam. Quem resolve é a UNIQUE(chave).
    """
    assento = cenario["assento"]
    chave = uuid.uuid4()
    barreira = threading.Barrier(2)
    saida = [None, None]

    def tentar(indice):
        from apps.screening.models import Screening

        connection.close()
        try:
            cliente = type(cenario["c1"]).objects.get(pk=cenario["c1"].pk)
            sessao = Screening.objects.get(pk=cenario["sessao"].pk)
            barreira.wait(timeout=10)
            reserva, criada = reservas.criar_reserva(
                cliente=cliente, sessao=sessao, seat_ids=[assento.pk], chave=chave
            )
            saida[indice] = ("ok", reserva.pk, criada)
        except Exception as erro:
            saida[indice] = ("erro", f"{type(erro).__name__}: {erro}", None)
        finally:
            connection.close()

    threads = [threading.Thread(target=tentar, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert all(r and r[0] == "ok" for r in saida), saida
    assert saida[0][1] == saida[1][1], "as duas precisam apontar para a mesma reserva"
    assert Reservation.objects.filter(idempotency_key=chave).count() == 1
    assert ReservedSeat.objects.filter(screening=cenario["sessao"]).count() == 1


# --- Guarda contra o teste que não testa -----------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_constraint_existe_no_banco_com_este_nome():
    """Se a constraint sumir, os testes acima perdem o que provam.

    Não substitui a T065 — comentar a constraint e ver a corrida falhar é a
    verificação de verdade. Este teste é o aviso barato: pega a remoção
    acidental sem precisar de duas migrações e uma rodada manual.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexdef FROM pg_indexes
            WHERE tablename = 'screening_reservedseat'
              AND indexname = 'unico_assento_por_sessao'
            """
        )
        linha = cursor.fetchone()

    assert linha is not None, "a constraint unico_assento_por_sessao sumiu"

    definicao = linha[0].lower()
    assert "unique" in definicao
    assert "screening_id" in definicao and "seat_id" in definicao
    # Sem predicado: um índice parcial deixaria brechas por onde a duplicata
    # passa, e é impossível de qualquer forma sobre now() (R1).
    assert " where " not in definicao, f"a constraint ganhou predicado: {definicao}"


@pytest.mark.django_db(transaction=True)
def test_insercao_direta_de_duplicata_e_recusada_pelo_banco(cenario, make_reservation):
    """Sem passar pelo serviço, sem bloqueio, sem aplicação.

    É a diferença entre "a aplicação evita" e "o banco impede" — que é
    exatamente o que o Princípio II exige (FR-016).
    """
    from django.db import IntegrityError

    assento = cenario["assento"]
    make_reservation(cenario["sessao"], cenario["c1"], [assento])

    outra = Reservation.objects.create(
        screening=cenario["sessao"],
        customer=cenario["c2"],
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    with pytest.raises(IntegrityError):
        ReservedSeat.objects.create(
            reservation=outra, screening=cenario["sessao"], seat=assento
        )
