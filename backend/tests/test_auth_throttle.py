"""Limite de tentativas de entrada (FR-007)."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

User = get_user_model()

SENHA = "desafio2026"
MAX_TENTATIVAS = 5


@pytest.fixture(autouse=True)
def _limpa_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(username="cliente1", password=SENHA)


def _login(client, username="cliente1", password="errada", origem=None):
    extra = {"HTTP_X_FORWARDED_FOR": origem} if origem else {}
    return client.post(
        reverse("accounts:login"),
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
        **extra,
    )


@pytest.mark.django_db
def test_bloqueia_apos_o_limite(client, usuario):
    for _ in range(MAX_TENTATIVAS):
        assert _login(client).status_code == 401

    resposta = _login(client)

    assert resposta.status_code == 429
    corpo = resposta.json()
    assert "Muitas tentativas" in corpo["detail"]
    assert corpo["retry_after_seconds"] > 0


@pytest.mark.django_db
def test_bloqueio_vale_mesmo_com_a_senha_correta(client, usuario):
    """Depois de bloqueado, acertar a senha não deve destravar na hora.

    Caso contrário o limite só atrasaria a força bruta em vez de contê-la.
    """
    for _ in range(MAX_TENTATIVAS):
        _login(client)

    assert _login(client, password=SENHA).status_code == 429


@pytest.mark.django_db
def test_entrada_bem_sucedida_zera_o_contador(client, usuario):
    for _ in range(MAX_TENTATIVAS - 1):
        _login(client)

    assert _login(client, password=SENHA).status_code == 200

    # Com o contador zerado, há novamente o orçamento inteiro de tentativas.
    for _ in range(MAX_TENTATIVAS - 1):
        assert _login(Client()).status_code == 401


@pytest.mark.django_db
def test_bloqueio_nao_atinge_outro_identificador(client, usuario):
    """Só pelo identificador bloquearia contas alheias de uma rede compartilhada."""
    User.objects.create_user(username="cliente2", password=SENHA)

    for _ in range(MAX_TENTATIVAS):
        _login(client, username="cliente1")

    assert _login(client, username="cliente1").status_code == 429
    assert _login(client, username="cliente2", password=SENHA).status_code == 200


@pytest.mark.django_db
def test_bloqueio_nao_atinge_outra_origem(client, usuario):
    for _ in range(MAX_TENTATIVAS):
        _login(client, origem="10.0.0.1")

    assert _login(client, origem="10.0.0.1").status_code == 429
    assert _login(client, origem="10.0.0.2").status_code == 401


@pytest.mark.django_db
def test_trocar_de_identificador_nao_contorna_o_limite(client, usuario):
    """Cada par origem+identificador tem seu próprio orçamento, mas o do
    identificado original continua bloqueado."""
    for _ in range(MAX_TENTATIVAS):
        _login(client, username="cliente1", origem="10.0.0.1")

    _login(client, username="outro", origem="10.0.0.1")

    assert _login(client, username="cliente1", origem="10.0.0.1").status_code == 429


@pytest.mark.django_db
def test_identificador_e_tratado_sem_diferenca_de_caixa(client, usuario):
    """Alternar maiúsculas não pode render um orçamento novo de tentativas."""
    for _ in range(MAX_TENTATIVAS):
        _login(client, username="cliente1")

    assert _login(client, username="CLIENTE1").status_code == 429
