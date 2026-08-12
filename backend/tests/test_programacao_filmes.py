"""Filmes do painel — catálogo local (US2) e TMDb (US3).

A fronteira que este arquivo protege: o catálogo LOCAL é o que mantém a
promessa de FR-014 — com o TMDb fora do ar, programar continua funcionando.
Nenhuma das respostas de catálogo local pode acabar dependendo da API externa.
"""

import pytest

from apps.screening.models import Screening

FILMES = "/api/v1/programacao/filmes/"


@pytest.mark.django_db
def test_catalogo_local_vazio_devolve_200(painel):
    assert painel.get(FILMES).json() == {"count": 0, "results": []}


@pytest.mark.django_db
def test_catalogo_local_traz_o_que_o_painel_precisa(painel, make_movie):
    """Reconhecer o filme e escolher — nada além disso (contrato §GET filmes)."""
    make_movie(title="A Odisseia", runtime_minutes=166)

    linha = painel.get(FILMES).json()["results"][0]

    assert linha["titulo"] == "A Odisseia"
    assert linha["duracao_min"] == 166
    assert "tmdb_id" in linha
    assert linha["poster_url"].endswith("/poster.jpg")
    # Sem sinopse, sem gêneros, sem trailers: a tela lista o catálogo inteiro
    # para bater o olho, e cada campo a mais é peso.
    assert "sinopse" not in linha


@pytest.mark.django_db
def test_conta_sessoes_nao_canceladas_por_filme(
    painel, make_movie, make_screening, room
):
    """A contagem existe para dizer o que já tem grade e o que não tem.

    Canceladas ficam de fora: elas não estão programadas, e contá-las faria um
    filme sem nenhuma sessão viva parecer programado.
    """
    filme = make_movie()
    make_screening(filme, hours_from_now=5)
    make_screening(filme, hours_from_now=9)
    make_screening(filme, hours_from_now=13, status=Screening.Status.CANCELLED)

    assert painel.get(FILMES).json()["results"][0]["sessoes"] == 2


@pytest.mark.django_db
def test_lista_filme_sem_sessao_nenhuma(painel, make_movie):
    """A pergunta aqui é "para qual filme dá para programar?", não "o que está
    em cartaz?".

    Reusar um filtro de vitrine esconderia justamente o filme que ainda não tem
    grade — que é o que o organizador veio programar.
    """
    make_movie(title="Sem grade ainda")

    corpo = painel.get(FILMES).json()

    assert corpo["count"] == 1
    assert corpo["results"][0]["sessoes"] == 0


@pytest.mark.django_db
def test_catalogo_local_nao_faz_uma_consulta_por_filme(
    painel, make_movie, django_assert_max_num_queries
):
    for indice in range(12):
        make_movie(title=f"Filme {indice}")

    with django_assert_max_num_queries(5):
        assert painel.get(FILMES).json()["count"] == 12
