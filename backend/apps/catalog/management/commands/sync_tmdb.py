"""Importa o catálogo de filmes do TMDb para o banco local.

Traz três listas — em cartaz, em alta da semana e estreias futuras — e marca
cada filme com o que ele é, para alimentar as trilhas da home.

Depois deste comando o TMDb pode ficar fora do ar sem afetar a navegação: é o
que sustenta o Princípio VII e o SC-004.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Movie
from apps.catalog.services.tmdb_client import TMDBClient, TMDBError
from apps.catalog.services.tmdb_sync import sync_movie


class Command(BaseCommand):
    help = "Importa filmes em cartaz, em alta e com estreia futura do TMDb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Máximo de filmes por lista (padrão: 20). Vale por lista, não no total.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        client = TMDBClient()

        listas = [
            ("em cartaz", client.now_playing, {}),
            ("em alta", client.trending, {"is_trending": True}),
            ("em breve", client.upcoming, {"is_upcoming": True}),
        ]

        # Cada filme é detalhado uma única vez, mesmo aparecendo em duas listas
        # — detalhar de novo gastaria o dobro de requisições sem ganho.
        # Guardamos as marcas acumuladas por filme antes de buscar o detalhe.
        marcas = {}
        ordem = []

        for rotulo, buscar, marca in listas:
            try:
                payload = buscar()
            except TMDBError as exc:
                raise CommandError(f"Falha ao buscar a lista '{rotulo}': {exc}") from exc

            entradas = (payload.get("results") or [])[:limit]
            self.stdout.write(f"{rotulo}: {len(entradas)} filme(s) na lista")

            for entrada in entradas:
                tmdb_id = entrada.get("id")
                if not tmdb_id:
                    continue
                if tmdb_id not in marcas:
                    marcas[tmdb_id] = {"is_trending": False, "is_upcoming": False}
                    ordem.append(tmdb_id)
                marcas[tmdb_id].update({k: True for k in marca})

        if not ordem:
            self.stdout.write(self.style.WARNING("O TMDb não retornou nenhum filme."))
            return

        # Zera a marca de "em alta" ANTES de remarcar. Sem isso, um filme que
        # entrou uma vez em alta ficaria em alta para sempre: nada o tiraria da
        # trilha. "Em alta" é estado do mundo, não atributo do filme (R3).
        Movie.objects.update(is_trending=False, is_upcoming=False)

        importados = 0
        falhas = 0

        for tmdb_id in ordem:
            try:
                detalhe = client.movie_detail(tmdb_id)
            except TMDBError as exc:
                # Um filme problemático não pode abortar a importação inteira.
                falhas += 1
                self.stderr.write(self.style.WARNING(f"  ! {tmdb_id}: {exc}"))
                continue

            filme = sync_movie(detalhe, **marcas[tmdb_id])
            importados += 1
            self.stdout.write(f"  · {filme.title}{self._etiquetas(filme)}")

        self.stdout.write(
            self.style.SUCCESS(f"\n{importados} filme(s) importado(s) do TMDb.")
        )
        if falhas:
            self.stdout.write(
                self.style.WARNING(f"{falhas} filme(s) não puderam ser importados.")
            )

    def _etiquetas(self, filme):
        etiquetas = []
        if filme.is_trending:
            etiquetas.append("em alta")
        if filme.is_upcoming:
            etiquetas.append("em breve")
        if filme.primary_trailer:
            etiquetas.append("trailer")
        return f"  [{', '.join(etiquetas)}]" if etiquetas else ""
