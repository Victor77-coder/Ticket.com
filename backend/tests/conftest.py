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
