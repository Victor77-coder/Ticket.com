"""Semeia o cenário de demonstração exigido pelo desafio.

Cria 1 organizador, 2 clientes, 1 usuário de portaria, salas e sessões
publicadas, para que o fluxo possa ser percorrido sem montar nada do zero.

Idempotente: rodar de novo atualiza, não duplica.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Movie
from apps.catalog.selectors import HIGHLIGHTS_LIMIT
from apps.screening.models import Reservation, Room, Screening, Seat

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

# Quantos filmes a demonstração coloca à venda. Doze faz a trilha Em cartaz ter
# substância, afasta a trilha Em alta de ser quase idêntica a ela, e faz o
# carrossel de três parecer um recorte em vez da lista inteira (R4).
FILMES_A_VENDA = 12

# Abaixo disso é curta, show ou especial — não é o que um cinema põe em cartaz.
MIN_RUNTIME_MINUTES = 60

# --- Curadoria da vitrine -------------------------------------------------
#
# ⚠️ A ORDEM DESTA LISTA DEFINE O CARROSSEL.
#
# `_seed_screenings` agenda a sessão como `agora + offset + 30min × índice`, e
# o carrossel exibe os filmes com sessão mais próxima. Quem está primeiro aqui
# aparece no destaque.
#
# Ou seja: reordenar esta lista — alfabeticamente, por exemplo — muda a vitrine
# sem que nada quebre. É por isso que existe teste fixando a ordem
# (`test_o_carrossel_traz_os_tres_destaques_na_ordem`).
#
# Toda a curadoria vive aqui, no cenário de demonstração. O carrossel continua
# sem saber que ela existe: aplica a regra de sempre, "os N com sessão mais
# próxima" (R1).
DESTAQUES = ["a odisseia", "homem aranha", "minions"]

# À venda, mas fora do carrossel por vir depois dos destaques.
TAMBEM_A_VENDA = ["moana"]


class Command(BaseCommand):
    help = "Cria usuários, salas e sessões de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._seed_users()
        rooms = self._seed_rooms()

        # Antes de qualquer coisa que dependa da grade: limpar reservas e
        # sessões. Precisa vir cedo porque os assentos são refeitos abaixo, e
        # ReservedSeat.seat é PROTECT — com ocupação viva, refazer o mapa da
        # sala falharia.
        self._reset_demo_state()

        seats = self._seed_seats(rooms)
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

        self._report(users, rooms, seats, movies, screenings)

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

    def _reset_demo_state(self):
        """Apaga reservas e sessões antes de recriar a demonstração.

        A grade é recriada do zero a cada execução — `update_or_create` por
        (sala, horário) não basta, porque o horário é calculado a partir de
        agora e cada execução geraria uma grade nova, acumulando as antigas.

        As reservas vão junto, e não por descuido: elas apontam para sessões
        com PROTECT, então sobreviver à grade seria impossível de qualquer
        forma. Mais importante, uma reserva de uma sessão que deixou de
        existir não significa nada — o seed reconstrói o cenário inteiro.

        Apagar tudo é correto porque não existe painel de organizador: toda
        sessão e toda reserva no banco vieram deste comando ou do fluxo de
        demonstração. Quando o painel existir, isto precisa passar a apagar
        apenas o que o seed criou.
        """
        reservas, _ = Reservation.objects.all().delete()
        if reservas:
            self.stdout.write(f"  reservas anteriores removidas ({reservas} linha(s))")

        apagadas, _ = Screening.objects.all().delete()
        if apagadas:
            self.stdout.write(f"  grade anterior removida ({apagadas} sessão(ões))")

    def _seed_seats(self, rooms):
        """Gera o mapa físico de cada sala a partir da capacidade.

        Fileiras de SEATS_PER_ROW lugares, identificadas por letra. Capacidade
        que não fecha a fileira deixa a última incompleta — sem inventar
        lugares que a sala não tem.

        Os lugares de acessibilidade ficam na última fileira, que é a
        convenção de sala real: é onde há espaço para cadeira de rodas sem
        obstruir a passagem (R7).

        Idempotente por reconstrução: os assentos da sala são apagados e
        refeitos. Só é seguro porque `_reset_demo_state` já removeu as
        ocupações — sem isso, `ReservedSeat.seat` com PROTECT impediria.
        """
        por_fileira = settings.SEATS_PER_ROW
        criados = []

        for room in rooms:
            room.seats.all().delete()

            posicoes = self._posicoes_da_sala(room.capacity, por_fileira)

            # Os últimos lugares da última fileira. `min` protege a sala cuja
            # última fileira tem menos lugares que a cota de acessibilidade.
            ultima_letra = posicoes[-1][0] if posicoes else None
            na_ultima = [p for p in posicoes if p[0] == ultima_letra]
            acessiveis = {
                p for p in na_ultima[-min(settings.ACCESSIBLE_SEATS_PER_ROOM, len(na_ultima)) :]
            }

            criados.extend(
                Seat.objects.bulk_create(
                    [
                        Seat(
                            room=room,
                            row=letra,
                            number=numero,
                            kind=(
                                Seat.Kind.ACCESSIBLE
                                if (letra, numero) in acessiveis
                                else Seat.Kind.COMMON
                            ),
                        )
                        for letra, numero in posicoes
                    ]
                )
            )

        return criados

    @staticmethod
    def _posicoes_da_sala(capacity, por_fileira):
        """As posições (letra, número) de uma sala, na ordem de leitura.

        Vinte e seis fileiras é o teto do alfabeto — bem acima de qualquer
        sala do cenário, mas o corte explícito evita gerar identificação
        ilegível em silêncio se a capacidade crescer.
        """
        teto = 26 * por_fileira
        total = min(capacity, teto)

        return [
            (chr(ord("A") + indice // por_fileira), indice % por_fileira + 1)
            for indice in range(total)
        ]

    def _buscar_por_nome(self, fragmento):
        """Encontra um filme por fragmento do título, ou None.

        Cada palavra do fragmento é exigida separadamente, em vez de buscar a
        expressão inteira. É o que faz "homem aranha" achar
        "Homem-Aranha: Um Novo Dia": `unaccent` resolve acento e `icontains`
        resolve caixa, mas **nenhum dos dois remove pontuação** — a expressão
        literal "homem aranha" não existe dentro de "Homem-Aranha".

        Exigir as palavras uma a uma atravessa hífen, dois-pontos e qualquer
        outro separador (R2, corrigido na implementação).

        O desempate é obrigatório: sem ordem fixa, dois filmes casando com o
        mesmo fragmento produziriam vitrines diferentes entre execuções.
        """
        consulta = Movie.objects.filter(is_active=True)
        for palavra in fragmento.split():
            consulta = consulta.filter(title__unaccent__icontains=palavra)

        candidatos = list(consulta.order_by("-release_date", "pk")[:2])

        if not candidatos:
            return None

        if len(candidatos) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f'  "{fragmento}" casou com mais de um filme; '
                    f"escolhido: {candidatos[0].title}"
                )
            )

        return candidatos[0]

    def _pick_movies(self):
        """Escolhe os filmes que vão para a vitrine, **em ordem**.

        ⚠️ A ordem do retorno define o carrossel — ver o comentário em
        DESTAQUES, no topo do arquivo.

        Montagem, nesta sequência:
          1. os destaques nomeados, na ordem de DESTAQUES
          2. os demais nomeados (à venda, mas fora do carrossel)
          3. preenchimento até FILMES_A_VENDA pelo critério de vitrine

        O preenchimento existe porque uma vitrine com quatro filmes faz o
        carrossel de três parecer a lista inteira. Critério, em ordem de
        preferência:
          a. longa-metragem com arte, já lançado — o que um cinema exibe hoje
          b. qualquer longa-metragem com arte
          c. o que houver, para o seed nunca falhar em catálogo pequeno
        """
        escolhidos = []
        vistos = set()
        ausentes = []

        for fragmento in DESTAQUES + TAMBEM_A_VENDA:
            filme = self._buscar_por_nome(fragmento)
            if filme is None:
                # Ausência é aviso, não falha: o catálogo externo pode renomear
                # ou parar de listar um filme, e um seed que quebra por isso é
                # pior do que uma vitrine com um filme a menos (R3).
                ausentes.append(fragmento)
                continue
            if filme.pk not in vistos:
                escolhidos.append(filme)
                vistos.add(filme.pk)

        if ausentes:
            nomes = ", ".join(f.title() for f in ausentes)
            self.stdout.write(
                self.style.WARNING(
                    f"  não encontrado(s) no catálogo: {nomes} "
                    "— rode sync_tmdb com um --limit maior"
                )
            )

        hoje = timezone.localdate()
        base = Movie.objects.filter(is_active=True).exclude(backdrop_path="")

        filtros = [
            base.filter(
                runtime_minutes__gte=MIN_RUNTIME_MINUTES,
                release_date__lte=hoje,
            ).order_by("-release_date", "pk"),
            base.filter(runtime_minutes__gte=MIN_RUNTIME_MINUTES).order_by("-release_date", "pk"),
            Movie.objects.filter(is_active=True).order_by("-release_date", "pk"),
        ]

        for consulta in filtros:
            for filme in consulta:
                if len(escolhidos) >= FILMES_A_VENDA:
                    return escolhidos
                if filme.pk in vistos:
                    continue
                escolhidos.append(filme)
                vistos.add(filme.pk)

        return escolhidos

    def _seed_screenings(self, movies, rooms):
        # A grade anterior já foi removida por `_reset_demo_state`, junto das
        # reservas que dependiam dela.
        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        screenings = []

        for index, movie in enumerate(movies):
            for offset_index, hours in enumerate(SESSION_OFFSETS_HOURS):
                room = rooms[(index + offset_index) % len(rooms)]

                # ⚠️ É AQUI que a ordem da lista vira a vitrine: o índice do
                # filme desloca o horário em 30 minutos, e o carrossel exibe
                # os de sessão mais próxima. Primeiro na lista, primeiro no
                # destaque.
                #
                # A constraint UNIQUE(sala, horário) fica protegida sem
                # depender da sala: com 12 filmes o deslocamento máximo é de
                # 5h30, e as faixas de horário distam 23h entre si — dois
                # filmes nunca chegam ao mesmo instante.
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

    def _report(self, users, rooms, seats, movies, screenings):
        self.stdout.write(self.style.SUCCESS("\nCenário de demonstração pronto.\n"))
        self.stdout.write(
            f"  {len(movies)} filme(s) à venda · {len(rooms)} sala(s) · "
            f"{len(seats)} lugar(es) · {len(screenings)} sessão(ões) publicada(s)\n"
        )

        # A vitrine precisa ser conferível sem abrir o navegador (FR-014): os
        # primeiros da lista são os que o carrossel vai exibir, porque têm a
        # sessão mais próxima.
        no_carrossel = movies[:HIGHLIGHTS_LIMIT]
        so_na_trilha = movies[HIGHLIGHTS_LIMIT:]

        if no_carrossel:
            self.stdout.write(self.style.MIGRATE_HEADING("No carrossel (sessão mais próxima):"))
            for posicao, filme in enumerate(no_carrossel, start=1):
                self.stdout.write(f"  {posicao}. {filme.title}")

        if so_na_trilha:
            self.stdout.write(self.style.MIGRATE_HEADING("\nTambém à venda (só na trilha):"))
            for filme in so_na_trilha:
                self.stdout.write(f"  · {filme.title}")
        self.stdout.write("")

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
