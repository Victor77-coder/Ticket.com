"""Serializers públicos do catálogo.

GATE DO PRINCÍPIO IV — estas respostas são públicas. Nenhum campo abaixo
pode expor dado de gestão do organizador: status de sessão, custo, margem,
capacidade da sala, contagem de assentos vendidos ou identificação de
usuário. `contracts/highlights-api.md` lista as proibições e
`tests/test_highlights_api.py` as verifica.
"""

from rest_framework import serializers


class TrailerSerializer(serializers.Serializer):
    provider = serializers.CharField()
    external_key = serializers.CharField()


class HighlightSerializer(serializers.Serializer):
    """Um painel do carrossel."""

    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    synopsis_short = serializers.CharField()
    backdrop_url = serializers.CharField(allow_null=True)
    poster_url = serializers.CharField(allow_null=True)
    certification_br = serializers.CharField(allow_null=True)
    runtime_minutes = serializers.IntegerField(allow_null=True)
    genres = serializers.SerializerMethodField()
    trailer = serializers.SerializerMethodField()
    next_screening_at = serializers.DateTimeField()
    has_available_seats = serializers.SerializerMethodField()
    movie_path = serializers.SerializerMethodField()

    def get_genres(self, movie):
        return [genre.name for genre in movie.genres.all()]

    def get_trailer(self, movie):
        """Nulo esconde o botão 'Trailer' no painel (FR-015)."""
        trailers = getattr(movie, "primary_trailers", None)
        trailer = trailers[0] if trailers else movie.primary_trailer
        if not trailer:
            return None
        return TrailerSerializer(trailer).data

    def get_has_available_seats(self, movie):
        """Booleano, nunca contagem.

        O carrossel só precisa saber se ainda dá para comprar; expor o número
        aberto seria vazar operação (ver os campos proibidos no contrato).
        """
        return any(screening.has_available_seats for screening in movie.screenings.all())

    def get_movie_path(self, movie):
        return f"/filmes/{movie.slug}"


class ScreeningSerializer(serializers.Serializer):
    """Sessão comprável. Sem `status`, sem custo, sem capacidade."""

    id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    room_name = serializers.CharField(source="room.name")
    has_available_seats = serializers.BooleanField()


class MovieDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    synopsis = serializers.CharField()
    backdrop_url = serializers.CharField(allow_null=True)
    poster_url = serializers.CharField(allow_null=True)
    certification_br = serializers.CharField(allow_null=True)
    runtime_minutes = serializers.IntegerField(allow_null=True)
    genres = serializers.SerializerMethodField()
    screenings = serializers.SerializerMethodField()

    def get_genres(self, movie):
        return [genre.name for genre in movie.genres.all()]

    def get_screenings(self, movie):
        return ScreeningSerializer(movie.screenings.all(), many=True).data
