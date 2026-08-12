"""Cenário de demonstração.

O seed nunca teve teste próprio: era verificado rodando o comando. Com regras
de seleção e de **ordem**, passa a merecer — a ordem da lista é o mecanismo
que coloca os três destaques no carrossel, e ela quebra em silêncio (R1).
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.catalog.management.commands.seed_demo import Command
from apps.catalog.models import Movie
from apps.catalog.selectors import get_highlighted_movies, get_sellable_movies
from apps.screening.models import Reservation, ReservedSeat, Room, Screening, Seat

# Os títulos como o TMDb os devolve — o seed procura por fragmento.
CATALOGO = [
    ("A Odisseia", 172),
    ("Homem-Aranha: Um Novo Dia", 143),
    ("Minions & Monstros", 87),
    ("Moana", 115),
    ("Cidade de Deus", 130),
    ("Bacurau", 131),
    ("Central do Brasil", 113),
    ("Tropa de Elite", 115),
    ("O Auto da Compadecida", 104),
    ("Aquarius", 146),
    ("Que Horas Ela Volta?", 112),
    ("O Som ao Redor", 131),
    ("Ainda Estou Aqui", 137),
    ("Pixote", 128),
]


@pytest.fixture
def catalogo(db):
    """Catálogo com os quatro nomeados e preenchimento suficiente."""
    hoje = timezone.localdate()
    filmes = []
    for i, (titulo, duracao) in enumerate(CATALOGO):
        filmes.append(
            Movie.objects.create(
                tmdb_id=7000 + i,
                title=titulo,
                runtime_minutes=duracao,
                backdrop_path=f"/backdrop{i}.jpg",
                poster_path=f"/poster{i}.jpg",
                release_date=hoje - timedelta(days=30 + i),
            )
        )
    return filmes


def _semear():
    saida = StringIO()
    call_command("seed_demo", stdout=saida, stderr=saida)
    return saida.getvalue()


def _titulos_do_carrossel():
    return [m.title for m in get_highlighted_movies()]


def _titulos_a_venda():
    return [m.title for m in get_sellable_movies()]


# --- Filmes nomeados (FR-004) ---------------------------------------------


@pytest.mark.django_db
def test_os_quatro_nomeados_recebem_sessao(catalogo):
    _semear()

    a_venda = _titulos_a_venda()

    for esperado in ["A Odisseia", "Homem-Aranha", "Minions", "Moana"]:
        assert any(esperado in t for t in a_venda), f"{esperado} ficou sem sessão"


@pytest.mark.django_db
def test_sessoes_dos_nomeados_sao_publicadas_e_futuras(catalogo):
    _semear()

    agora = timezone.now()
    for fragmento in ["Odisseia", "Aranha", "Minions", "Moana"]:
        sessoes = Screening.objects.filter(
            movie__title__icontains=fragmento,
            status=Screening.Status.PUBLISHED,
            starts_at__gt=agora,
        )
        assert sessoes.exists(), f"{fragmento} sem sessão publicada e futura"


# --- A ordem é o mecanismo (FR-005, SC-002) -------------------------------


@pytest.mark.django_db
def test_o_carrossel_traz_os_tres_destaques_na_ordem(catalogo):
    """É o mecanismo inteiro da feature.

    A posição na lista do seed define o horário da sessão, e o carrossel
    ordena pela sessão mais próxima. Se alguém reordenar `_pick_movies` — por
    higiene, alfabeticamente —, este teste é o que avisa.
    """
    _semear()

    carrossel = _titulos_do_carrossel()

    assert len(carrossel) == 3
    assert "Odisseia" in carrossel[0]
    assert "Aranha" in carrossel[1]
    assert "Minions" in carrossel[2]


@pytest.mark.django_db
def test_moana_esta_a_venda_mas_fora_do_carrossel(catalogo):
    """FR-006, SC-003."""
    _semear()

    assert any("Moana" in t for t in _titulos_a_venda())
    assert not any("Moana" in t for t in _titulos_do_carrossel())


# --- Volume (FR-007, SC-004) ----------------------------------------------


@pytest.mark.django_db
def test_seed_coloca_a_venda_mais_que_os_nomeados(catalogo):
    _semear()

    assert len(_titulos_a_venda()) > 4


@pytest.mark.django_db
def test_trilha_tem_ao_menos_o_dobro_do_carrossel(catalogo):
    """SC-004: o carrossel precisa parecer um recorte, não a lista inteira."""
    _semear()

    assert len(_titulos_a_venda()) >= 2 * len(_titulos_do_carrossel())


# --- Degradação graciosa (FR-011, SC-006) ---------------------------------


@pytest.mark.django_db
def test_filme_nomeado_ausente_nao_quebra_o_seed(catalogo):
    """Um seed que falha porque um título mudou é pior do que uma vitrine
    com um filme a menos."""
    Movie.objects.filter(title__icontains="Moana").delete()

    saida = _semear()

    assert "Moana" in saida
    # E o resto da vitrine sai normalmente.
    assert len(_titulos_do_carrossel()) == 3


@pytest.mark.django_db
def test_catalogo_vazio_nao_quebra_o_seed(db):
    """O caso mais comum na prática: rodar o seed antes do sync_tmdb."""
    saida = _semear()

    assert _titulos_a_venda() == []
    assert saida  # o comando disse alguma coisa em vez de estourar


@pytest.mark.django_db
def test_seed_informa_quais_nomeados_faltaram(catalogo):
    Movie.objects.filter(title__icontains="Minions").delete()

    saida = _semear()

    assert "Minions" in saida


# --- Idempotência (FR-013, SC-005) ----------------------------------------


@pytest.mark.django_db
def test_duas_execucoes_produzem_a_mesma_vitrine(catalogo):
    _semear()
    primeira = _titulos_do_carrossel()
    sessoes_primeira = Screening.objects.count()

    _semear()
    segunda = _titulos_do_carrossel()

    assert primeira == segunda
    assert Screening.objects.count() == sessoes_primeira


# --- Busca por nome (FR-010, FR-012) --------------------------------------


@pytest.mark.django_db
def test_busca_tolera_acento_caixa_e_sufixo(catalogo):
    """"homem aranha" precisa achar "Homem-Aranha: Um Novo Dia"."""
    _semear()

    carrossel = _titulos_do_carrossel()

    assert "Homem-Aranha: Um Novo Dia" in carrossel
    assert "Minions & Monstros" in carrossel


@pytest.mark.django_db
def test_escolha_e_deterministica_com_titulos_parecidos(catalogo):
    """Dois filmes casando com o mesmo fragmento não podem alternar."""
    hoje = timezone.localdate()
    Movie.objects.create(
        tmdb_id=9500,
        title="Minions: A Origem de Gru",
        runtime_minutes=87,
        backdrop_path="/b.jpg",
        poster_path="/p.jpg",
        release_date=hoje - timedelta(days=500),
    )

    _semear()
    primeira = _titulos_do_carrossel()
    _semear()

    assert primeira == _titulos_do_carrossel()


# --- Usuários semeados (FR-009) -------------------------------------------


@pytest.mark.django_db
def test_seed_continua_criando_os_quatro_usuarios(catalogo):
    from django.contrib.auth import get_user_model

    _semear()

    User = get_user_model()
    for username in ["organizador", "cliente1", "cliente2", "portaria"]:
        assert User.objects.filter(username=username).exists()


# --- Mapa das salas (feature 007) -----------------------------------------


@pytest.mark.django_db
def test_seed_gera_um_lugar_para_cada_unidade_de_capacidade(catalogo):
    _semear()

    for room in Room.objects.all():
        assert room.seats.count() == room.capacity


@pytest.mark.django_db
def test_lugares_ficam_em_fileiras_de_dez_com_letra_por_fileira(catalogo):
    _semear()

    sala = Room.objects.get(name="Sala 1")  # 60 lugares → A a F

    letras = sorted({s.row for s in sala.seats.all()})
    assert letras == ["A", "B", "C", "D", "E", "F"]

    for letra in letras:
        numeros = sorted(s.number for s in sala.seats.filter(row=letra))
        assert numeros == list(range(1, 11))


def test_capacidade_que_nao_fecha_a_fileira_deixa_a_ultima_incompleta():
    """Sala de 45 lugares dá quatro fileiras cheias e uma com cinco.

    O que não pode acontecer é inventar cinco lugares que a sala não tem só
    para a última fileira ficar simétrica.

    Testado direto na regra de posição, e não semeando uma sala: o seed só
    administra as salas que ele mesmo cria (DEMO_ROOMS), e ambas fecham a
    grade exata. Criar uma sala de fora para o teste provaria outra coisa —
    que o seed invade salas alheias, que é justamente o que ele não faz.
    """
    posicoes = Command._posicoes_da_sala(45, por_fileira=10)

    assert len(posicoes) == 45
    assert posicoes[0] == ("A", 1)
    assert posicoes[-1] == ("E", 5)
    assert [p for p in posicoes if p[0] == "E"] == [("E", n) for n in range(1, 6)]
    assert not [p for p in posicoes if p[0] == "F"]


@pytest.mark.django_db
def test_acessibilidade_fica_na_ultima_fileira(catalogo):
    _semear()

    sala = Room.objects.get(name="Sala 1")
    acessiveis = sala.seats.filter(kind=Seat.Kind.ACCESSIBLE)

    assert acessiveis.count() == 3
    assert {s.row for s in acessiveis} == {"F"}
    assert sorted(s.number for s in acessiveis) == [8, 9, 10]


@pytest.mark.django_db
def test_duas_execucoes_nao_duplicam_lugares(catalogo):
    _semear()
    antes = Seat.objects.count()

    _semear()

    assert Seat.objects.count() == antes


@pytest.mark.django_db
def test_seed_refaz_o_cenario_mesmo_com_reserva_existente(catalogo):
    """Reserva viva não pode travar o seed.

    `ReservedSeat.seat` e `Reservation.screening` são PROTECT. Sem apagar as
    reservas antes de refazer a grade e o mapa, a segunda execução estouraria
    `ProtectedError` — e o comando que se diz idempotente falharia na segunda
    vez, justo depois de alguém ter percorrido a demonstração.
    """
    from django.contrib.auth import get_user_model

    _semear()

    sessao = Screening.objects.first()
    assento = sessao.room.seats.first()
    reserva = Reservation.objects.create(
        screening=sessao,
        customer=get_user_model().objects.get(username="cliente1"),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    ReservedSeat.objects.create(reservation=reserva, screening=sessao, seat=assento)

    _semear()

    assert Reservation.objects.count() == 0
    assert ReservedSeat.objects.count() == 0
    assert Seat.objects.count() == 100


def test_seed_refaz_o_cenario_mesmo_com_compra_concluida(catalogo):
    """Ingresso emitido não pode travar o seed — regressão da feature 008.

    A 008 acrescentou `Payment` e `Ticket`, os dois com PROTECT na direção da
    reserva. `Reservation.objects.all().delete()` passou a estourar
    `ProtectedError` assim que alguém concluía uma compra — e o comando que o
    avaliador usa para voltar ao cenário conhecido morria justamente depois de
    a demonstração ter sido percorrida até o fim.

    Foi encontrado rodando o seed durante a implementação, não pela suíte: o
    teste anterior cobre reserva viva, que é um estado que a 007 já produzia, e
    nenhum teste chegava a pagar antes de semear de novo.

    O PROTECT continua certo. Quem tinha de mudar era a ORDEM do reset.
    """
    from django.contrib.auth import get_user_model

    from apps.screening.models import Payment, Ticket

    _semear()

    sessao = Screening.objects.first()
    assento = sessao.room.seats.first()
    reserva = Reservation.objects.create(
        screening=sessao,
        customer=get_user_model().objects.get(username="cliente1"),
        expires_at=timezone.now() + timedelta(minutes=10),
        status=Reservation.Status.PAID,
    )
    ocupacao = ReservedSeat.objects.create(
        reservation=reserva, screening=sessao, seat=assento
    )
    pagamento = Payment.objects.create(
        reservation=reserva,
        status=Payment.Status.APPROVED,
        amount=sessao.price,
        card_last4="4242",
        card_brand="visa",
    )
    Ticket.objects.create(reserved_seat=ocupacao, payment=pagamento)

    _semear()

    assert Ticket.objects.count() == 0
    assert Payment.objects.count() == 0
    assert Reservation.objects.count() == 0
    assert ReservedSeat.objects.count() == 0
    assert Seat.objects.count() == 100
