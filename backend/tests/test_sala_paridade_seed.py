"""O painel e o seed produzem o MESMO mapa de sala — SC-006, FR-017.

UMA DAS TRÊS PROVAS DE RECORTE DA 013, e a que a spec nomeia como a armadilha
da feature: a geometria da sala já existia dentro de `seed_demo`, e escrevê-la
de novo no painel criaria duas verdades sobre onde ficam os lugares de
acessibilidade. A segunda diverge da primeira na primeira correção.

Este arquivo compara LUGAR A LUGAR — fileira, número e tipo — o que os dois
caminhos produzem. Enquanto os dois chamarem `services/salas.py`, ele passa
por construção; no dia em que alguém copiar a regra para um dos lados, é ele
que acusa.

E ELE NÃO PODE SER "SIMPLIFICADO" PARA COMPARAR SÓ A CONTAGEM: contar lugares
não vê a diferença que importa, que é qual deles é de acessibilidade.
"""

import pytest
from django.conf import settings

from apps.catalog.management.commands.seed_demo import Command as SeedDemo
from apps.screening.models import Room, Seat
from apps.screening.services import salas


def _mapa(room):
    """(fileira, número, tipo) de cada lugar, na ordem de leitura."""
    return [
        (s.row, s.number, s.kind)
        for s in room.seats.order_by("row", "number")
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("capacidade", [1, 3, 10, 40, 45, 60, 260])
def test_o_painel_e_o_seed_geram_o_mesmo_mapa(capacidade):
    """A prova, para capacidades que exercitam cada caso da geometria.

    45 é a que mais importa: quatro fileiras cheias e uma quinta com cinco
    lugares — a última incompleta, com a acessibilidade dentro dela.
    """
    pelo_painel = Room.objects.create(name="Pelo painel", capacity=capacidade)
    salas.gerar_assentos(pelo_painel)

    pelo_seed = Room.objects.create(name="Pelo seed", capacity=capacidade)
    SeedDemo()._seed_seats([pelo_seed])

    assert _mapa(pelo_painel) == _mapa(pelo_seed)


@pytest.mark.django_db
def test_a_ultima_fileira_fica_incompleta_sem_inventar_lugar():
    """Capacidade que não fecha a fileira não ganha lugar que a sala não tem."""
    sala = Room.objects.create(name="Sala 45", capacity=45)
    salas.gerar_assentos(sala)

    assert sala.seats.count() == 45
    assert sala.seats.filter(row="E").count() == 5
    assert sala.seats.filter(row="F").count() == 0


@pytest.mark.django_db
def test_a_acessibilidade_fica_nos_ultimos_lugares_da_ultima_fileira():
    """A convenção de sala real: é onde cabe cadeira de rodas sem obstruir."""
    sala = Room.objects.create(name="Sala 45", capacity=45)
    salas.gerar_assentos(sala)

    acessiveis = list(
        sala.seats.filter(kind=Seat.Kind.ACCESSIBLE).order_by("number")
    )

    assert len(acessiveis) == settings.ACCESSIBLE_SEATS_PER_ROOM
    assert {s.row for s in acessiveis} == {"E"}
    assert [s.number for s in acessiveis] == [3, 4, 5]


@pytest.mark.django_db
def test_sala_menor_que_a_cota_vira_toda_acessivel_e_nao_falha():
    """Edge case da spec — a criação não pode quebrar por sala minúscula.

    É o `min(...)` que morava numa linha só do seed, e é exatamente a sutileza
    que uma segunda cópia da regra perderia.
    """
    sala = Room.objects.create(name="Salinha", capacity=2)
    salas.gerar_assentos(sala)

    assert sala.seats.count() == 2
    assert sala.seats.filter(kind=Seat.Kind.ACCESSIBLE).count() == 2


@pytest.mark.django_db
def test_cota_zero_nao_marca_a_fileira_inteira():
    """`lista[-0:]` é a lista INTEIRA — a guarda contra a fatia traiçoeira.

    Sem ela, pedir zero lugares de acessibilidade marcaria a última fileira
    toda, que é o oposto do pedido. A fixture `make_seats(acessiveis=0)` dos
    testes de reserva depende deste comportamento.
    """
    posicoes = salas.posicoes_da_sala(20)

    assert salas.lugares_acessiveis(posicoes, cota=0) == set()


@pytest.mark.django_db
def test_a_geometria_trunca_no_teto_em_vez_de_estourar():
    """A fronteira que a extração NÃO podia apagar (R1).

    `posicoes_da_sala` é geometria pura e trunca, como o seed sempre fez. A
    RECUSA de capacidade acima do teto é validação de entrada e mora no
    serializer — se ela tivesse descido para cá, uma sala do cenário criada
    acima do teto passaria a quebrar o seed.
    """
    posicoes = salas.posicoes_da_sala(10_000)

    assert len(posicoes) == salas.teto_de_capacidade()
    assert posicoes[-1][0] == "Z"
