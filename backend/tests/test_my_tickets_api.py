"""Contrato da área "Meus ingressos".

Os dois primeiros testes deste arquivo são a defesa contra a armadilha
herdada (R10), e é por eles que o arquivo começa.

Toda consulta de sessão escrita da 001 até a 008 passa por
`Screening.objects.sellable()`, que é `published()` E `starts_at > now()`. É o
filtro certo para ESTOQUE — o que ainda dá para comprar — e o errado para
HISTÓRICO. Usá-lo aqui:

  - esvaziaria o grupo "já aconteceram" para sempre, porque toda sessão que
    já começou deixa de ser vendável;
  - faria sumir o ingresso de sessão CANCELADA, que é o pior caso: some
    justamente aquele sobre o qual o cliente precisa de explicação.

Nenhuma constraint pega isso e nenhum teste pega por acidente. A linha errada
é mais parecida com o resto do projeto do que a certa — por isso a guarda é
explícita e vem primeiro.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

SENHA = "desafio2026"


def _listar(client):
    return client.get(reverse("screening:my-tickets"))


# --- A armadilha herdada (R10) ---------------------------------------------


@pytest.mark.django_db
def test_ingresso_de_sessao_ja_iniciada_continua_na_lista(client, tres_cenarios):
    """FR-009 — passado não é escondido, é ordenado depois.

    Se este teste falhar com o grupo `passados` vazio, alguma consulta está
    usando `sellable()`.
    """
    client.force_login(tres_cenarios["cliente"])

    corpo = _listar(client).json()

    titulos = [i["filme"] for i in corpo["passados"]]
    assert "Filme iniciada" in titulos


@pytest.mark.django_db
def test_ingresso_de_sessao_cancelada_continua_na_lista_e_avisa(client, tres_cenarios):
    """FR-011 — o pior caso da armadilha.

    Uma sessão cancelada não é vendável, então `sellable()` a exclui. Sumir
    com este ingresso é sumir com o único que precisa de explicação.
    """
    client.force_login(tres_cenarios["cliente"])

    corpo = _listar(client).json()

    todos = corpo["futuros"] + corpo["passados"]
    cancelado = [i for i in todos if i["filme"] == "Filme cancelada"]

    assert len(cancelado) == 1
    assert cancelado[0]["sessao_cancelada"] is True


@pytest.mark.django_db
def test_sessao_cancelada_futura_continua_no_grupo_dos_futuros(client, tres_cenarios):
    """Cancelamento e horário são fatos ORTOGONAIS.

    A sessão cancelada da fixture ainda não começou. Ela pertence ao grupo
    dos futuros e carrega o aviso — fundir as duas coisas num campo só
    obrigaria o front a desfazer a fusão.
    """
    client.force_login(tres_cenarios["cliente"])

    corpo = _listar(client).json()

    assert "Filme cancelada" in [i["filme"] for i in corpo["futuros"]]


# --- US1: a lista ----------------------------------------------------------


@pytest.fixture
def cliente(db):
    return User.objects.create_user(
        username="cliente1", password=SENHA, role=User.Role.CUSTOMER
    )


@pytest.fixture
def compra_de_dois(make_movie, make_screening, seats, room, cliente, make_tickets):
    """Uma compra de DOIS lugares numa sessão futura."""
    sessao = make_screening(make_movie("A Odisseia"), hours_from_now=24)
    lugares = list(room.seats.filter(kind="common")[:2])
    return sessao, make_tickets(sessao, cliente, lugares, minutes_left=10)


@pytest.mark.django_db
def test_lista_traz_um_item_por_lugar_comprado(client, cliente, compra_de_dois):
    """FR-004 — um ingresso por LUGAR, nunca um por compra."""
    client.force_login(cliente)

    corpo = _listar(client).json()

    assert len(corpo["futuros"]) == 2
    assert corpo["passados"] == []

    lugares = {(i["assento"]["fileira"], i["assento"]["numero"]) for i in corpo["futuros"]}
    assert len(lugares) == 2


@pytest.mark.django_db
def test_cada_item_identifica_filme_sessao_sala_e_lugar(client, cliente, compra_de_dois):
    """FR-005 — sem exigir interação nenhuma."""
    client.force_login(cliente)

    item = _listar(client).json()["futuros"][0]

    assert item["filme"] == "A Odisseia"
    assert item["sessao"]
    assert item["sala"]
    assert item["assento"]["fileira"]
    assert item["grupo"] == "futuro"


@pytest.mark.django_db
def test_proxima_sessao_primeiro_e_passado_mais_recente_primeiro(
    client, cliente, make_movie, make_screening, make_seats, make_tickets
):
    """FR-007, FR-008, SC-002 — as duas ordenações, em direções opostas.

    Este é o teste que pega a herança de `Ticket.Meta.ordering`: se a lista
    sair ordenada por poltrona em vez de por horário, as asserções abaixo
    quebram.
    """
    from apps.screening.models import Room

    horas = {"daqui_3h": 3, "daqui_50h": 50, "ha_2h": -2, "ha_40h": -40}
    for nome, delta in horas.items():
        sala = Room.objects.create(name=f"Sala {nome}", capacity=10)
        lugares = make_seats(sala, acessiveis=0)
        sessao = make_screening(
            make_movie(title=nome), hours_from_now=delta, room_obj=sala
        )
        make_tickets(sessao, cliente, lugares[:1])

    client.force_login(cliente)
    corpo = _listar(client).json()

    assert [i["filme"] for i in corpo["futuros"]] == ["daqui_3h", "daqui_50h"]
    assert [i["filme"] for i in corpo["passados"]] == ["ha_2h", "ha_40h"]


@pytest.mark.django_db
def test_lista_nao_faz_uma_consulta_por_ingresso(
    client, cliente, make_movie, make_screening, make_seats, make_tickets,
    django_assert_num_queries,
):
    """R11 — o teste falha se o `select_related` do selector for removido.

    Doze ingressos no caminho ingênuo dariam dezenas de consultas: o
    serializer toca filme, sala, sessão e assento de cada linha.
    """
    from apps.screening.models import Room

    sala = Room.objects.create(name="Sala cheia", capacity=12)
    lugares = make_seats(sala, acessiveis=0)
    sessao = make_screening(make_movie("Lotação"), hours_from_now=24, room_obj=sala)
    make_tickets(sessao, cliente, lugares, minutes_left=10)

    client.force_login(cliente)

    # Sessão, usuário, e uma consulta por GRUPO. O número não pode crescer
    # com a quantidade de ingressos — é isso que está sendo fixado.
    with django_assert_num_queries(4):
        resposta = _listar(client)

    assert len(resposta.json()["futuros"]) == 12


# --- US2: o estado vazio ---------------------------------------------------


@pytest.mark.django_db
def test_cliente_sem_ingressos_recebe_200_com_grupos_vazios(client, cliente):
    """FR-012 — nunca `404` e nunca `204`.

    O estado vazio é uma TELA escrita para gente, não a ausência de um
    recurso. Um `404` faria o front tratar "nunca comprou" como erro.
    """
    client.force_login(cliente)

    resposta = _listar(client)

    assert resposta.status_code == 200
    assert resposta.json() == {"futuros": [], "passados": []}


# --- US7: papéis e posse ---------------------------------------------------


@pytest.mark.django_db
def test_cliente_ve_apenas_os_proprios_ingressos(client, compra_de_dois, tres_cenarios):
    """FR-047 — `cliente1` tem dois ingressos; o dono da outra fixture, três."""
    outro = User.objects.create_user(
        username="cliente2", password=SENHA, role=User.Role.CUSTOMER
    )
    client.force_login(outro)

    corpo = _listar(client).json()

    assert corpo == {"futuros": [], "passados": []}


@pytest.mark.django_db
@pytest.mark.parametrize("papel", ["organizer", "gate"])
def test_organizador_e_portaria_recebem_403_por_papel(client, papel):
    """FR-049 — `403`, nunca `401`.

    Eles ENTRARAM, só não têm ingressos. Um `401` os mandaria à tela de
    entrada, que é caminho sem saída: entrar de novo não muda o papel.
    """
    usuario = User.objects.create_user(
        username=f"user_{papel}", password=SENHA, role=papel
    )
    client.force_login(usuario)

    resposta = _listar(client)

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Apenas clientes têm ingressos."


@pytest.mark.django_db
def test_visitante_recebe_401_e_nenhum_dado_de_ingresso(client, compra_de_dois):
    """FR-051 — e a resposta não vaza nada sobre os ingressos que existem."""
    resposta = _listar(client)

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Entre para ver seus ingressos."}
    assert "A Odisseia" not in resposta.content.decode()
