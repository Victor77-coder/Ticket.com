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
        """Filmes com arte, para que o carrossel não caia no fallback."""
        with_art = list(
            Movie.objects.filter(is_active=True)
            .exclude(backdrop_path="")
            .order_by("-release_date")[:MIN_HIGHLIGHTED_MOVIES]
        )
        if len(with_art) >= MIN_HIGHLIGHTED_MOVIES:
            return with_art

        # Catálogo pequeno: completa com o que houver, mesmo sem arte.
        extra = Movie.objects.filter(is_active=True).exclude(
            pk__in=[m.pk for m in with_art]
        )[: MIN_HIGHLIGHTED_MOVIES - len(with_art)]
        return with_art + list(extra)

    def _seed_screenings(self, movies, rooms):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
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
