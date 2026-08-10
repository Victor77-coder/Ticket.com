"""Usuário e papéis.

A constitution (Princípio IV) define exatamente três papéis com fronteiras
rígidas. O modelo é criado agora, e não na feature de autenticação, porque o
Django exige que AUTH_USER_MODEL seja fixado antes da primeira migração —
trocá-lo depois obriga a recriar o banco.

Escopo mínimo de propósito: apenas o campo `role` e os atalhos de leitura. As
regras de permissão por endpoint pertencem à feature de autenticação.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organizador"
        CUSTOMER = "customer", "Cliente"
        GATE = "gate", "Portaria"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
        verbose_name="papel",
    )

    class Meta(AbstractUser.Meta):
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_gate(self):
        return self.role == self.Role.GATE
