"""Consultas de leitura do catálogo.

Ficam fora das views para serem testáveis sem HTTP.
"""

from django.db.models import Case, IntegerField, Min, Prefetch, Q, Value, When
from django.utils import timezone

from apps.catalog.models import Movie, Trailer
from apps.screening.models import Screening

HIGHLIGHTS_LIMIT = 5

# --- Busca do cabeçalho ---
SEARCH_LIMIT_PADRAO = 6
SEARCH_LIMIT_MIN = 1
SEARCH_LIMIT_MAX = 20
SEARCH_TERMO_MAX_CHARS = 80


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


def normalizar_termo(bruto):
    """Termo pronto para consulta: sem espaços nas pontas, com teto de tamanho.

    O teto existe para que uma entrada absurda vire uma consulta inútil em vez
    de um erro — o campo já limita em 80, mas o servidor não confia nisso.
    """
    if not bruto:
        return ""
    return str(bruto).strip()[:SEARCH_TERMO_MAX_CHARS]


def normalizar_limite(bruto):
    """Limite fixado na faixa aceita.

    Valor inválido cai no padrão e valor fora da faixa é fixado no extremo
    mais próximo. Nunca levanta erro: limite malformado é problema de quem
    chama, não motivo para negar a busca a quem digitou.
    """
    try:
        limite = int(bruto)
    except (TypeError, ValueError):
        return SEARCH_LIMIT_PADRAO
    return max(SEARCH_LIMIT_MIN, min(limite, SEARCH_LIMIT_MAX))


def search_movies(termo, limite=SEARCH_LIMIT_PADRAO):
    """Filmes cujo título corresponde ao termo (FR-007, FR-008).

    Devolve `(filmes, truncado)`.

    Sem filtro por sessão, de propósito: a busca não esconde o que existe no
    catálogo (R6). É o oposto da regra do carrossel, que só destaca filme com
    sessão comprável — destaque é promessa de compra, busca é navegação.
    """
    termo = normalizar_termo(termo)
    if not termo:
        return [], False

    # Uma linha a mais que o pedido responde "existe mais?" sem um COUNT(*)
    # separado sobre a mesma condição.
    janela = limite + 1

    filmes = list(
        Movie.objects.filter(is_active=True)
        .filter(title__unaccent__icontains=termo)
        .annotate(
            # Quem digita "mat" espera "Matrix" antes de "Chamado da Mata".
            relevancia=Case(
                When(title__unaccent__istartswith=termo, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        # O desempate por título torna o resultado determinístico — sem ele o
        # teste dependeria da ordem física das linhas.
        .order_by("relevancia", "title")[:janela]
    )

    truncado = len(filmes) > limite
    return filmes[:limite], truncado


def get_movie_by_slug(slug):
    """Filme ativo com suas sessões compráveis, ou None."""
    now = timezone.now()
    sellable = _sellable_screenings(now).select_related("room")

    return (
        Movie.objects.filter(is_active=True, slug=slug)
        .prefetch_related("genres", Prefetch("screenings", queryset=sellable))
        .first()
    )
