"""Contrato aditivo de GET /api/v1/filmes/<slug>/ — campo `trailers`.

Não substitui o contrato de highlights da 001. O carrossel continua sem
`kind` nem `name` (012 / contracts/filme-detalhe.md).
"""

import json
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Trailer


@pytest.fixture(autouse=True)
def _limpa_cache():
    cache.clear()
    yield
    cache.clear()


def detalhe(client, slug):
    return client.get(reverse("catalog:movie-detail", args=[slug]))


@pytest.mark.django_db
def test_filme_com_trailers_lista_o_primario_primeiro(client, make_movie):
    movie = make_movie("Com Trailers")
    Trailer.objects.create(
        movie=movie,
        external_key="teaser-depois",
        kind=Trailer.Kind.TEASER,
        name="Teaser",
        is_primary=False,
        published_at=timezone.now(),
    )
    Trailer.objects.create(
        movie=movie,
        external_key="oficial-primeiro",
        kind=Trailer.Kind.TRAILER,
        name="Trailer oficial",
        is_primary=True,
        published_at=timezone.now() - timedelta(days=10),
    )

    corpo = detalhe(client, movie.slug).json()

    assert corpo["trailers"][0] == {
        "provider": "youtube",
        "external_key": "oficial-primeiro",
        "kind": "trailer",
        "name": "Trailer oficial",
    }
    assert corpo["trailers"][1]["external_key"] == "teaser-depois"
    assert len(corpo["trailers"]) == 2


@pytest.mark.django_db
def test_filme_sem_trailer_devolve_lista_vazia(client, make_movie):
    movie = make_movie("Sem Trailer")

    corpo = detalhe(client, movie.slug).json()

    assert "trailers" in corpo
    assert corpo["trailers"] == []
    assert corpo["trailers"] is not None


@pytest.mark.django_db
def test_highlights_nao_ganha_kind_nem_name(client, make_movie, make_screening):
    movie = make_movie("Destaque")
    make_screening(movie)
    Trailer.objects.create(
        movie=movie,
        external_key="Way9Dexny3w",
        kind=Trailer.Kind.TRAILER,
        name="Oficial",
        is_primary=True,
    )

    item = client.get(reverse("catalog:highlights")).json()["results"][0]
    trailer = item["trailer"]

    assert trailer == {"provider": "youtube", "external_key": "Way9Dexny3w"}
    assert "kind" not in trailer
    assert "name" not in trailer


@pytest.mark.django_db
def test_detalhe_nao_vaza_dado_de_gestao(client, make_movie, make_screening):
    movie = make_movie("Qualquer Filme")
    make_screening(movie)
    Trailer.objects.create(
        movie=movie,
        external_key="abc",
        kind=Trailer.Kind.TRAILER,
        is_primary=True,
    )

    raw = json.dumps(detalhe(client, movie.slug).json())

    proibidos = [
        "status",
        "capacity",
        "seats_taken",
        "cost",
        "username",
        "email",
        "password",
        "draft",
        "cancelled",
        "is_primary",
        "tmdb_id",
    ]
    vazados = [campo for campo in proibidos if campo in raw]
    assert not vazados, f"resposta pública vazou dado de gestão: {vazados}"


@pytest.mark.django_db
def test_detalhe_continua_publico(client, make_movie):
    movie = make_movie("Aberto")
    resposta = detalhe(client, movie.slug)
    assert resposta.status_code == 200
