"""Configuração de produção — Render.

O navegador nunca fala com o Django: o Next, no mesmo painel, chama a API
pela rede interna em HTTP. Por isso NÃO há SECURE_SSL_REDIRECT — um
redirect para https:// quebraria o salto interno e o health check.
O HTTPS público fica na borda do Render, no serviço do front-end.
"""

import os

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])  # noqa: F405
for extra in (
    os.environ.get("RENDER_EXTERNAL_HOSTNAME"),
    "ticketcom-api",  # Host da rede interna (Next → http://ticketcom-api:10000)
    ".onrender.com",
):
    if extra and extra not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(extra)

DATABASES["default"]["CONN_MAX_AGE"] = 60  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
DATABASES["default"]["OPTIONS"].setdefault("sslmode", "require")  # noqa: F405

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# O cookie que o navegador guarda é emitido pelo Next (HTTPS). O cookie
# que trafega neste processo só existe no salto interno HTTP Next → Django.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
if SITE_URL and SITE_URL not in CSRF_TRUSTED_ORIGINS:  # noqa: F405
    CSRF_TRUSTED_ORIGINS.append(SITE_URL)

CORS_ALLOWED_ORIGINS = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    default=[SITE_URL] if SITE_URL else [],  # noqa: F405
)

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# WhiteNoise logo após Security, como a documentação pede. O CORS do base
# continua no restante da lista — o navegador não chama o Django, mas o
# admin ainda existe.
_middleware = [m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"]  # noqa: F405
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *_middleware,
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ingressos-prod",
    }
}
