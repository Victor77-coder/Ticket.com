"""Limite de tentativas de entrada (FR-007).

Contador no cache, não no banco: escrever a cada senha errada transformaria
uma tentativa de força bruta em carga de escrita.

A chave combina origem e identificador de propósito — só pela origem, alguém
numa rede compartilhada bloquearia contas alheias; só pelo identificador,
trocar de usuário contornaria o limite.
"""

from django.conf import settings
from django.core.cache import cache

PREFIXO = "auth:tentativas"


def _chave(origem, identificador):
    return f"{PREFIXO}:{origem}:{identificador}".lower()


def origem_da_requisicao(request):
    """Endereço de origem da requisição.

    Atrás do proxy do Next o endereço remoto é sempre o do contêiner do
    front-end, então `X-Forwarded-For` é o que distingue os visitantes. O
    primeiro elemento é o cliente original.
    """
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "desconhecido")


def esta_bloqueado(origem, identificador):
    """Se este par já esgotou as tentativas permitidas."""
    return _contagem(origem, identificador) >= settings.LOGIN_MAX_ATTEMPTS


def segundos_restantes(origem, identificador):
    """Quanto falta para o bloqueio expirar, em segundos."""
    restante = cache.ttl(_chave(origem, identificador)) if hasattr(cache, "ttl") else None
    if restante is None:
        # O backend de cache em memória não expõe TTL. A janela cheia é uma
        # estimativa honesta: nunca informa menos tempo do que o real.
        return settings.LOGIN_ATTEMPT_WINDOW_SECONDS
    return max(int(restante), 0)


def registrar_falha(origem, identificador):
    """Conta mais uma tentativa malsucedida e devolve o total."""
    chave = _chave(origem, identificador)
    janela = settings.LOGIN_ATTEMPT_WINDOW_SECONDS

    # `add` só grava se a chave não existir — é o que inicia a janela sem
    # renová-la a cada falha subsequente.
    cache.add(chave, 0, janela)
    try:
        return cache.incr(chave)
    except ValueError:
        # A chave expirou entre o `add` e o `incr`. Recomeça a janela.
        cache.set(chave, 1, janela)
        return 1


def limpar(origem, identificador):
    """Zera o contador — chamado após entrada bem-sucedida."""
    cache.delete(_chave(origem, identificador))


def _contagem(origem, identificador):
    return cache.get(_chave(origem, identificador), 0)
