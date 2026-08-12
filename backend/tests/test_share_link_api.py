"""Contrato do link de compartilhamento: gerar, revogar, e o que morre.

A prova de concorrência mora em `test_share_link_concurrency.py` e a prova de
não vazamento em `test_share_link_leakage.py`. Aqui ficam os desfechos que uma
conexão só já demonstra — e o que este arquivo protege, acima de tudo, é que
**revogado seja para sempre** e que **token morto e token inventado sejam
indistinguíveis**.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.screening.models import TicketShareLink

User = get_user_model()

SENHA = "desafio2026"


@pytest.fixture
def cliente(db):
    return User.objects.create_user(
        username="cliente1", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def outro_cliente(db):
    return User.objects.create_user(
        username="cliente2", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def ingresso(make_movie, make_screening, seats, room, cliente, make_tickets):
    sessao = make_screening(make_movie("A Odisseia"), hours_from_now=24)
    lugares = list(room.seats.filter(kind="common")[:1])
    return make_tickets(sessao, cliente, lugares, minutes_left=10)[0]


def _url_link(ingresso):
    return reverse("screening:ticket-share-link", args=[ingresso.public_id])


def _url_publica(token):
    return reverse("screening:shared-ticket", args=[token])


def _gerar(client, ingresso):
    return client.post(_url_link(ingresso))


def _revogar(client, ingresso):
    return client.delete(_url_link(ingresso))


# --- Gerar -----------------------------------------------------------------


@pytest.mark.django_db
def test_gerar_devolve_201_e_endereco_completo(client, cliente, ingresso):
    """FR-024 — pronto para copiar e colar num aplicativo de mensagens."""
    client.force_login(cliente)

    resposta = _gerar(client, ingresso)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["ativo"] is True
    assert corpo["endereco"].startswith("http")
    assert "/ingresso/" in corpo["endereco"]


@pytest.mark.django_db
def test_gerar_de_novo_devolve_o_mesmo_endereco_com_200(client, cliente, ingresso):
    """FR-028 — nunca um segundo link válido em paralelo."""
    client.force_login(cliente)

    primeiro = _gerar(client, ingresso).json()
    segunda = _gerar(client, ingresso)

    assert segunda.status_code == 200
    assert segunda.json()["endereco"] == primeiro["endereco"]
    assert TicketShareLink.objects.filter(
        ticket=ingresso, revoked_at__isnull=True
    ).count() == 1


@pytest.mark.django_db
def test_ingresso_sem_link_gerado_nao_tem_endereco_publico(client, cliente, ingresso):
    """FR-034 — não existe endereço a adivinhar."""
    client.force_login(cliente)

    corpo = client.get(reverse("screening:ticket-detail", args=[ingresso.public_id])).json()

    assert corpo["link"] == {"ativo": False, "endereco": None}


# --- O token ---------------------------------------------------------------


@pytest.mark.django_db
def test_token_nao_e_o_codigo_do_qr_nem_derivado_dele(client, cliente, ingresso):
    """FR-026, SC-012 — os dois segredos não se encontram."""
    client.force_login(cliente)
    _gerar(client, ingresso)

    token = TicketShareLink.objects.get(ticket=ingresso).token
    corpo = client.get(reverse("screening:ticket-detail", args=[ingresso.public_id])).json()
    codigo = corpo["codigo"]

    assert token != codigo
    assert token not in codigo
    assert codigo not in token
    # Nem o `public_id` aparece no token: ele é o que vai DENTRO do código
    # assinado, e derivar o token dele daria a metade não secreta de graça.
    assert str(ingresso.public_id) not in token


@pytest.mark.django_db
def test_tokens_de_ingressos_distintos_nao_permitem_deduzir_um_terceiro(
    client, cliente, make_movie, make_screening, make_seats, make_tickets
):
    """FR-027, SC-012 — e nenhum deles é sequencial."""
    from apps.screening.models import Room

    sala = Room.objects.create(name="Sala tokens", capacity=5)
    lugares = make_seats(sala, acessiveis=0)
    sessao = make_screening(make_movie("Tokens"), hours_from_now=24, room_obj=sala)
    ingressos = make_tickets(sessao, cliente, lugares[:3], minutes_left=10)

    client.force_login(cliente)
    for i in ingressos:
        _gerar(client, i)

    tokens = list(TicketShareLink.objects.values_list("token", flat=True))

    assert len(set(tokens)) == 3
    assert all(len(t) >= 40 for t in tokens)
    # Nenhum é prefixo de outro: sequencial ou derivado de contador colaria.
    for a in tokens:
        assert sum(1 for b in tokens if b.startswith(a[:20])) == 1


# --- Revogar ---------------------------------------------------------------


@pytest.mark.django_db
def test_revogar_mata_o_endereco_antigo(client, cliente, ingresso):
    """FR-031 — e a página pública deixa de exibir na primeira abertura."""
    client.force_login(cliente)
    endereco = _gerar(client, ingresso).json()["endereco"]
    token = endereco.rsplit("/", 1)[-1]

    assert client.get(_url_publica(token)).status_code == 200

    _revogar(client, ingresso)

    assert client.get(_url_publica(token)).status_code == 404


@pytest.mark.django_db
def test_revogar_sem_link_ativo_devolve_200(client, cliente, ingresso):
    """Idempotente.

    Um `404` na segunda chamada faria o front exibir erro por uma ação que
    produziu exatamente o resultado desejado.
    """
    client.force_login(cliente)
    _gerar(client, ingresso)

    primeira = _revogar(client, ingresso)
    segunda = _revogar(client, ingresso)

    assert primeira.status_code == segunda.status_code == 200
    assert segunda.json() == {"ativo": False, "endereco": None}


@pytest.mark.django_db
def test_link_revogado_nunca_e_apagado(client, cliente, ingresso):
    """FR-031 — preservar a linha é o que impede o token de voltar."""
    client.force_login(cliente)
    _gerar(client, ingresso)
    token_antigo = TicketShareLink.objects.get(ticket=ingresso).token

    _revogar(client, ingresso)

    morto = TicketShareLink.objects.get(token=token_antigo)
    assert morto.revoked_at is not None


@pytest.mark.django_db
def test_gerar_depois_de_revogar_produz_endereco_diferente(client, cliente, ingresso):
    """FR-032, SC-011 — e o revogado continua morto."""
    client.force_login(cliente)
    antigo = _gerar(client, ingresso).json()["endereco"]
    _revogar(client, ingresso)

    novo = _gerar(client, ingresso)

    assert novo.status_code == 201
    assert novo.json()["endereco"] != antigo

    token_antigo = antigo.rsplit("/", 1)[-1]
    assert client.get(_url_publica(token_antigo)).status_code == 404


# --- Token morto e token inventado são a MESMA resposta --------------------


@pytest.mark.django_db
def test_token_revogado_e_token_inventado_respondem_igual(client, cliente, ingresso):
    """FR-043, SC-014 — byte a byte.

    Distinguir entregaria a quem está adivinhando a informação de que um
    palpite chegou perto.
    """
    client.force_login(cliente)
    endereco = _gerar(client, ingresso).json()["endereco"]
    _revogar(client, ingresso)
    token_morto = endereco.rsplit("/", 1)[-1]

    revogado = client.get(_url_publica(token_morto))
    inventado = client.get(_url_publica("eu-inventei-isso-aqui-agora-mesmo"))

    assert revogado.status_code == inventado.status_code == 404
    assert revogado.content == inventado.content


@pytest.mark.django_db
def test_a_frase_do_link_morto_e_escrita_para_gente(client):
    """FR-052 — nunca "Não encontrado".

    Quem recebeu o ingresso de um amigo concluiria que o site quebrou.
    """
    corpo = client.get(_url_publica("qualquer-coisa")).json()

    assert corpo["detail"] == (
        "Este link não vale mais. Peça um novo a quem enviou o ingresso."
    )


# --- US7: posse ------------------------------------------------------------


@pytest.mark.django_db
def test_outro_cliente_recebe_404_em_abrir_gerar_e_revogar(
    client, cliente, outro_cliente, ingresso
):
    """FR-048 — `404`, nunca `403`.

    Um `403` confirmaria que aquele `public_id` existe, e `public_id` é o
    valor que vai dentro do código assinado do QR.
    """
    client.force_login(outro_cliente)

    detalhe = client.get(reverse("screening:ticket-detail", args=[ingresso.public_id]))
    gerar = _gerar(client, ingresso)
    revogar = _revogar(client, ingresso)

    assert detalhe.status_code == gerar.status_code == revogar.status_code == 404


@pytest.mark.django_db
def test_gerar_link_alheio_nao_cria_link_nenhum(client, outro_cliente, ingresso):
    """US7-3 — a recusa não pode deixar rastro."""
    client.force_login(outro_cliente)

    _gerar(client, ingresso)

    assert TicketShareLink.objects.count() == 0


@pytest.mark.django_db
def test_revogar_link_alheio_deixa_o_link_ativo(client, cliente, outro_cliente, ingresso):
    """US7-4 — o dono continua com o link dele."""
    client.force_login(cliente)
    endereco = _gerar(client, ingresso).json()["endereco"]

    client.force_login(outro_cliente)
    _revogar(client, ingresso)

    token = endereco.rsplit("/", 1)[-1]
    assert client.get(_url_publica(token)).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("papel", ["organizer", "gate"])
def test_organizador_e_portaria_recebem_403_nas_tres_operacoes(client, ingresso, papel):
    """FR-049 — `403` por papel, não `404`.

    A ordem importa: a permissão recusa ANTES de a posse ser consultada, então
    eles nunca chegam ao ponto em que o `404` esconderia a existência.
    """
    usuario = User.objects.create_user(
        username=f"user_{papel}", password=SENHA, role=papel
    )
    client.force_login(usuario)

    for resposta in (
        client.get(reverse("screening:ticket-detail", args=[ingresso.public_id])),
        _gerar(client, ingresso),
        _revogar(client, ingresso),
    ):
        assert resposta.status_code == 403
        assert resposta.json()["detail"] == "Apenas clientes têm ingressos."


@pytest.mark.django_db
def test_visitante_recebe_401_nas_tres_operacoes(client, ingresso):
    """FR-051."""
    for resposta in (
        client.get(reverse("screening:ticket-detail", args=[ingresso.public_id])),
        _gerar(client, ingresso),
        _revogar(client, ingresso),
    ):
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "Entre para ver seus ingressos."


@pytest.mark.django_db
def test_pagina_publica_nao_exige_sessao(client, cliente, ingresso):
    """FR-036 — sem conta, sem convite para entrar."""
    client.force_login(cliente)
    endereco = _gerar(client, ingresso).json()["endereco"]
    token = endereco.rsplit("/", 1)[-1]
    client.logout()

    resposta = client.get(_url_publica(token))

    assert resposta.status_code == 200
    assert resposta.json()["filme"] == "A Odisseia"
