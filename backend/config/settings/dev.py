"""Configuração de desenvolvimento."""

from .base import *  # noqa: F403

DEBUG = True

# Cache local em memória. O endpoint de highlights guarda a resposta por 60s
# (R7) — curto o bastante para não segurar um destaque cuja sessão já passou.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ingressos-dev",
    }
}
