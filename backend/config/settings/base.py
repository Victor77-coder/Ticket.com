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

# Segredo que assina o código do ingresso. PRÓPRIO e DISTINTO da SECRET_KEY,
# por exigência do Princípio III e do FR-031: são dois raios de comprometimento
# diferentes. Vazar a SECRET_KEY compromete sessões; vazar esta compromete a
# catraca. Amarrar as duas faz um incidente virar dois.
#
# Sem valor padrão de propósito — um padrão em código viraria o segredo real de
# todo mundo que não leu o README, e o QR passaria a ser forjável por quem leu
# o repositório. Falta da variável derruba o boot, e isso é o comportamento
# desejado.
TICKET_SIGNING_KEY = env("TICKET_SIGNING_KEY")
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
# Compose injeta POSTGRES_*. O Render injeta DATABASE_URL. As duas formas
# não podem ser exigidas ao mesmo tempo: o `from .base import *` do prod
# avaliaria POSTGRES_DB antes de o prod.py ter chance de usar a URL.
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    # No host o PostgreSQL é exposto em 5438; dentro da rede do Compose o
    # serviço `db` atende em 5432. POSTGRES_HOST/PORT vêm do docker-compose.
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

# --- Sessão ---
# Duas semanas é o padrão do Django e cobre folgadamente o período de
# avaliação sem virar sessão eterna.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# O cookie que o navegador guarda é emitido pelo Next, não por aqui: o
# navegador nunca fala com o Django direto. Este cookie só trafega no salto
# servidor-a-servidor Next → Django.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --- Limite de tentativas de entrada ---
# Comportamento exigido pelo FR-007. Contador no cache, chaveado por origem e
# identificador: só pela origem, alguém numa rede compartilhada bloquearia
# contas alheias; só pelo identificador, trocar de usuário contornaria.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 60 * 15

# --- DRF ---
# Princípio IV da constitution: negar por padrão. As rotas públicas declaram
# AllowAny explicitamente na própria view, nunca por herança silenciosa.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Resolve o usuário a partir do cookie de sessão que o Next repassa.
        "rest_framework.authentication.SessionAuthentication",
    ],
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

# --- Reserva de assentos ---
# Prazo da reserva temporária. Fixo de propósito: não é lido do ambiente,
# porque encurtá-lo para demonstrar a expiração ao vivo foi descartado —
# ver "Limitação assumida da demonstração" em specs/007-seat-selection/spec.md.
RESERVATION_HOLD_MINUTES = 10

# Teto de lugares por reserva. Impede que uma pessoa trave a sala inteira
# sem impedir a compra de um grupo.
MAX_SEATS_PER_RESERVATION = 6

# Lugares reservados para acessibilidade por sala, na última fileira.
ACCESSIBLE_SEATS_PER_ROOM = 3

# Lugares por fileira do mapa. O corredor visual fica entre o quinto e o sexto.
SEATS_PER_ROW = 10

# --- Pagamento simulado ---
# A cobrança é simulada: sem transação financeira real e sem provedor externo
# (FR-005). O desfecho é decidido pelo NÚMERO do cartão, por esta tabela.
#
# DETERMINÍSTICO, nunca por sorteio. A constitution exige que os dois caminhos
# — aprovação e recusa — sejam "exercitáveis pelo avaliador", e recusa que
# aparece uma vez em cada cinco não é exercitável nem testável: o avaliador
# pode não vê-la, e o teste falharia sozinho de vez em quando.
#
# ESTA TABELA É CONTRATO COM O README (FR-007). Mudar um número aqui sem mudar
# o README quebra a única forma que o avaliador tem de alcançar a recusa.
#
# Os números são os de ambiente de teste que qualquer pessoa que já integrou
# pagamento reconhece — quem digitar 4242… por reflexo acerta o caminho feliz
# sem consultar nada. Qualquer outro número bem formado é aprovado.
PAYMENT_DECLINE_CARDS = {
    "4000000000009995": "saldo_insuficiente",
    "4000000000000069": "cartao_expirado",
    "4000000000000002": "recusado_pelo_emissor",
}

# Documentado no README como o cartão do caminho feliz.
PAYMENT_APPROVED_CARD = "4242424242424242"
