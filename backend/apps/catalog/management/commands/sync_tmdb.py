"""Importa o catálogo de filmes do TMDb para o banco local.

Depois deste comando o TMDb pode ficar fora do ar sem afetar o carrossel —
é o que sustenta o Princípio VII e o SC-006.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.services.tmdb_client import TMDBClient, TMDBError
from apps.catalog.services.tmdb_sync import sync_movie


class Command(BaseCommand):
    help = "Importa filmes em cartaz do TMDb. Idempotente por tmdb_id."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade máxima de filmes a importar (padrão: 20).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        client = TMDBClient()

        try:
            listing = client.now_playing()
        except TMDBError as exc:
            raise CommandError(str(exc)) from exc

        entries = (listing.get("results") or [])[:limit]
        if not entries:
            self.stdout.write(
                self.style.WARNING("O TMDb não retornou nenhum filme em cartaz.")
            )
            return

        imported = 0
        failed = 0

        for entry in entries:
            tmdb_id = entry.get("id")
            if not tmdb_id:
                continue

            try:
                detail = client.movie_detail(tmdb_id)
            except TMDBError as exc:
                # Um filme problemático não pode abortar a importação inteira.
                failed += 1
                self.stderr.write(self.style.WARNING(f"  ! {tmdb_id}: {exc}"))
                continue

            movie = sync_movie(detail)
            imported += 1
            trailer = "com trailer" if movie.primary_trailer else "sem trailer"
            self.stdout.write(f"  · {movie.title} ({trailer})")

        self.stdout.write(
            self.style.SUCCESS(f"\n{imported} filme(s) importado(s) do TMDb.")
        )
        if failed:
            self.stdout.write(
                self.style.WARNING(f"{failed} filme(s) não puderam ser importados.")
            )
