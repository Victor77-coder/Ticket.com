"""Contrato do mapa de assentos.

Dois testes carregam mais peso que os outros:

  - o de vazamento, gate do Princípio IV — o mapa diz "tomado", nunca *por
    quem*;
  - o de que rascunho, cancelada, passada e inexistente convergem para a
    mesma 404, porque distinguir revelaria a grade interna de programação.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.screening.models import Screening


@pytest.fixture
def sessao(make_movie, make_screening, seats):
    """Sessão vendável numa sala com o mapa já gerado."""
    return make_screening(make_movie("A Odisseia"))


def _mapa(client, screening):
    return client.get(reverse("screening:seat-map", args=[screening.pk]))


def _assentos(corpo):
    return [a for fileira in corpo["fileiras"] for a in fileira["assentos"]]


# --- Composição do mapa (FR-004, FR-005) -----------------------------------


@pytest.mark.django_db
def test_mapa_traz_todos_os_lugares_da_sala(client, sessao):
    corpo = _mapa(client, sessao).json()

    assert len(_assentos(corpo)) == sessao.room.capacity


@pytest.mark.django_db
def test_fileiras_vem_na_ordem_de_leitura(client, sessao):
    corpo = _mapa(client, sessao).json()

    letras = [f["letra"] for f in corpo["fileiras"]]
    assert letras == sorted(letras)
    assert letras == ["A", "B", "C", "D", "E", "F"]

    for fileira in corpo["fileiras"]:
        numeros = [a["numero"] for a in fileira["assentos"]]
        assert numeros == sorted(numeros)


@pytest.mark.django_db
def test_mapa_identifica_a_sessao_e_a_sala(client, sessao):
    corpo = _mapa(client, sessao).json()

    assert corpo["sala"]["nome"] == sessao.room.name
    assert corpo["filme"]["titulo"] == sessao.movie.title
    assert corpo["filme"]["slug"] == sessao.movie.slug
    assert corpo["limite_por_reserva"] == 6


# --- Situação e tipo são campos distintos (contrato) -----------------------


@pytest.mark.django_db
def test_situacao_so_assume_livre_ou_tomado(client, sessao, make_user, make_reservation):
    """Selecionado é estado do navegador e acessibilidade é tipo, não situação.

    Colapsar os quatro estados num campo só obrigaria o front a desfazer a
    fusão — e o servidor não tem como saber o que alguém selecionou, porque
    seleção não existe no banco até virar reserva.
    """
    make_reservation(sessao, make_user(), list(sessao.room.seats.all()[:2]))

    situacoes = {a["situacao"] for a in _assentos(_mapa(client, sessao).json())}

    assert situacoes <= {"livre", "tomado"}
    assert situacoes == {"livre", "tomado"}


@pytest.mark.django_db
def test_acessibilidade_e_tipo_e_pode_estar_livre(client, sessao):
    corpo = _mapa(client, sessao).json()

    acessiveis = [a for a in _assentos(corpo) if a["tipo"] == "acessibilidade"]

    assert len(acessiveis) == 3
    assert all(a["situacao"] == "livre" for a in acessiveis)


@pytest.mark.django_db
def test_lugar_reservado_aparece_como_tomado(client, sessao, make_user, make_reservation):
    tomados = list(sessao.room.seats.all()[:3])
    make_reservation(sessao, make_user(), tomados)

    corpo = _mapa(client, sessao).json()
    ids_tomados = {a["id"] for a in _assentos(corpo) if a["situacao"] == "tomado"}

    assert ids_tomados == {s.pk for s in tomados}


@pytest.mark.django_db
def test_ocupacao_de_outra_sessao_nao_contamina_o_mapa(
    client, sessao, make_movie, make_screening, make_user, make_reservation
):
    """A mesma sala em outro horário é outro estoque."""
    outra = make_screening(make_movie("Outro Filme"), hours_from_now=48)
    make_reservation(outra, make_user(), list(sessao.room.seats.all()[:5]))

    corpo = _mapa(client, sessao).json()

    assert all(a["situacao"] == "livre" for a in _assentos(corpo))


@pytest.mark.django_db
def test_esgotada_e_derivado(client, sessao, make_user, make_reservation):
    livre = _mapa(client, sessao).json()
    assert livre["esgotada"] is False

    comuns = list(sessao.room.seats.exclude(kind="accessible"))
    make_reservation(sessao, make_user(), comuns)

    assert _mapa(client, sessao).json()["esgotada"] is True


# --- Acesso (FR-002, FR-003, FR-010) ---------------------------------------


@pytest.mark.django_db
def test_mapa_e_publico(client, sessao):
    """Ver onde há lugar não exige conta.

    Exigir entrada para olhar afastaria o visitante antes de ele ter motivo
    para criar conta (R10).
    """
    assert _mapa(client, sessao).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cenario",
    ["inexistente", "rascunho", "cancelada", "ja_comecou"],
)
def test_sessao_nao_vendavel_devolve_a_mesma_404(
    client, cenario, make_movie, make_screening, seats
):
    """Uma resposta só para os quatro casos (FR-003).

    Distinguir "não existe" de "está em rascunho" revelaria a grade interna
    de programação a quem não deveria vê-la.
    """
    if cenario == "inexistente":
        resposta = client.get(reverse("screening:seat-map", args=[999999]))
    else:
        filme = make_movie()
        if cenario == "rascunho":
            alvo = make_screening(filme, status=Screening.Status.DRAFT)
        elif cenario == "cancelada":
            alvo = make_screening(filme, status=Screening.Status.CANCELLED)
        else:
            alvo = make_screening(filme, hours_from_now=-2)
        resposta = _mapa(client, alvo)

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Sessão não encontrada."}


# --- Gate do Princípio IV --------------------------------------------------


@pytest.mark.django_db
def test_mapa_nao_revela_quem_ocupou(client, sessao, make_user, make_reservation):
    """O mapa diz "tomado", nunca *por quem*.

    Serializa a resposta inteira e procura qualquer traço do outro cliente:
    nome, identificador, e-mail, o id da reserva ou o prazo dela.
    """
    outro = make_user(username="cliente_alheio")
    reserva = make_reservation(sessao, outro, list(sessao.room.seats.all()[:2]))

    bruto = _mapa(client, sessao).content.decode()

    for proibido in [
        "cliente_alheio",
        outro.email or "@",
        "customer",
        "reservation",
        "expires",
        "expira",
        str(reserva.idempotency_key),
    ]:
        assert proibido not in bruto, f"vazou: {proibido}"

    assert f'"id": {reserva.pk}' not in bruto


@pytest.mark.django_db
def test_mapa_nao_expoe_dado_de_gestao(client, sessao):
    bruto = _mapa(client, sessao).content.decode()

    for proibido in ["status", "draft", "published", "created_at", "updated_at"]:
        assert proibido not in bruto, f"vazou dado de gestão: {proibido}"


@pytest.mark.django_db
def test_mapa_nao_expoe_a_capacidade_da_sala(client, sessao):
    """A mesma proibição que `ScreeningSerializer` do catálogo já aplica.

    O rascunho do contrato trazia `sala.capacidade`; foi retirado ao ser
    confrontado com o gate — e não faz falta, porque o cliente recebe todos
    os lugares e conta se quiser.
    """
    corpo = _mapa(client, sessao).json()

    assert "capacidade" not in corpo["sala"]
    assert set(corpo["sala"]) == {"nome"}


# --- Desempenho (R8) -------------------------------------------------------


@pytest.mark.django_db
def test_mapa_nao_faz_uma_consulta_por_assento(
    client, sessao, django_assert_max_num_queries
):
    """Uma consulta por assento daria 60 por mapa.

    O teto é folgado de propósito — o que ele proíbe é o crescimento com o
    número de lugares, não um SELECT a mais.
    """
    with django_assert_max_num_queries(6):
        _mapa(client, sessao)


# --- Expiração (FR-021) ----------------------------------------------------


@pytest.mark.django_db
def test_reserva_vencida_nao_conta_como_ocupacao(
    client, sessao, make_user, make_reservation
):
    """Sem depender de rotina agendada ter passado."""
    make_reservation(
        sessao, make_user(), list(sessao.room.seats.all()[:2]), minutes_left=-1
    )

    corpo = _mapa(client, sessao).json()

    assert all(a["situacao"] == "livre" for a in _assentos(corpo))


@pytest.mark.django_db
def test_reserva_no_limite_do_prazo_ainda_bloqueia(
    client, sessao, make_user, make_reservation
):
    reserva = make_reservation(sessao, make_user(), list(sessao.room.seats.all()[:1]))
    reserva.expires_at = timezone.now() + timedelta(seconds=5)
    reserva.save(update_fields=["expires_at"])

    corpo = _mapa(client, sessao).json()

    assert any(a["situacao"] == "tomado" for a in _assentos(corpo))
