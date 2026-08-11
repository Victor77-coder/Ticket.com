"""Configuração compartilhada do projeto.

Toda variável sensível vem do ambiente. Nenhum segredo tem valor padrão
utilizável — ver `.env.example` na raiz do repositório.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    POSTGRES_PORT=(int, 5432),
)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Registra o lookup `__unaccent`, usado pela busca do cabeçalho. A
    # extensão no PostgreSQL sozinha não basta: sem este app o Django levanta
    # FieldError, não erro de banco.
    "django.contrib.postgres",
    "rest_framework",
    "corsheaders",
    "apps.accounts",
    "apps.catalog",
    "apps.screening",
]

# Fixado antes da primeira migração: o Django não permite trocar o modelo de
# usuário depois sem recriar o banco. Os três papéis do Princípio IV vivem aqui.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Banco de dados ---
# No host o PostgreSQL é exposto em 5438; dentro da rede do Compose o serviço
# `db` atende em 5432. POSTGRES_HOST/PORT são injetados pelo docker-compose.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default=5438),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
# Princípio IV da constitution: negar por padrão. As rotas públicas declaram
# AllowAny explicitamente na própria view, nunca por herança silenciosa.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --- CORS ---
# O fetch principal da home é server-side e não passa por CORS. A liberação
# existe para chamadas feitas do navegador em features futuras.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5003", "http://127.0.0.1:5003"],
)

# --- TMDb ---
# Princípio VII: a chave nunca chega ao navegador. Só o comando de sync a usa.
TMDB_API_KEY = env("TMDB_API_KEY", default="")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"
TMDB_LANGUAGE = "pt-BR"
TMDB_REGION = "BR"
TMDB_TIMEOUT_SECONDS = 10.0

SITE_URL = env("SITE_URL", default="http://localhost:5003")
