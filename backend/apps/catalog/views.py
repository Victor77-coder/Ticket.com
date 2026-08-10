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

from apps.catalog import selectors
from apps.catalog.serializers import HighlightSerializer, MovieDetailSerializer

HIGHLIGHTS_CACHE_SECONDS = 60


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
