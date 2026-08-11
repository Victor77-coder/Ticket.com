"""Habilita a extensão `unaccent` do PostgreSQL.

É o que permite `title__unaccent__icontains` — buscar "cacador" e achar
"Caçador" (FR-008). Ver research.md (R2) para as alternativas descartadas.

Nenhum dado é migrado e nenhum backfill é necessário: a normalização acontece
na consulta, mantendo o título como única fonte de verdade.
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        UnaccentExtension(),
    ]
