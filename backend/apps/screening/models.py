"""Salas e sessões.

Escopo deliberadamente mínimo: só o necessário para decidir quais filmes
entram no carrossel (FR-002) e para listar o que está à venda.

FRONTEIRA COM A FEATURE DE RESERVA — não adicionar aqui:
  - modelos Seat, Reservation, Ticket
  - a constraint UNIQUE(screening, seat) exigida pelo Princípio II
  - qualquer coluna que materialize ocupação de assento

Criar escrita de assento sem a constraint que a protege violaria o
Princípio II da constitution. Ver a seção de fronteira em data-model.md.
"""

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
        """Assentos já vendidos.

        Valor derivado por consulta, nunca coluna materializada. Enquanto a
        feature de reserva não existir não há ingresso emitido, então o valor
        é sempre 0. Quando ela chegar, esta propriedade passa a contar os
        ingressos confirmados — sem migração de dados aqui.
        """
        return 0

    @property
    def has_available_seats(self):
        return self.seats_taken < self.room.capacity
