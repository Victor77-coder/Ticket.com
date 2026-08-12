"""Serializers públicos do catálogo.

GATE DO PRINCÍPIO IV — estas respostas são públicas. Nenhum campo abaixo
pode expor dado de gestão do organizador: status de sessão, custo, margem,
capacidade da sala, contagem de assentos vendidos ou identificação de
usuário. `contracts/highlights-api.md` lista as proibições e
`tests/test_highlights_api.py` as verifica.
"""

from django.conf import settings
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


class SearchResultSerializer(serializers.Serializer):
    """Uma sugestão da busca do cabeçalho.

    Projeção deliberadamente pobre: só o necessário para reconhecer o filme e
    chegar até ele. Reaproveitar `MovieDetailSerializer` por conveniência
    arrastaria sessões para uma resposta pública de busca.
    """

    slug = serializers.CharField()
    title = serializers.CharField()
    poster_url = serializers.CharField(allow_null=True)
    year = serializers.SerializerMethodField()
    movie_path = serializers.SerializerMethodField()

    def get_year(self, movie):
        """Só o ano, para desambiguar títulos parecidos."""
        return movie.release_date.year if movie.release_date else None

    def get_movie_path(self, movie):
        return f"/filmes/{movie.slug}"


class ScreeningSerializer(serializers.Serializer):
    """Sessão comprável. Sem `status`, sem custo, sem capacidade."""

    id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    room_name = serializers.CharField(source="room.name")
    has_available_seats = serializers.BooleanField()


class MovieDetailTrailerSerializer(serializers.Serializer):
    """Trailer na página do filme.

    Distinto de `TrailerSerializer` de propósito: `kind` e `name` já existem
    no modelo, mas o carrossel **não** os recebe. Enriquecer o serializer da
    home vazaria o contrato da 001 (012 / R2).
    """

    provider = serializers.CharField()
    external_key = serializers.CharField()
    kind = serializers.CharField()
    name = serializers.CharField()


class MovieDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    synopsis = serializers.CharField()
    backdrop_url = serializers.CharField(allow_null=True)
    poster_url = serializers.CharField(allow_null=True)
    certification_br = serializers.CharField(allow_null=True)
    runtime_minutes = serializers.IntegerField(allow_null=True)
    # Alimenta "Estreia em DD/MM/AAAA" na página do filme sem sessão (FR-025).
    release_date = serializers.DateField(allow_null=True)
    genres = serializers.SerializerMethodField()
    screenings = serializers.SerializerMethodField()
    trailers = serializers.SerializerMethodField()

    def get_genres(self, movie):
        return [genre.name for genre in movie.genres.all()]

    def get_screenings(self, movie):
        return ScreeningSerializer(movie.screenings.all(), many=True).data

    def get_trailers(self, movie):
        """Lista, nunca nula. Primário primeiro; depois published_at, pk."""
        trailers = list(movie.trailers.all())
        trailers.sort(
            key=lambda trailer: (
                not trailer.is_primary,
                -(trailer.published_at.timestamp() if trailer.published_at else 0),
                trailer.pk,
            )
        )
        return MovieDetailTrailerSerializer(trailers, many=True).data


class MovieCardSerializer(serializers.Serializer):
    """Cartão de filme nas trilhas da home.

    Sem `backdrop_url`: o cartão é vertical, de cartaz — enviar a arte
    horizontal seria transferir dado que nenhuma tela usa.

    Sem `trailer`: não há reprodução na trilha.

    Sem `is_trending` / `is_upcoming` / `catalog_synced_at`: são mecânica
    interna de classificação. O cliente recebe a trilha pronta e não precisa
    saber por que o filme está nela (gate do Princípio IV).
    """

    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    poster_url = serializers.CharField(allow_null=True)
    certification_br = serializers.CharField(allow_null=True)
    runtime_minutes = serializers.IntegerField(allow_null=True)
    release_date = serializers.DateField(allow_null=True)
    movie_path = serializers.SerializerMethodField()

    def get_movie_path(self, movie):
        return f"/filmes/{movie.slug}"


# --- Painel do organizador (feature 013) ----------------------------------
#
# ⚠️ O AVISO DO TOPO CONTINUA VALENDO PARA TUDO ACIMA. Os serializers daqui para
# baixo servem a área de programação, e são os únicos deste arquivo autorizados
# a expor `tmdb_id` — que é a chave da importação e não tem uso nenhum numa
# resposta pública.
#
# A pressão de crescimento tem direção: campo de gestão nasce aqui embaixo,
# nunca migra para cima. `tests/test_highlights_api.py`, `test_home_rows_api.py`
# e `test_search_api.py` são a guarda do outro lado.


class FilmeDoPainelSerializer(serializers.Serializer):
    """Um filme do catálogo local, como o painel precisa dele.

    `sessoes` vem da anotação de `catalogo_do_painel` — nunca de
    `movie.screenings.count()`, que seria uma consulta por linha numa tela que
    lista o catálogo inteiro.
    """

    id = serializers.IntegerField()
    tmdb_id = serializers.IntegerField()
    titulo = serializers.CharField(source="title")
    ano = serializers.SerializerMethodField()
    poster_url = serializers.CharField(allow_null=True)
    duracao_min = serializers.IntegerField(source="runtime_minutes", allow_null=True)
    sessoes = serializers.IntegerField(default=0)

    def get_ano(self, movie):
        return movie.release_date.year if movie.release_date else None


class ResultadoTmdbSerializer(serializers.Serializer):
    """Um resultado da busca no TMDb, ainda não persistido.

    NÃO É UM `Movie`: vem do payload do TMDb, e por isso lê chaves de
    dicionário. Reaproveitar `FilmeDoPainelSerializer` obrigaria a inventar um
    `id` local para um filme que talvez nunca seja importado.

    `ja_no_catalogo` é resolvido por UMA consulta `__in` sobre a página inteira
    de resultados, e chega pelo contexto — uma consulta por linha aqui seria
    vinte consultas para uma busca.
    """

    tmdb_id = serializers.IntegerField(source="id")
    titulo = serializers.SerializerMethodField()
    ano = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()
    ja_no_catalogo = serializers.SerializerMethodField()

    def get_titulo(self, item):
        return item.get("title") or item.get("original_title") or ""

    def get_ano(self, item):
        data = item.get("release_date") or ""
        return int(data[:4]) if data[:4].isdigit() else None

    def get_poster_url(self, item):
        caminho = item.get("poster_path")
        return f"{settings.TMDB_IMAGE_BASE_URL}/w500{caminho}" if caminho else None

    def get_ja_no_catalogo(self, item):
        return item.get("id") in self.context.get("ja_no_catalogo", set())


class ImportacaoInputSerializer(serializers.Serializer):
    tmdb_id = serializers.IntegerField(
        error_messages={
            "required": "Escolha um filme da busca.",
            "invalid": "Escolha um filme da busca.",
        }
    )
