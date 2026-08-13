"""Sonda de vida para o orquestrador — sem autenticação e sem TMDb.

O Render (e qualquer health check) precisa de um endereço que responda 200
enquanto o processo sobe, sem depender de sessão nem de serviço externo.
A consulta ao banco é o mínimo: se o Postgres não está alcançável, esta
instância não deve receber tráfego.
"""

from django.conf import settings
from django.db import connection
from django.http import HttpResponse


def healthz(request):
    connection.ensure_connection()
    resposta = HttpResponse("ok", content_type="text/plain")
    # O navegador da home pinge este endereço para acordar a API dormindo.
    # Sem CORS a sonda falha em silêncio e a página recarrega para sempre.
    origem = request.headers.get("Origin", "")
    if origem in settings.CORS_ALLOWED_ORIGINS:
        resposta["Access-Control-Allow-Origin"] = origem
    return resposta
