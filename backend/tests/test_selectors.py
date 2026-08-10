"""Regra de elegibilidade ao destaque (FR-002, R6).

Sustenta o SC-004: 100% dos destaques levam a uma sessão comprável.
"""

import pytest

from apps.catalog.selectors import get_highlighted_movies
from apps.screening.models import Room, Screening


@pytest.mark.django_db
def test_catalogo_vazio_retorna_lista_vazia():
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_filme_sem_sessao_nao_e_destacado(make_movie):
    make_movie("Sem Sessão")
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_sessao_passada_nao_torna_filme_elegivel(make_movie, make_screening):
    movie = make_movie("Já Passou")
    make_screening(movie, hours_from_now=-2)
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_sessao_em_rascunho_nao_torna_filme_elegivel(make_movie, make_screening):
    movie = make_movie("Rascunho")
    make_screening(movie, status=Screening.Status.DRAFT)
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_sessao_cancelada_nao_torna_filme_elegivel(make_movie, make_screening):
    movie = make_movie("Cancelado")
    make_screening(movie, status=Screening.Status.CANCELLED)
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_filme_inativo_nao_e_destacado(make_movie, make_screening):
    movie = make_movie("Inativo", is_active=False)
    make_screening(movie)
    assert list(get_highlighted_movies()) == []


@pytest.mark.django_db
def test_ordena_pela_sessao_mais_proxima(make_movie, make_screening):
    tarde = make_movie("Tarde")
    cedo = make_movie("Cedo")
    make_screening(tarde, hours_from_now=48)
    make_screening(cedo, hours_from_now=6)

    assert [m.title for m in get_highlighted_movies()] == ["Cedo", "Tarde"]


@pytest.mark.django_db
def test_sessao_passada_nao_puxa_filme_para_o_topo(make_movie, make_screening):
    """O annotate precisa usar o mesmo predicado do filtro.

    Sem isso, uma sessão antiga daria a este filme o menor `next_screening_at`
    e ele apareceria primeiro sem ter sessão comprável mais cedo.
    """
    antigo = make_movie("Com Sessão Antiga")
    outro = make_movie("Outro")

    sala_extra = Room.objects.create(name="Sala 9", capacity=30)
    make_screening(antigo, hours_from_now=-100, room_obj=sala_extra)
    make_screening(antigo, hours_from_now=72)
    make_screening(outro, hours_from_now=10)

    assert [m.title for m in get_highlighted_movies()] == ["Outro", "Com Sessão Antiga"]


@pytest.mark.django_db
def test_limita_em_cinco_destaques(make_movie, make_screening):
    for i in range(8):
        movie = make_movie(f"Filme {i}")
        make_screening(movie, hours_from_now=i + 1)

    assert len(get_highlighted_movies()) == 5


@pytest.mark.django_db
def test_filme_com_varias_sessoes_aparece_uma_vez(make_movie, make_screening):
    movie = make_movie("Muitas Sessões")
    for hours in (5, 10, 15):
        make_screening(movie, hours_from_now=hours)

    highlights = list(get_highlighted_movies())
    assert len(highlights) == 1
    assert highlights[0].title == "Muitas Sessões"


@pytest.mark.django_db
def test_desempate_por_titulo_e_deterministico(make_movie, make_screening):
    """Duas sessões no mesmo horário não podem gerar ordem instável."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.screening.models import Screening as S

    momento = timezone.now() + timedelta(hours=12)
    zebra = make_movie("Zebra")
    alfa = make_movie("Alfa")

    sala_a = Room.objects.create(name="Sala A", capacity=20)
    sala_b = Room.objects.create(name="Sala B", capacity=20)
    S.objects.create(
        movie=zebra, room=sala_a, starts_at=momento, price=10, status=S.Status.PUBLISHED
    )
    S.objects.create(
        movie=alfa, room=sala_b, starts_at=momento, price=10, status=S.Status.PUBLISHED
    )

    assert [m.title for m in get_highlighted_movies()] == ["Alfa", "Zebra"]
