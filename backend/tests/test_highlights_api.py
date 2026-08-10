"""Contrato do endpoint público de highlights.

O teste de vazamento é o GATE DO PRINCÍPIO IV da constitution: a resposta é
pública e não pode carregar nenhum dado de gestão do organizador.
"""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.catalog.models import Trailer


@pytest.fixture(autouse=True)
def _limpa_cache():
    """A view guarda a resposta por 60s; testes não podem ver dado do vizinho."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_endpoint_e_publico(client):
    """Sem autenticação, sem cabeçalho, sem sessão: 200."""
    response = client.get(reverse("catalog:highlights"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_catalogo_vazio_responde_200_e_nao_404(client):
    """Ausência de destaque é estado legítimo, não erro."""
    response = client.get(reverse("catalog:highlights"))
    assert response.status_code == 200
    assert response.json() == {"count": 0, "results": []}


@pytest.mark.django_db
def test_resposta_segue_o_contrato(client, make_movie, make_screening):
    movie = make_movie("Duna: Parte Dois")
    make_screening(movie, hours_from_now=8)
    Trailer.objects.create(
        movie=movie,
        external_key="Way9Dexny3w",
        kind=Trailer.Kind.TRAILER,
        is_official=True,
        is_primary=True,
    )

    payload = client.get(reverse("catalog:highlights")).json()

    assert payload["count"] == 1
    item = payload["results"][0]
    assert set(item) == {
        "id",
        "slug",
        "title",
        "synopsis_short",
        "backdrop_url",
        "poster_url",
        "certification_br",
        "runtime_minutes",
        "genres",
        "trailer",
        "next_screening_at",
        "has_available_seats",
        "movie_path",
    }
    assert item["title"] == "Duna: Parte Dois"
    assert item["movie_path"] == f"/filmes/{movie.slug}"
    assert item["trailer"] == {"provider": "youtube", "external_key": "Way9Dexny3w"}
    assert item["has_available_seats"] is True
    assert item["backdrop_url"].startswith("https://image.tmdb.org/t/p/w1280")


@pytest.mark.django_db
def test_filme_sem_trailer_tem_campo_nulo(client, make_movie, make_screening):
    """Nulo é o que esconde o botão 'Trailer' no painel (FR-015)."""
    movie = make_movie("Sem Trailer")
    make_screening(movie)

    item = client.get(reverse("catalog:highlights")).json()["results"][0]
    assert item["trailer"] is None


@pytest.mark.django_db
def test_certificacao_ausente_vira_nulo(client, make_movie, make_screening):
    movie = make_movie("Sem Classificação", certification_br=None)
    make_screening(movie)

    item = client.get(reverse("catalog:highlights")).json()["results"][0]
    assert item["certification_br"] is None


@pytest.mark.django_db
def test_nao_vaza_dado_de_gestao(client, make_movie, make_screening):
    """GATE DO PRINCÍPIO IV.

    Varre a resposta inteira em busca de qualquer campo restrito ao
    organizador. Falha aqui significa violação da constitution, não um
    detalhe de contrato.
    """
    movie = make_movie("Qualquer Filme")
    make_screening(movie)

    raw = json.dumps(client.get(reverse("catalog:highlights")).json())

    proibidos = [
        "status",       # rascunho/publicada/cancelada é decisão do organizador
        "capacity",     # capacidade da sala é operação
        "seats_taken",  # contagem de vendidos é operação
        "cost",         # qualquer custo ou margem
        "username",     # identificação de usuário de qualquer papel
        "email",
        "password",
        "draft",
        "cancelled",
    ]
    vazados = [campo for campo in proibidos if campo in raw]
    assert not vazados, f"resposta pública vazou dado de gestão: {vazados}"


@pytest.mark.django_db
def test_ordena_e_limita_como_o_contrato_promete(client, make_movie, make_screening):
    for i in range(7):
        movie = make_movie(f"Filme {i}")
        make_screening(movie, hours_from_now=7 - i)

    payload = client.get(reverse("catalog:highlights")).json()

    assert payload["count"] == 5
    horarios = [item["next_screening_at"] for item in payload["results"]]
    assert horarios == sorted(horarios)


@pytest.mark.django_db
def test_responde_sem_chave_do_tmdb(client, settings, make_movie, make_screening):
    """Princípio VII / SC-006.

    O endpoint lê apenas o banco. Sem TMDB_API_KEY a resposta é idêntica —
    só a reprodução do trailer no navegador degrada.
    """
    settings.TMDB_API_KEY = ""
    movie = make_movie("Funciona Offline")
    make_screening(movie)

    payload = client.get(reverse("catalog:highlights")).json()

    assert payload["count"] == 1
    assert payload["results"][0]["title"] == "Funciona Offline"
