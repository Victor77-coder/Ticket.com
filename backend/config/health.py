"""Sonda de vida para o orquestrador — sem autenticação e sem TMDb.

O Render (e qualquer health check) precisa de um endereço que responda 200
enquanto o processo sobe, sem depender de sessão nem de serviço externo.
A consulta ao banco é o mínimo: se o Postgres não está alcançável, esta
instância não deve receber tráfego.
"""

from django.db import connection
from django.http import HttpResponse


def healthz(_request):
    connection.ensure_connection()
    return HttpResponse("ok", content_type="text/plain")
