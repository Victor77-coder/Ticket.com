"""Primeiro arranque em produção: catálogo TMDb + cenário de demonstração.

Idempotente. Rodar de novo depois que a grade existe não apaga nada — o
`seed_demo` já recusa sem `--force`, e este comando nem chega a chamá-lo.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Movie
from apps.screening.models import Screening


class Command(BaseCommand):
    help = "Sincroniza o TMDb e semeia a demonstração se a base ainda estiver vazia."

    def handle(self, *args, **options):
        if not Movie.objects.exists():
            self.stdout.write("Catálogo vazio — importando do TMDb.")
            call_command("sync_tmdb", limit=20)
        else:
            self.stdout.write("Catálogo já existe; sync ignorado.")

        if not Movie.objects.exists():
            raise CommandError(
                "O TMDb não deixou filme nenhum. Confira TMDB_API_KEY e tente de novo."
            )

        if not Screening.objects.exists():
            self.stdout.write("Sem grade — semeando o cenário de demonstração.")
            call_command("seed_demo")
        else:
            self.stdout.write("Grade já existe; seed ignorado.")
