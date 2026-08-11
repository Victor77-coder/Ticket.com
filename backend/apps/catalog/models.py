"""Catálogo de filmes.

Os dados de apresentação são persistidos localmente no momento da
sincronização com o TMDb. O caminho de leitura da home nunca chama a API
externa — é o Princípio VII da constitution virando esquema de banco.
"""

from django.conf import settings
from django.db import models
from django.utils.text import Truncator, slugify


class Genre(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=80)

    class Meta:
        verbose_name = "gênero"
        verbose_name_plural = "gêneros"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    original_title = models.CharField(max_length=200, blank=True)
    synopsis = models.TextField(blank=True)

    # Guardamos o caminho relativo do TMDb ("/abc.jpg"), não a URL completa:
    # trocar o tamanho da imagem não deve exigir migração de dados.
    backdrop_path = models.CharField(max_length=200, blank=True)
    poster_path = models.CharField(max_length=200, blank=True)

    runtime_minutes = models.PositiveIntegerField(null=True, blank=True)
    certification_br = models.CharField(max_length=10, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)

    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)

    is_active = models.BooleanField(default=True, db_index=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    # --- Classificação de catálogo (trilhas da home) ---
    # Booleanos em vez de tabela de coleção: a cardinalidade é fixa em três
    # trilhas e nenhuma tem atributo próprio — sem ordem manual, sem curadoria,
    # sem janela de vigência. Ver R2 em 004-home-movie-rows/research.md.
    #
    # `is_trending` é zerado em todos os filmes no início de cada sincronização
    # e remarcado nos que voltarem: "em alta" é estado do mundo, não atributo
    # do filme. Sem isso quem entrou uma vez ficaria em alta para sempre.
    is_trending = models.BooleanField(default=False, db_index=True)
    # `is_upcoming` não basta sozinho — a consulta exige também
    # `release_date > hoje`, senão um filme já estreado fica preso na trilha
    # até a próxima sincronização.
    is_upcoming = models.BooleanField(default=False, db_index=True)
    catalog_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "filme"
        verbose_name_plural = "filmes"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # O slug é definido uma única vez. Um ajuste de título no TMDb não pode
        # quebrar uma URL que já circula.
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self):
        base = slugify(self.title)[:180] or f"filme-{self.tmdb_id}"
        candidate = base

        if Movie.objects.filter(slug=candidate).exists() and self.release_date:
            candidate = f"{base}-{self.release_date.year}"

        suffix = 2
        while Movie.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1

        return candidate

    @property
    def backdrop_url(self):
        if not self.backdrop_path:
            return None
        return f"{settings.TMDB_IMAGE_BASE_URL}/w1280{self.backdrop_path}"

    @property
    def poster_url(self):
        if not self.poster_path:
            return None
        return f"{settings.TMDB_IMAGE_BASE_URL}/w500{self.poster_path}"

    @property
    def synopsis_short(self):
        """Sinopse cortada na fronteira de palavra, para caber no painel."""
        return Truncator(self.synopsis).chars(180, truncate="…")

    @property
    def primary_trailer(self):
        return self.trailers.filter(is_primary=True).first()


class Trailer(models.Model):
    """Vídeo associado a um filme.

    Guardamos todos os candidatos retornados pelo TMDb e marcamos um como
    primário, para poder trocar o escolhido sem nova sincronização.
    """

    class Provider(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"

    class Kind(models.TextChoices):
        TRAILER = "trailer", "Trailer"
        TEASER = "teaser", "Teaser"

    movie = models.ForeignKey(Movie, related_name="trailers", on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.YOUTUBE)
    external_key = models.CharField(max_length=60)
    name = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=10, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.TRAILER)
    is_official = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "trailer"
        verbose_name_plural = "trailers"
        constraints = [
            models.UniqueConstraint(
                fields=["movie", "provider", "external_key"],
                name="unique_trailer_por_filme_e_provedor",
            ),
            models.UniqueConstraint(
                fields=["movie"],
                condition=models.Q(is_primary=True),
                name="unico_trailer_primario_por_filme",
            ),
        ]

    def __str__(self):
        return f"{self.movie.title} — {self.name or self.external_key}"
