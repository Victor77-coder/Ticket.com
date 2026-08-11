"""Mapeamento TMDb → modelos locais.

Concentra a lógica frágil de terceiro: classificação indicativa brasileira
(R3) e escolha do trailer a exibir (R4).
"""

import pytest

from apps.catalog.models import Movie, Trailer
from apps.catalog.services.tmdb_sync import (
    extract_certification_br,
    extract_videos,
    pick_primary_video,
    sync_movie,
)

# --- Classificação indicativa (R3) ---------------------------------------


def test_certificacao_prefere_exibicao_em_cinema():
    payload = {
        "results": [
            {
                "iso_3166_1": "BR",
                "release_dates": [
                    {"certification": "16", "type": 4},  # Digital
                    {"certification": "14", "type": 3},  # Theatrical
                ],
            }
        ]
    }
    assert extract_certification_br(payload) == "14"


def test_certificacao_cai_para_primeira_entrada_preenchida():
    payload = {
        "results": [
            {
                "iso_3166_1": "BR",
                "release_dates": [{"certification": "12", "type": 4}],
            }
        ]
    }
    assert extract_certification_br(payload) == "12"


def test_certificacao_sem_entrada_brasileira_vira_none():
    payload = {
        "results": [
            {"iso_3166_1": "US", "release_dates": [{"certification": "PG-13", "type": 3}]}
        ]
    }
    assert extract_certification_br(payload) is None


def test_certificacao_vazia_vira_none():
    payload = {
        "results": [
            {"iso_3166_1": "BR", "release_dates": [{"certification": "  ", "type": 3}]}
        ]
    }
    assert extract_certification_br(payload) is None


def test_certificacao_com_payload_ausente_vira_none():
    assert extract_certification_br(None) is None
    assert extract_certification_br({}) is None


# --- Seleção de vídeo (R4) -----------------------------------------------


def _video(key, kind="Trailer", lang="en", official=True, site="YouTube"):
    return {
        "key": key,
        "type": kind,
        "iso_639_1": lang,
        "official": official,
        "site": site,
        "name": f"Vídeo {key}",
    }


def test_descarta_video_que_nao_e_do_youtube():
    videos = extract_videos({"results": [_video("abc", site="Vimeo")]})
    assert videos == []


def test_descarta_tipo_que_nao_e_trailer_nem_teaser():
    videos = extract_videos({"results": [_video("abc", kind="Featurette")]})
    assert videos == []


def test_prefere_trailer_oficial_em_portugues():
    videos = extract_videos(
        {
            "results": [
                _video("ingles", lang="en"),
                _video("portugues", lang="pt"),
            ]
        }
    )
    assert pick_primary_video(videos)["external_key"] == "portugues"


def test_prefere_oficial_sobre_nao_oficial():
    videos = extract_videos(
        {
            "results": [
                _video("nao-oficial", lang="pt", official=False),
                _video("oficial", lang="en", official=True),
            ]
        }
    )
    assert pick_primary_video(videos)["external_key"] == "oficial"


def test_cai_para_teaser_quando_nao_ha_trailer():
    videos = extract_videos({"results": [_video("teaser", kind="Teaser")]})
    assert pick_primary_video(videos)["external_key"] == "teaser"


def test_sem_video_reproduzivel_nao_ha_primario():
    assert pick_primary_video([]) is None


# --- Sincronização completa ----------------------------------------------


def _detail(tmdb_id=550, **overrides):
    payload = {
        "id": tmdb_id,
        "title": "Clube da Luta",
        "original_title": "Fight Club",
        "overview": "Um homem insone conhece um vendedor de sabonetes.",
        "backdrop_path": "/backdrop.jpg",
        "poster_path": "/poster.jpg",
        "runtime": 139,
        "release_date": "1999-10-15",
        "genres": [{"id": 18, "name": "Drama"}],
        "videos": {"results": [_video("trailer-key", lang="pt")]},
        "release_dates": {
            "results": [
                {"iso_3166_1": "BR", "release_dates": [{"certification": "16", "type": 3}]}
            ]
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_sincroniza_filme_completo():
    movie = sync_movie(_detail())

    assert movie.title == "Clube da Luta"
    assert movie.runtime_minutes == 139
    assert movie.certification_br == "16"
    assert movie.slug == "clube-da-luta"
    assert [g.name for g in movie.genres.all()] == ["Drama"]
    assert movie.primary_trailer.external_key == "trailer-key"


@pytest.mark.django_db
def test_segunda_execucao_nao_duplica():
    sync_movie(_detail())
    sync_movie(_detail())

    assert Movie.objects.count() == 1
    assert Trailer.objects.count() == 1


@pytest.mark.django_db
def test_slug_nao_muda_quando_titulo_muda_no_tmdb():
    """Uma URL que já circula não pode quebrar por ajuste de título."""
    movie = sync_movie(_detail())
    slug_original = movie.slug

    atualizado = sync_movie(_detail(title="Clube da Luta — Edição Especial"))

    assert atualizado.slug == slug_original
    assert atualizado.title == "Clube da Luta — Edição Especial"


@pytest.mark.django_db
def test_filme_sem_video_do_youtube_fica_sem_trailer():
    movie = sync_movie(_detail(videos={"results": [_video("v", site="Vimeo")]}))
    assert movie.primary_trailer is None


@pytest.mark.django_db
def test_troca_de_primario_respeita_a_constraint():
    """Só pode existir um trailer primário por filme."""
    sync_movie(_detail())
    movie = sync_movie(
        _detail(videos={"results": [_video("novo-primario", lang="pt")]})
    )

    assert movie.trailers.filter(is_primary=True).count() == 1
    assert movie.primary_trailer.external_key == "novo-primario"


@pytest.mark.django_db
def test_video_removido_do_tmdb_some_do_banco():
    sync_movie(_detail())
    sync_movie(_detail(videos={"results": []}))

    assert Trailer.objects.count() == 0


@pytest.mark.django_db
def test_campos_ausentes_no_payload_nao_quebram():
    movie = sync_movie({"id": 999, "title": "Mínimo"})

    assert movie.runtime_minutes is None
    assert movie.certification_br is None
    assert movie.release_date is None
    assert movie.backdrop_url is None


# --- Classificação de catálogo (feature 004) ------------------------------


@pytest.mark.django_db
def test_marca_em_alta_e_em_breve():
    filme = sync_movie(_detail(), is_trending=True, is_upcoming=True)

    assert filme.is_trending is True
    assert filme.is_upcoming is True
    assert filme.catalog_synced_at is not None


@pytest.mark.django_db
def test_marcacao_e_aditiva_dentro_da_mesma_execucao():
    """Um filme presente em duas listas recebe as duas marcas.

    A segunda passagem não pode apagar a marca da primeira (FR-005).
    """
    sync_movie(_detail(), is_trending=True)
    filme = sync_movie(_detail(), is_upcoming=True)

    assert filme.is_trending is True
    assert filme.is_upcoming is True


@pytest.mark.django_db
def test_sem_marcas_o_filme_nasce_fora_das_trilhas():
    filme = sync_movie(_detail())

    assert filme.is_trending is False
    assert filme.is_upcoming is False
