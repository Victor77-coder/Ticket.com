"""Tipo de ingresso e valor cobrado por lugar (feature 014).

ESCRITA À MÃO, e não gerada. `unit_price` não tem padrão de propósito — um
padrão significaria que existe valor razoável a gravar quando ninguém decidiu, e
não existe. Sem padrão, o `makemigrations` pergunta o que fazer com as linhas
que já existem, e a resposta certa não cabe numa pergunta interativa: ela é uma
consulta.

O PASSO DE DADOS É RETRATO HONESTO DO PASSADO. Tudo o que foi vendido antes da
014 foi vendido como inteira, ao preço da sessão — não havia outra opção. E o
preço não muda sob reserva viva, porque a 013 não permite editar sessão
publicada.

Três operações, na ordem que o PostgreSQL exige para coluna obrigatória em
tabela populada:

    1. acrescenta permitindo nulo — nenhuma linha existente é violada;
    2. preenche a partir da sessão de cada lugar;
    3. fecha para nulo, e a partir daqui toda escrita precisa decidir.

A volta apaga as colunas. É segura: nada fora da 014 as lê.
"""

from django.db import migrations, models


def preencher_valores(apps, schema_editor):
    """Um UPDATE com junção, e não um laço em Python.

    Uma base de demonstração tem centenas de linhas e um laço rodaria em
    silêncio; o mesmo laço numa base real seria uma consulta por lugar. O SQL
    faz o trabalho onde o dado está.
    """
    schema_editor.execute(
        """
        UPDATE screening_reservedseat AS rs
           SET unit_price = s.price,
               ticket_type = 'inteira'
          FROM screening_screening AS s
         WHERE s.id = rs.screening_id
           AND rs.unit_price IS NULL
        """
    )


def sem_volta(apps, schema_editor):
    """A volta não precisa fazer nada: as colunas somem logo em seguida."""


class Migration(migrations.Migration):
    dependencies = [
        ("screening", "0005_ticket_used_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservedseat",
            name="ticket_type",
            field=models.CharField(
                choices=[("inteira", "Inteira"), ("meia", "Meia")],
                default="inteira",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="reservedseat",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, max_digits=8, null=True),
        ),
        migrations.RunPython(preencher_valores, sem_volta),
        migrations.AlterField(
            model_name="reservedseat",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
    ]
