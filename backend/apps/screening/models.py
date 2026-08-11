"""Salas, sessões, assentos e reservas.

Da 001 até a 006 este arquivo carregou um aviso: escrita de ocupação de
assento não entrava sem a constraint UNIQUE(screening, seat) que a protege,
porque criar uma sem a outra é o que o Princípio II proíbe.

A feature 007 atravessou a fronteira, e o aviso saiu porque foi cumprido:
ReservedSeat e `unico_assento_por_sessao` nasceram na mesma migração. A
garantia continua sendo a razão de o modelo poder existir — ver a seção
"onde a garantia vive" em specs/007-seat-selection/data-model.md.

Ticket permanece fora: emissão de ingresso é a próxima feature.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Room(models.Model):
    name = models.CharField(max_length=60)
    capacity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScreeningQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Screening.Status.PUBLISHED)

    def upcoming(self):
        return self.filter(starts_at__gt=timezone.now())

    def sellable(self):
        """Sessões que um cliente pode efetivamente comprar agora."""
        return self.published().upcoming()


class Screening(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicada"
        CANCELLED = "cancelled", "Cancelada"

    # PROTECT: apagar um filme com sessão agendada deve falhar, não cascatear.
    movie = models.ForeignKey(
        "catalog.Movie", related_name="screenings", on_delete=models.PROTECT
    )
    room = models.ForeignKey(Room, related_name="screenings", on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScreeningQuerySet.as_manager()

    class Meta:
        verbose_name = "sessão"
        verbose_name_plural = "sessões"
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "starts_at"],
                name="uma_sessao_por_sala_e_horario",
            ),
        ]
        indexes = [
            # Exatamente o filtro da consulta de elegibilidade ao destaque.
            models.Index(fields=["status", "starts_at"], name="idx_sessao_status_inicio"),
        ]

    def __str__(self):
        return f"{self.movie.title} — {self.starts_at:%d/%m/%Y %H:%M}"

    @property
    def seats_taken(self):
        """Assentos ocupados por reserva viva.

        Valor derivado por consulta, nunca coluna materializada — foi assim
        que a 004 escreveu esta propriedade prevendo a feature de reserva, e
        é por isso que a 007 pôde preenchê-la sem migração de dados.

        Reserva vencida não conta: a liberação é por consulta, sem depender
        de rotina agendada ter passado.
        """
        return self.reserved_seats.filter(
            reservation__expires_at__gt=timezone.now()
        ).count()

    @property
    def has_available_seats(self):
        return self.seats_taken < self.room.capacity


class Seat(models.Model):
    """Um lugar físico da sala. O mesmo em todas as sessões dela."""

    class Kind(models.TextChoices):
        COMMON = "common", "Comum"
        ACCESSIBLE = "accessible", "Acessibilidade"

    room = models.ForeignKey(Room, related_name="seats", on_delete=models.CASCADE)
    row = models.CharField(max_length=2)
    number = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.COMMON)

    class Meta:
        verbose_name = "assento"
        verbose_name_plural = "assentos"
        ordering = ["row", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "row", "number"],
                name="unico_lugar_por_posicao_na_sala",
            ),
        ]

    def __str__(self):
        return f"{self.row}{self.number}"

    @property
    def label(self):
        return f"{self.row}{self.number}"


class Reservation(models.Model):
    """Intenção de compra de um cliente para uma sessão.

    É a unidade que segue para o pagamento: um cliente comprando três
    lugares tem uma reserva, não três.
    """

    class Status(models.TextChoices):
        HELD = "held", "Reservada"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"

    screening = models.ForeignKey(
        Screening, related_name="reservations", on_delete=models.PROTECT
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reservations", on_delete=models.PROTECT
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    expires_at = models.DateTimeField()

    # A idempotência é resolvida por esta constraint, nunca por consulta
    # prévia: "já existe reserva parecida?" é justamente o padrão que a
    # concorrência quebra — duas requisições verificam, nenhuma encontra,
    # ambas criam.
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reserva {self.pk} — {self.customer} — {self.screening}"

    @property
    def is_expired(self):
        """Vencimento é sempre lido do relógio, nunca do campo `status`.

        `status` é registro histórico e serve à feature de pagamento para
        distinguir "venceu" de "foi paga". Ele não é o que libera o lugar —
        se fosse, haveria uma janela entre o vencimento e a rotina que o
        marcasse, e nessa janela o lugar apareceria tomado sem estar.
        """
        return self.expires_at <= timezone.now()


class ReservedSeat(models.Model):
    """A ocupação de um lugar por uma reserva.

    É esta tabela que carrega o Princípio II.
    """

    reservation = models.ForeignKey(
        Reservation, related_name="seats", on_delete=models.CASCADE
    )
    # Denormalizado de propósito: `reservation.screening` já tem a
    # informação, mas a constraint precisa das duas colunas na MESMA tabela,
    # e nem o Django nem o PostgreSQL declaram unicidade através de
    # travessia de chave estrangeira. Preenchido num único ponto do código
    # (services/reservas.py) e nunca editado depois.
    screening = models.ForeignKey(
        Screening, related_name="reserved_seats", on_delete=models.PROTECT
    )
    seat = models.ForeignKey(Seat, related_name="occupations", on_delete=models.PROTECT)

    class Meta:
        verbose_name = "assento reservado"
        verbose_name_plural = "assentos reservados"
        constraints = [
            # A garantia do Princípio II. ABSOLUTA, sem `condition`.
            #
            # O índice parcial sobre "reserva viva" seria a saída natural
            # para conciliar com a expiração e é IMPOSSÍVEL: o PostgreSQL
            # exige predicado imutável em índice parcial, e now() não é.
            #
            # A conciliação está em services/reservas.py: a linha vencida é
            # apagada sob SELECT FOR UPDATE, dentro da própria transação de
            # reserva. Ver R1 e R2 em specs/007-seat-selection/research.md.
            models.UniqueConstraint(
                fields=["screening", "seat"],
                name="unico_assento_por_sessao",
            ),
        ]

    def __str__(self):
        return f"{self.seat} — sessão {self.screening_id}"
