"""Semeia o cenário de demonstração exigido pelo desafio.

Cria 1 organizador, 2 clientes, 1 usuário de portaria, salas e sessões
publicadas, para que o fluxo possa ser percorrido sem montar nada do zero.

Idempotente: rodar de novo atualiza, não duplica.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Movie
from apps.screening.models import Room, Screening

User = get_user_model()

DEMO_PASSWORD = "desafio2026"

DEMO_USERS = [
    ("organizador", "organizador@cinema.test", User.Role.ORGANIZER, "Olívia", "Martins"),
    ("cliente1", "cliente1@cinema.test", User.Role.CUSTOMER, "Camila", "Souza"),
    ("cliente2", "cliente2@cinema.test", User.Role.CUSTOMER, "Caio", "Ribeiro"),
    ("portaria", "portaria@cinema.test", User.Role.GATE, "Paulo", "Andrade"),
]

DEMO_ROOMS = [("Sala 1", 60), ("Sala 2", 40)]

# Horários das sessões, em horas a partir de agora. Todas no futuro, para que
# os filmes sejam elegíveis ao destaque (FR-002).
SESSION_OFFSETS_HOURS = [4, 27, 51]

MIN_HIGHLIGHTED_MOVIES = 5

# Abaixo disso é curta, show ou especial — não é o que um cinema põe em cartaz.
MIN_RUNTIME_MINUTES = 60


class Command(BaseCommand):
    help = "Cria usuários, salas e sessões de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._seed_users()
        rooms = self._seed_rooms()
        movies = self._pick_movies()

        if not movies:
            self.stdout.write(
                self.style.ERROR(
                    "Nenhum filme no catálogo. Rode primeiro:\n"
                    "  python manage.py sync_tmdb --limit 20"
                )
            )
            return

        screenings = self._seed_screenings(movies, rooms)

        self._report(users, rooms, movies, screenings)

    def _seed_users(self):
        created = []
        for username, email, role, first_name, last_name in DEMO_USERS:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": role == User.Role.ORGANIZER,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
            created.append(user)
        return created

    def _seed_rooms(self):
        rooms = []
        for name, capacity in DEMO_ROOMS:
            room, _ = Room.objects.update_or_create(
                name=name, defaults={"capacity": capacity}
            )
            rooms.append(room)
        return rooms

    def _pick_movies(self):
        """Escolhe os filmes que vão para a vitrine.

        Com catálogo real, ordenar só por data de lançamento trouxe um show de
        banda e um curta de 9 minutos para o carrossel. A vitrine de um cinema
        precisa parecer um cinema — o avaliador vê a home antes de ler código
        (Princípio V).

        Critério, em ordem de preferência:
          1. longa-metragem com arte, já lançado — o que um cinema exibe hoje
          2. qualquer longa-metragem com arte
          3. o que houver, para o seed nunca falhar em catálogo pequeno
        """
        hoje = timezone.localdate()
        base = Movie.objects.filter(is_active=True).exclude(backdrop_path="")

        filtros = [
            base.filter(
                runtime_minutes__gte=MIN_RUNTIME_MINUTES,
                release_date__lte=hoje,
            ).order_by("-release_date"),
            base.filter(runtime_minutes__gte=MIN_RUNTIME_MINUTES).order_by("-release_date"),
            Movie.objects.filter(is_active=True).order_by("-release_date"),
        ]

        escolhidos = []
        vistos = set()

        for consulta in filtros:
            for filme in consulta:
                if filme.pk in vistos:
                    continue
                escolhidos.append(filme)
                vistos.add(filme.pk)
                if len(escolhidos) == MIN_HIGHLIGHTED_MOVIES:
                    return escolhidos

        return escolhidos

    def _seed_screenings(self, movies, rooms):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        # A grade é recriada do zero a cada execução. `update_or_create` por
        # (sala, horário) não basta: o horário é calculado a partir de agora,
        # então cada execução geraria uma grade nova e as antigas ficariam —
        # o comando se diz idempotente e acumularia sessões, inflando a trilha
        # Em cartaz com filmes de execuções anteriores.
        #
        # Apagar tudo é correto aqui porque não existe painel de organizador:
        # toda sessão no banco veio deste comando. Quando existir, isto precisa
        # passar a apagar apenas o que o seed criou.
        apagadas, _ = Screening.objects.all().delete()
        if apagadas:
            self.stdout.write(f"  grade anterior removida ({apagadas} sessão(ões))")

        screenings = []

        for index, movie in enumerate(movies):
            for offset_index, hours in enumerate(SESSION_OFFSETS_HOURS):
                room = rooms[(index + offset_index) % len(rooms)]
                # O deslocamento por filme evita colidir com a constraint
                # UNIQUE(room, starts_at).
                starts_at = now + timedelta(hours=hours, minutes=30 * index)

                screening, _ = Screening.objects.update_or_create(
                    room=room,
                    starts_at=starts_at,
                    defaults={
                        "movie": movie,
                        "price": Decimal("32.00") if offset_index == 0 else Decimal("26.00"),
                        "status": Screening.Status.PUBLISHED,
                    },
                )
                screenings.append(screening)

        return screenings

    def _report(self, users, rooms, movies, screenings):
        self.stdout.write(self.style.SUCCESS("\nCenário de demonstração pronto.\n"))
        self.stdout.write(
            f"  {len(movies)} filme(s) em destaque · {len(rooms)} sala(s) · "
            f"{len(screenings)} sessão(ões) publicada(s)\n"
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Credenciais (todas com a mesma senha):"))
        self.stdout.write(f"  senha: {DEMO_PASSWORD}\n")
        for user in users:
            self.stdout.write(f"  {user.get_role_display():<13} {user.username}")

        self.stdout.write(
            self.style.WARNING(
                "\nCopie estas credenciais para o README — o desafio exige que o "
                "avaliador percorra o fluxo sem montar nada."
            )
        )
