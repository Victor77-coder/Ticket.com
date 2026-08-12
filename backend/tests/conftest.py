from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import Movie
from apps.screening.models import Room, Screening


@pytest.fixture
def room(db):
    return Room.objects.create(name="Sala 1", capacity=60)


@pytest.fixture
def make_movie(db):
    counter = {"n": 0}

    def _make(title="Filme de Teste", **kwargs):
        counter["n"] += 1
        defaults = {
            "tmdb_id": 1000 + counter["n"],
            "title": title,
            "synopsis": "Sinopse de teste.",
            "backdrop_path": "/backdrop.jpg",
            "poster_path": "/poster.jpg",
            "runtime_minutes": 120,
            "certification_br": "14",
        }
        defaults.update(kwargs)
        return Movie.objects.create(**defaults)

    return _make


@pytest.fixture
def make_screening(db, room):
    def _make(movie, hours_from_now=24, status=Screening.Status.PUBLISHED, room_obj=None):
        return Screening.objects.create(
            movie=movie,
            room=room_obj or room,
            starts_at=timezone.now() + timedelta(hours=hours_from_now),
            price=Decimal("30.00"),
            status=status,
        )

    return _make

# --- Assentos e reservas (feature 007) ------------------------------------


@pytest.fixture
def make_seats(db):
    """Gera o mapa de uma sala, com a mesma regra do seed.

    Fileiras de dez, letra por fileira, e os últimos lugares da última
    fileira marcados como acessibilidade.
    """

    def _make(room_obj, acessiveis=3):
        from apps.screening.models import Seat

        posicoes = [
            (chr(ord("A") + i // 10), i % 10 + 1) for i in range(room_obj.capacity)
        ]
        ultima = posicoes[-1][0]
        na_ultima = [p for p in posicoes if p[0] == ultima]
        marcados = set(na_ultima[-acessiveis:]) if acessiveis else set()

        return Seat.objects.bulk_create(
            [
                Seat(
                    room=room_obj,
                    row=letra,
                    number=numero,
                    kind=(
                        Seat.Kind.ACCESSIBLE
                        if (letra, numero) in marcados
                        else Seat.Kind.COMMON
                    ),
                )
                for letra, numero in posicoes
            ]
        )

    return _make


@pytest.fixture
def seats(room, make_seats):
    """O mapa da sala padrão das fixtures — 60 lugares, A a F."""
    return make_seats(room)


@pytest.fixture
def make_reservation(db):
    """Cria uma reserva ocupando lugares, sem passar pelo serviço.

    Serve para montar o estado de partida dos testes. O caminho de criação
    de verdade — com bloqueio e constraint — é exercitado pelos testes que
    chamam o serviço, nunca por esta fixture.
    """

    def _make(screening, customer, seats_list, minutes_left=10):
        from apps.screening.models import Reservation, ReservedSeat

        reserva = Reservation.objects.create(
            screening=screening,
            customer=customer,
            expires_at=timezone.now() + timedelta(minutes=minutes_left),
        )
        ReservedSeat.objects.bulk_create(
            [
                ReservedSeat(reservation=reserva, screening=screening, seat=s)
                for s in seats_list
            ]
        )
        return reserva

    return _make


# --- Pagamento e ingresso (feature 008) -----------------------------------


@pytest.fixture
def make_paid_reservation(make_reservation):
    """Uma reserva JÁ PAGA, montada sem passar pelo serviço de pagamento.

    Existe para que a prova de R3 — o lugar vendido não volta ao estoque —
    não dependa da fase seguinte estar pronta. O caminho de pagamento de
    verdade, com bloqueio e constraint, é exercitado pelos testes que chamam
    o serviço.

    `minutes_left` negativo é o cenário que interessa: uma reserva paga cujo
    prazo original JÁ PASSOU. É exatamente aí que a regra da 007, olhando só
    `expires_at`, trata um lugar vendido como abandonado.
    """

    def _make(screening, customer, seats_list, minutes_left=-1):
        from apps.screening.models import Reservation

        reserva = make_reservation(
            screening, customer, seats_list, minutes_left=minutes_left
        )
        reserva.status = Reservation.Status.PAID
        reserva.save(update_fields=["status"])
        return reserva

    return _make


@pytest.fixture
def make_user(db):
    """Usuário com papel, para os testes de autorização."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    counter = {"n": 0}

    def _make(role=None, username=None, password="segredo123"):
        counter["n"] += 1
        role = role or User.Role.CUSTOMER
        user = User.objects.create_user(
            username=username or f"user{counter['n']}",
            password=password,
            role=role,
        )
        return user

    return _make
