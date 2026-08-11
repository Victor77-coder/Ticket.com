"""Contrato do endpoint público de busca.

Cobre os 13 casos tabelados em
`specs/002-site-header-navigation/contracts/search-api.md`.

O teste de vazamento é o GATE DO PRINCÍPIO IV: a resposta é pública e não
pode carregar nenhum dado de gestão do organizador.
"""

import json

import pytest
from django.urls import reverse

URL = "catalog:busca"


def buscar(client, **params):
    return client.get(reverse(URL), params)


# --- 1 a 3: regras de correspondência -------------------------------------


@pytest.mark.django_db
def test_encontra_por_trecho_no_meio_do_titulo(client, make_movie):
    """Caso 1 — correspondência parcial, não só título completo (FR-008)."""
    make_movie("Matrix Reloaded")

    payload = buscar(client, q="trix").json()

    assert [item["title"] for item in payload["results"]] == ["Matrix Reloaded"]


@pytest.mark.django_db
@pytest.mark.parametrize("termo", ["cacador", "caçador", "CACADOR", "Caçador"])
def test_ignora_acento_e_caixa(client, make_movie, termo):
    """Casos 2 e 3 — as quatro grafias precisam achar o mesmo filme."""
    make_movie("O Caçador de Pipas")

    payload = buscar(client, q=termo).json()

    assert [item["title"] for item in payload["results"]] == ["O Caçador de Pipas"]


@pytest.mark.django_db
def test_acento_no_cadastro_e_termo_sem_acento_valem_nos_dois_sentidos(client, make_movie):
    """A normalização vale para os dois lados, não só para o termo."""
    make_movie("Ilusão")
    make_movie("Ilusao Perfeita")

    titulos = [item["title"] for item in buscar(client, q="ilusão").json()["results"]]

    assert set(titulos) == {"Ilusão", "Ilusao Perfeita"}


# --- 4: termo vazio --------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("termo", ["", "   ", "\t"])
def test_termo_vazio_responde_200_com_lista_vazia(client, make_movie, termo):
    """Caso 4 — campo vazio é o estado inicial, não erro do cliente."""
    make_movie("Qualquer Filme")

    response = buscar(client, q=termo)

    assert response.status_code == 200
    assert response.json() == {"termo": "", "count": 0, "truncated": False, "results": []}


@pytest.mark.django_db
def test_parametro_ausente_responde_200_com_lista_vazia(client, make_movie):
    make_movie("Qualquer Filme")

    response = client.get(reverse(URL))

    assert response.status_code == 200
    assert response.json()["results"] == []


# --- 5 e 6: limite e truncamento ------------------------------------------


@pytest.mark.django_db
def test_trunca_quando_ha_mais_correspondencias_que_o_limite(client, make_movie):
    """Caso 5 — FR-011."""
    for i in range(9):
        make_movie(f"Aventura {i}")

    payload = buscar(client, q="aventura", limite=6).json()

    assert payload["count"] == 6
    assert len(payload["results"]) == 6
    assert payload["truncated"] is True


@pytest.mark.django_db
def test_nao_trunca_quando_o_total_bate_com_o_limite(client, make_movie):
    """Caso 6 — a fronteira exata, onde um erro de off-by-one apareceria."""
    for i in range(6):
        make_movie(f"Aventura {i}")

    payload = buscar(client, q="aventura", limite=6).json()

    assert payload["count"] == 6
    assert payload["truncated"] is False


# --- 7 e 8: quem entra e quem fica de fora --------------------------------


@pytest.mark.django_db
def test_filme_inativo_nao_aparece(client, make_movie):
    """Caso 7."""
    make_movie("Fora de Cartaz", is_active=False)

    assert buscar(client, q="fora").json()["results"] == []


@pytest.mark.django_db
def test_filme_sem_sessao_publicada_aparece(client, make_movie):
    """Caso 8 — decisão registrada em research.md (R6).

    A busca não esconde o que existe no catálogo. Quem comunica a
    indisponibilidade é a página do filme, não o silêncio da busca.
    """
    make_movie("Sem Sessao Agendada")

    titulos = [item["title"] for item in buscar(client, q="sem sessao").json()["results"]]

    assert titulos == ["Sem Sessao Agendada"]


# --- 9 e 10: os dois gates do Princípio IV --------------------------------


@pytest.mark.django_db
def test_endpoint_e_publico(client, make_movie):
    """Caso 9 — sem autenticação, sem sessão, sem cabeçalho: 200."""
    make_movie("Filme Público")

    assert buscar(client, q="filme").status_code == 200


@pytest.mark.django_db
def test_resposta_tem_exatamente_as_chaves_permitidas(client, make_movie):
    """Caso 10 — GATE DO PRINCÍPIO IV.

    Compara o conjunto de chaves com o conjunto permitido em vez de conferir
    campo a campo: assim um campo novo acrescentado por descuido quebra o
    teste em vez de passar despercebido.
    """
    make_movie("Duna", release_date="2021-10-21")

    payload = buscar(client, q="duna").json()

    assert set(payload) == {"termo", "count", "truncated", "results"}

    item = payload["results"][0]
    assert set(item) == {"slug", "title", "poster_url", "year", "movie_path"}
    assert item["year"] == 2021
    assert item["movie_path"] == f"/filmes/{item['slug']}"
    assert item["poster_url"].startswith("https://image.tmdb.org/t/p/w500")


@pytest.mark.django_db
def test_nao_vaza_dado_de_gestao(client, make_movie, make_screening):
    """GATE DO PRINCÍPIO IV — varredura do payload inteiro."""
    movie = make_movie("Qualquer Filme")
    make_screening(movie)

    raw = json.dumps(buscar(client, q="qualquer").json())

    proibidos = [
        "status",
        "capacity",
        "seats_taken",
        "price",
        "cost",
        "room",
        "screening",
        "username",
        "email",
        "password",
        "tmdb_id",
        "synced_at",
    ]
    vazados = [campo for campo in proibidos if campo in raw]
    assert not vazados, f"resposta pública vazou dado de gestão: {vazados}"


# --- 11: ordenação ---------------------------------------------------------


@pytest.mark.django_db
def test_prefixo_vem_antes_de_quem_apenas_contem(client, make_movie):
    """Caso 11 — quem digita 'mat' espera 'Matrix' antes de 'Chamado da Mata'."""
    make_movie("Chamado da Mata")
    make_movie("Matrix")

    titulos = [item["title"] for item in buscar(client, q="mat").json()["results"]]

    assert titulos == ["Matrix", "Chamado da Mata"]


@pytest.mark.django_db
def test_desempate_por_titulo_e_deterministico(client, make_movie):
    """Sem desempate estável o teste ficaria instável conforme a ordem do banco."""
    make_movie("Aventura Zulu")
    make_movie("Aventura Alfa")
    make_movie("Aventura Meio")

    titulos = [item["title"] for item in buscar(client, q="aventura").json()["results"]]

    assert titulos == ["Aventura Alfa", "Aventura Meio", "Aventura Zulu"]


# --- 12 e 13: entradas fora da faixa --------------------------------------


@pytest.mark.django_db
def test_termo_muito_longo_e_truncado_sem_erro(client, make_movie):
    """Caso 12 — entrada absurda não pode virar 500."""
    make_movie("Filme Curto")

    response = buscar(client, q="a" * 500)

    assert response.status_code == 200
    assert len(response.json()["termo"]) <= 80


@pytest.mark.django_db
@pytest.mark.parametrize("limite,esperado", [("0", 1), ("999", 20), ("abc", 6), ("-5", 1)])
def test_limite_fora_da_faixa_e_ajustado_sem_erro(client, make_movie, limite, esperado):
    """Caso 13 — limite inválido é fixado na faixa, nunca 400."""
    for i in range(25):
        make_movie(f"Aventura {i:02d}")

    payload = buscar(client, q="aventura", limite=limite).json()

    assert payload["count"] == esperado


# --- resiliência -----------------------------------------------------------


@pytest.mark.django_db
def test_responde_sem_chave_do_tmdb(client, settings, make_movie):
    """Princípio VII / SC-009 — a busca lê apenas o PostgreSQL."""
    settings.TMDB_API_KEY = ""
    make_movie("Funciona Offline")

    payload = buscar(client, q="offline").json()

    assert [item["title"] for item in payload["results"]] == ["Funciona Offline"]


@pytest.mark.django_db
def test_metodo_nao_permitido(client):
    assert client.post(reverse(URL), {"q": "x"}).status_code == 405
