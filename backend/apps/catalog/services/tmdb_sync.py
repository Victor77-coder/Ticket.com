"""Mapeamento do payload do TMDb para os modelos locais.

Concentra toda a lógica frágil de terceiro: escolha da classificação
indicativa brasileira (R3) e do trailer a exibir (R4). É onde os testes de
`tests/test_tmdb_sync.py` batem.
"""

from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from apps.catalog.models import Genre, Movie, Trailer

# Tipos de lançamento do TMDb (confirmados na documentação da API).
RELEASE_TYPE_THEATRICAL = 3

# Ordem de preferência para escolher o trailer primário (R4). Cada item é um
# predicado aplicado à lista de vídeos; o primeiro que casar vence.
TRAILER_PREFERENCE = (
    lambda v: v["kind"] == Trailer.Kind.TRAILER and v["is_official"] and v["language"] == "pt",
    lambda v: v["kind"] == Trailer.Kind.TRAILER and v["is_official"] and v["language"] == "en",
    lambda v: v["kind"] == Trailer.Kind.TRAILER,
    lambda v: v["kind"] == Trailer.Kind.TEASER,
)

# O backdrop oficial do TMDb às vezes é demasiado escuro para o painel de
# destaques: o véu de contraste sobre uma still noturna apaga o filme. Os
# caminhos continuam sendo do TMDb — só escolhemos outra arte do mesmo filme.
ARTES_VITRINE = {
    1368337: {"backdrop_path": "/kGCOfQpITTI0rKzrVMRGOFteszf.jpg"},  # A Odisseia
}


def extract_certification_br(release_dates_payload):
    """Classificação indicativa brasileira, ou None.

    Prefere a entrada de exibição em cinema (type=3); se não houver, aceita a
    primeira entrada brasileira com certificação preenchida. Sem entrada BR o
    resultado é None e o painel simplesmente omite o selo — nunca exibe "N/A".
    """
    results = (release_dates_payload or {}).get("results") or []

    br = next((item for item in results if item.get("iso_3166_1") == "BR"), None)
    if not br:
        return None

    entries = [e for e in (br.get("release_dates") or []) if (e.get("certification") or "").strip()]
    if not entries:
        return None

    theatrical = next((e for e in entries if e.get("type") == RELEASE_TYPE_THEATRICAL), None)
    chosen = theatrical or entries[0]
    return chosen["certification"].strip()


def extract_videos(videos_payload):
    """Normaliza os vídeos do TMDb, mantendo apenas o que sabemos reproduzir.

    Só YouTube: o player embutido do painel não trata Vimeo, e um botão que
    abre um vídeo quebrado é pior do que botão nenhum.
    """
    results = (videos_payload or {}).get("results") or []
    videos = []

    for item in results:
        if item.get("site") != "YouTube" or not item.get("key"):
            continue

        raw_kind = (item.get("type") or "").lower()
        if raw_kind not in (Trailer.Kind.TRAILER, Trailer.Kind.TEASER):
            continue

        videos.append(
            {
                "external_key": item["key"],
                "name": item.get("name") or "",
                "language": item.get("iso_639_1") or "",
                "kind": raw_kind,
                "is_official": bool(item.get("official")),
                "published_at": _parse_datetime(item.get("published_at")),
            }
        )

    return videos


def pick_primary_video(videos):
    """Escolhe qual vídeo o botão 'Trailer' vai abrir, ou None."""
    for matches in TRAILER_PREFERENCE:
        for video in videos:
            if matches(video):
                return video
    return None


def sync_movie(detail_payload, *, is_trending=False, is_upcoming=False):
    """Cria ou atualiza um filme a partir do detalhe do TMDb.

    Idempotente por `tmdb_id`: rodar de novo atualiza, não duplica.

    `is_trending` e `is_upcoming` são a classificação de catálogo que alimenta
    as trilhas da home. O comando de sincronização zera `is_trending` em todos
    os filmes antes de chamar esta função — ver a explicação em `sync_tmdb`.
    """
    tmdb_id = detail_payload["id"]

    movie, _created = Movie.objects.get_or_create(
        tmdb_id=tmdb_id,
        defaults={"title": detail_payload.get("title") or f"Filme {tmdb_id}"},
    )

    movie.title = detail_payload.get("title") or movie.title
    movie.original_title = detail_payload.get("original_title") or ""
    movie.synopsis = detail_payload.get("overview") or ""
    movie.backdrop_path = detail_payload.get("backdrop_path") or ""
    movie.poster_path = detail_payload.get("poster_path") or ""
    arte = ARTES_VITRINE.get(tmdb_id)
    if arte:
        movie.backdrop_path = arte.get("backdrop_path") or movie.backdrop_path
        movie.poster_path = arte.get("poster_path") or movie.poster_path
    movie.runtime_minutes = detail_payload.get("runtime") or None
    movie.release_date = _parse_date(detail_payload.get("release_date"))
    movie.certification_br = extract_certification_br(detail_payload.get("release_dates"))
    movie.synced_at = timezone.now()

    # A marcação é aditiva dentro de uma mesma execução: um filme presente em
    # duas listas recebe as duas marcas, e a segunda passagem não apaga a
    # primeira (FR-005).
    movie.is_trending = movie.is_trending or is_trending
    movie.is_upcoming = movie.is_upcoming or is_upcoming
    movie.catalog_synced_at = timezone.now()

    movie.save()

    _sync_genres(movie, detail_payload.get("genres") or [])
    _sync_trailers(movie, extract_videos(detail_payload.get("videos")))

    return movie


def _sync_genres(movie, genres_payload):
    genres = []
    for item in genres_payload:
        if not item.get("id"):
            continue
        genre, _ = Genre.objects.update_or_create(
            tmdb_id=item["id"],
            defaults={"name": item.get("name") or ""},
        )
        genres.append(genre)
    movie.genres.set(genres)


def _sync_trailers(movie, videos):
    primary = pick_primary_video(videos)

    # Zera o primário antes de gravar: a constraint permite apenas um por filme.
    movie.trailers.update(is_primary=False)

    for video in videos:
        Trailer.objects.update_or_create(
            movie=movie,
            provider=Trailer.Provider.YOUTUBE,
            external_key=video["external_key"],
            defaults={
                "name": video["name"],
                "language": video["language"],
                "kind": video["kind"],
                "is_official": video["is_official"],
                "published_at": video["published_at"],
                "is_primary": primary is not None
                and video["external_key"] == primary["external_key"],
            },
        )

    # Vídeos que sumiram do TMDb não devem continuar apontando para nada.
    keys = [v["external_key"] for v in videos]
    movie.trailers.exclude(external_key__in=keys).delete()


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, TypeError):
        return None
    return timezone.make_aware(parsed, dt_timezone.utc)
