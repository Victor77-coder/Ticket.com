"""Consultas de leitura do catálogo.

Ficam fora das views para serem testáveis sem HTTP.
"""

from django.db.models import Min, Prefetch, Q
from django.utils import timezone

from apps.catalog.models import Movie, Trailer
from apps.screening.models import Screening

HIGHLIGHTS_LIMIT = 5


def _sellable_screenings(now):
    """Sessões que um cliente pode comprar agora."""
    return Screening.objects.filter(
        status=Screening.Status.PUBLISHED,
        starts_at__gt=now,
    )


def get_highlighted_movies(limit=HIGHLIGHTS_LIMIT):
    """Filmes em destaque no carrossel (FR-002).

    Elegível é o filme ativo com ao menos uma sessão publicada e futura.
    A ordem é pela sessão mais próxima; o desempate por título existe para
    que o resultado seja determinístico e o teste não fique instável.
    """
    now = timezone.now()
    sellable = _sellable_screenings(now)

    # O mesmo predicado usado no filtro precisa valer no annotate, senão uma
    # sessão passada ou em rascunho puxaria o filme para o topo da ordenação.
    only_sellable = Q(screenings__status=Screening.Status.PUBLISHED) & Q(
        screenings__starts_at__gt=now
    )

    return (
        Movie.objects.filter(is_active=True)
        .annotate(next_screening_at=Min("screenings__starts_at", filter=only_sellable))
        .filter(next_screening_at__isnull=False)
        .prefetch_related(
            "genres",
            Prefetch(
                "trailers",
                queryset=Trailer.objects.filter(is_primary=True),
                to_attr="primary_trailers",
            ),
            Prefetch("screenings", queryset=sellable.select_related("room")),
        )
        .order_by("next_screening_at", "title")[:limit]
    )


def get_movie_by_slug(slug):
    """Filme ativo com suas sessões compráveis, ou None."""
    now = timezone.now()
    sellable = _sellable_screenings(now).select_related("room")

    return (
        Movie.objects.filter(is_active=True, slug=slug)
        .prefetch_related("genres", Prefetch("screenings", queryset=sellable))
        .first()
    )
