"""Contrato da autenticação.

O teste de vazamento é o GATE DO PRINCÍPIO IV. O de mensagem uniforme é o
requisito mais fácil de quebrar em manutenção: basta alguém acrescentar um
`if not user` com texto diferente e a enumeração de contas volta.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

User = get_user_model()

SENHA = "desafio2026"


@pytest.fixture(autouse=True)
def _limpa_cache():
    """O contador de tentativas é global; um teste não pode herdar do vizinho."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def make_user(db):
    def _make(username="cliente1", role=User.Role.CUSTOMER, **kwargs):
        defaults = {
            "first_name": "Camila",
            "last_name": "Souza",
            "email": f"{username}@cinema.test",
        }
        defaults.update(kwargs)
        user = User.objects.create_user(username=username, password=SENHA, role=role, **defaults)
        return user

    return _make


def _login(client, username="cliente1", password=SENHA):
    return client.post(
        reverse("accounts:login"),
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )


# --- Entrada bem-sucedida -------------------------------------------------


@pytest.mark.django_db
def test_entrada_bem_sucedida_devolve_sessao(client, make_user):
    make_user()

    response = _login(client)

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["user"] == {"nome": "Camila Souza", "papel": "customer"}
    assert corpo["session_key"]
    assert corpo["expires_at"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("username", "role"),
    [
        ("organizador", User.Role.ORGANIZER),
        ("cliente1", User.Role.CUSTOMER),
        ("cliente2", User.Role.CUSTOMER),
        ("portaria", User.Role.GATE),
    ],
)
def test_os_quatro_papeis_semeados_entram(client, make_user, username, role):
    """SC-002: as contas publicadas no README entram e recebem o próprio papel."""
    make_user(username=username, role=role)

    response = _login(client, username=username)

    assert response.status_code == 200
    assert response.json()["user"]["papel"] == role


@pytest.mark.django_db
def test_nome_cai_para_o_usuario_quando_nao_ha_nome_preenchido(client, make_user):
    """O cabeçalho nunca pode exibir espaço em branco no lugar da identificação."""
    make_user(first_name="", last_name="")

    assert _login(client).json()["user"]["nome"] == "cliente1"


# --- Recusa uniforme (FR-004, SC-005) -------------------------------------


@pytest.mark.django_db
def test_usuario_inexistente_e_senha_errada_produzem_a_mesma_resposta(client, make_user):
    make_user()

    inexistente = _login(client, username="ninguem")
    senha_errada = _login(client, password="errada")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()
    assert inexistente.json() == {"detail": "Usuário ou senha incorretos."}


@pytest.mark.django_db
def test_conta_inativa_recebe_a_mesma_mensagem(client, make_user):
    """Revelar que a conta existe mas está inativa já entrega meio ataque."""
    make_user(is_active=False)

    response = _login(client)

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuário ou senha incorretos."}


@pytest.mark.django_db
def test_a_resposta_de_recusa_nao_diz_qual_campo_errou(client, make_user):
    make_user()

    corpo = json.dumps(_login(client, password="errada").json()).lower()

    assert "senha incorret" in corpo
    for pista in ["não existe", "inexistente", "inativ", "usuário não"]:
        assert pista not in corpo


# --- Validação de campos (FR-006) -----------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "esperado"),
    [
        ({"password": SENHA}, "Informe o usuário."),
        ({"username": "cliente1"}, "Informe a senha."),
        ({"username": "", "password": ""}, "Informe o usuário."),
    ],
)
def test_campo_faltando_responde_400_apontando_o_campo(client, payload, esperado):
    response = client.post(
        reverse("accounts:login"), data=json.dumps(payload), content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == esperado


@pytest.mark.django_db
def test_campo_faltando_nao_consome_tentativa(client, make_user):
    """Erro de formulário não pode gastar o limite de tentativas."""
    make_user()

    for _ in range(10):
        client.post(
            reverse("accounts:login"),
            data=json.dumps({"username": "cliente1"}),
            content_type="application/json",
        )

    assert _login(client).status_code == 200


# --- Gate do Princípio IV -------------------------------------------------


@pytest.mark.django_db
def test_resposta_de_entrada_nao_vaza_credencial(client, make_user):
    """GATE DO PRINCÍPIO IV.

    Falha aqui é violação da constitution, não detalhe de contrato.
    """
    make_user()

    bruto = json.dumps(_login(client).json()).lower()

    proibidos = [
        "password",
        "pbkdf2",
        "argon2",
        "bcrypt",
        "last_login",
        "is_staff",
        "is_superuser",
        "email",
        "cinema.test",
    ]
    vazados = [campo for campo in proibidos if campo in bruto]
    assert not vazados, f"resposta de entrada vazou: {vazados}"


@pytest.mark.django_db
def test_sessao_expoe_apenas_nome_e_papel(client, make_user):
    make_user()
    _login(client)

    corpo = client.get(reverse("accounts:me")).json()

    assert set(corpo) == {"nome", "papel"}


@pytest.mark.django_db
def test_me_nao_vaza_credencial(client, make_user):
    make_user()
    _login(client)

    bruto = json.dumps(client.get(reverse("accounts:me")).json()).lower()

    for proibido in ["password", "pbkdf2", "email", "is_staff", "last_login"]:
        assert proibido not in bruto


# --- Sessão ---------------------------------------------------------------


@pytest.mark.django_db
def test_me_sem_sessao_responde_401(client):
    """Estado normal, não falha: é como o cabeçalho sabe mostrar 'Entrar'."""
    response = client.get(reverse("accounts:me"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Sessão não encontrada."}


@pytest.mark.django_db
def test_sessao_persiste_entre_requisicoes(client, make_user):
    make_user()
    _login(client)

    assert client.get(reverse("accounts:me")).status_code == 200
    assert client.get(reverse("accounts:me")).status_code == 200


@pytest.mark.django_db
def test_sessao_expirada_responde_401_sem_excecao(client, make_user):
    """FR-017: expirar não pode produzir erro."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    make_user()
    _login(client)

    Session.objects.update(expire_date=timezone.now() - timezone.timedelta(days=1))

    response = client.get(reverse("accounts:me"))
    assert response.status_code == 401


# --- Saída (FR-014) -------------------------------------------------------


@pytest.mark.django_db
def test_saida_invalida_a_sessao(client, make_user):
    make_user()
    _login(client)
    assert client.get(reverse("accounts:me")).status_code == 200

    assert client.post(reverse("accounts:logout")).status_code == 204

    assert client.get(reverse("accounts:me")).status_code == 401


@pytest.mark.django_db
def test_saida_sem_sessao_responde_204(client):
    """Encerrar algo que já não existe é o resultado desejado, não erro."""
    assert client.post(reverse("accounts:logout")).status_code == 204


@pytest.mark.django_db
def test_chave_de_sessao_antiga_deixa_de_resolver(client, make_user):
    from django.contrib.sessions.models import Session

    make_user()
    chave = _login(client).json()["session_key"]
    client.post(reverse("accounts:logout"))

    assert not Session.objects.filter(session_key=chave).exists()
