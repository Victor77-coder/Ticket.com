"""Consultas de leitura do catálogo.

Ficam fora das views para serem testáveis sem HTTP.
"""

from django.db.models import Case, IntegerField, Min, Prefetch, Q, Value, When
from django.utils import timezone

from apps.catalog.models import Movie, Trailer
from apps.screening.models import Screening

# Três desde a feature 005; eram cinco na entrega original da 001. O limite é
# só do carrossel — a trilha Em cartaz usa a mesma regra de elegibilidade sem
# teto, então não é afetada.
HIGHLIGHTS_LIMIT = 3

# Limite da trilha Em alta, definido pelo usuário no pedido da feature (FR-003).
TRENDING_LIMIT = 9

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


def get_sellable_movies(limit=None):
    """Filmes com ao menos uma sessão publicada e futura.

    Uma regra, dois consumidores: o carrossel pede 5, a trilha Em cartaz pede
    todos. Duplicar a regra criaria dois lugares para manter em sincronia, e a
    divergência apareceria como promessa quebrada na trilha (R5, SC-003).

    A ordem é pela sessão mais próxima; o desempate por título existe para que
    o resultado seja determinístico e o teste não fique instável.
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


def get_highlighted_movies(limit=HIGHLIGHTS_LIMIT):
    """Filmes em destaque no carrossel (FR-002 da feature 001).

    É `get_sellable_movies` com teto de 5. A regra de elegibilidade é a mesma
    que alimenta a trilha Em cartaz — é isso que garante que as duas
    superfícies façam a mesma promessa de compra.
    """
    return get_sellable_movies(limit=limit)


def get_trending_movies(limit=TRENDING_LIMIT):
    """Filmes em alta **com sessão planejada**, para a trilha da home.

    `is_trending` é zerado a cada sincronização e remarcado, então esta
    consulta reflete a última lista do catálogo externo — não um acúmulo
    histórico.

    Emenda de 2026-08-11 (FR-003a): estar em alta no catálogo externo não
    basta. Num site de ingressos, uma faixa chamada "Em alta" que leva a filme
    sem nada à venda é atrito sem contrapartida.

    A condição de sessão é **a mesma** de `get_sellable_movies`, não uma
    parecida: usar o predicado idêntico é o que impede as duas trilhas de
    divergirem — um filme não pode ser comprável para uma e não para a outra
    (R11).
    """
    now = timezone.now()

    return (
        Movie.objects.filter(is_active=True, is_trending=True)
        # `filter` sobre a relação inversa faz o join no banco, sem N+1 e sem
        # trazer o filme para o Python só para descobrir se tem sessão.
        .filter(
            screenings__status=Screening.Status.PUBLISHED,
            screenings__starts_at__gt=now,
        )
        # O join com sessões multiplica a linha por sessão; sem isto um filme
        # com três sessões ocuparia três das nove vagas.
        .distinct()
        .prefetch_related("genres")
        # O corte vem DEPOIS do filtro (FR-003b). Cortar antes devolveria menos
        # de 9 mesmo havendo elegíveis suficientes — e o erro seria silencioso,
        # porque a trilha continuaria parecendo correta.
        .order_by("-release_date", "title")[:limit]
    )


def get_upcoming_movies(limit=None):
    """Filmes com estreia futura, para a trilha da home (FR-004).

    Exige a marca **e** a data futura. Só a marca deixaria um filme já
    estreado preso na trilha até a próxima sincronização; só a data traria
    todo filme futuro do catálogo, inclusive os que o TMDb não considera
    lançamento próximo (R3).
    """
    return (
        Movie.objects.filter(
            is_active=True,
            is_upcoming=True,
            release_date__gt=timezone.localdate(),
        )
        .prefetch_related("genres")
        .order_by("release_date", "title")[:limit]
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
        .prefetch_related(
            "genres",
            Prefetch("screenings", queryset=sellable),
            Prefetch(
                "trailers",
                queryset=Trailer.objects.order_by("-is_primary", "-published_at", "pk"),
            ),
        )
        .first()
    )
