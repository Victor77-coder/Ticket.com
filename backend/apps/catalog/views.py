"""Views públicas do catálogo — somente leitura.

Estas rotas declaram `AllowAny` explicitamente. O padrão do projeto é
`IsAuthenticated` (ver REST_FRAMEWORK em config/settings/base.py): o acesso
público é uma decisão registrada aqui, não herança silenciosa.
"""

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.views_base import ProgramacaoViewBase
from apps.catalog import selectors
from apps.catalog.serializers import (
    FilmeDoPainelSerializer,
    HighlightSerializer,
    MovieCardSerializer,
    MovieDetailSerializer,
    SearchResultSerializer,
)

HIGHLIGHTS_CACHE_SECONDS = 60
HOME_CACHE_SECONDS = 60

# Ordem fixa das trilhas na home (FR-001). É do servidor: o cliente renderiza
# o que veio, na ordem em que veio.
TRILHAS = (
    ("em-cartaz", "Em cartaz", selectors.get_sellable_movies),
    ("em-alta", "Em alta", selectors.get_trending_movies),
    ("em-breve", "Em breve", selectors.get_upcoming_movies),
)


@method_decorator(cache_page(HIGHLIGHTS_CACHE_SECONDS), name="get")
class HighlightsView(APIView):
    """GET /api/v1/highlights/ — até 5 filmes em destaque.

    Lê exclusivamente o banco local. Nunca chama o TMDb: com a API externa
    fora do ar esta resposta permanece idêntica (Princípio VII, SC-006).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        movies = selectors.get_highlighted_movies()
        data = HighlightSerializer(movies, many=True).data
        return Response({"count": len(data), "results": data})


class SearchView(APIView):
    """GET /api/v1/busca/?q=<termo> — sugestões de filme para o cabeçalho.

    Lê exclusivamente o banco local, como o endpoint de highlights: com o
    TMDb fora do ar esta resposta permanece idêntica (Princípio VII, SC-009).

    Sem cache: o termo muda a cada tecla e uma resposta guardada por 60s
    serviria mais requisição obsoleta do que acerto.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        termo = selectors.normalizar_termo(request.query_params.get("q"))
        limite = selectors.normalizar_limite(
            request.query_params.get("limite", selectors.SEARCH_LIMIT_PADRAO)
        )

        filmes, truncado = selectors.search_movies(termo, limite)
        data = SearchResultSerializer(filmes, many=True).data

        return Response(
            {
                # Devolver o termo normalizado deixa o cliente confirmar a
                # qual busca a resposta pertence.
                "termo": termo,
                "count": len(data),
                "truncated": truncado,
                "results": data,
            }
        )


@method_decorator(cache_page(HOME_CACHE_SECONDS), name="get")
class HomeRowsView(APIView):
    """GET /api/v1/home/ — as três trilhas da home.

    Lê exclusivamente o banco local. Nunca chama o TMDb: com a API externa
    fora do ar esta resposta permanece idêntica (Princípio VII, SC-004).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        rows = []

        for key, title, selecionar in TRILHAS:
            filmes = MovieCardSerializer(selecionar(), many=True).data

            # Trilha vazia é omitida do array, não devolvida vazia (FR-006).
            # Deixar o cliente decidir colocaria a regra em dois lugares, e o
            # dia em que um deles esquecesse apareceria um título de seção com
            # nada embaixo.
            if not filmes:
                continue

            rows.append({"key": key, "title": title, "count": len(filmes), "movies": filmes})

        return Response({"rows": rows})


class MovieDetailView(APIView):
    """GET /api/v1/filmes/<slug>/ — destino do botão 'Ver ingressos'."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        movie = selectors.get_movie_by_slug(slug)
        if movie is None:
            return Response(
                {"detail": "Filme não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MovieDetailSerializer(movie).data)


# --- Painel do organizador (feature 013) ----------------------------------
#
# As três views abaixo herdam de `ProgramacaoViewBase` e vivem sob
# `/api/v1/programacao/`. As duas coisas juntas são o que faz FR-034 legível de
# fora — declarar a permissão à mão em cada uma dependeria de alguém lembrar.


class CatalogoDoPainelView(ProgramacaoViewBase):
    """GET /api/v1/programacao/filmes/ — o catálogo LOCAL, para programar.

    É o que mantém a promessa de FR-014: com o TMDb fora do ar, programar
    continua funcionando. Esta resposta não toca a API externa em nenhuma
    hipótese.
    """

    def get(self, request):
        dados = FilmeDoPainelSerializer(selectors.catalogo_do_painel(), many=True).data
        return Response({"count": len(dados), "results": dados})
