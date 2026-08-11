"""Contrato das trilhas da home.

Dois testes carregam mais peso: o de vazamento (gate do Princípio IV) e o de
que a trilha Em cartaz só traz filme comprável — que é a promessa que a trilha
faz ao ser chamada de "Em cartaz" num site de ingressos.
"""

import json
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone


@pytest.fixture(autouse=True)
def _limpa_cache():
    cache.clear()
    yield
    cache.clear()


def _trilhas(client):
    return {r["key"]: r for r in client.get(reverse("catalog:home-rows")).json()["rows"]}


# --- Composição ------------------------------------------------------------


@pytest.mark.django_db
def test_catalogo_vazio_responde_200_com_lista_vazia(client):
    response = client.get(reverse("catalog:home-rows"))

    assert response.status_code == 200
    assert response.json() == {"rows": []}


@pytest.mark.django_db
def test_trilha_sem_filmes_e_omitida_do_array(client, make_movie, make_screening):
    """FR-006: omitida, não devolvida vazia.

    Devolver a trilha vazia e esperar que o cliente esconda coloca a regra em
    dois lugares.
    """
    make_screening(make_movie("Comprável"))

    trilhas = _trilhas(client)

    assert "em-cartaz" in trilhas
    assert "em-alta" not in trilhas
    assert "em-breve" not in trilhas


@pytest.mark.django_db
def test_ordem_das_trilhas_e_do_servidor(client, make_movie, make_screening):
    hoje = timezone.localdate()
    make_screening(make_movie("Comprável"))
    make_movie("Em Alta", is_trending=True)
    make_movie("Em Breve", is_upcoming=True, release_date=hoje + timedelta(days=30))

    chaves = [r["key"] for r in client.get(reverse("catalog:home-rows")).json()["rows"]]

    assert chaves == ["em-cartaz", "em-alta", "em-breve"]


@pytest.mark.django_db
def test_filme_em_duas_trilhas_aparece_nas_duas(client, make_movie, make_screening):
    """FR-005: a repetição é aceita e esperada."""
    filme = make_movie("Nos Dois", is_trending=True)
    make_screening(filme)

    trilhas = _trilhas(client)

    assert "Nos Dois" in [m["title"] for m in trilhas["em-cartaz"]["movies"]]
    assert "Nos Dois" in [m["title"] for m in trilhas["em-alta"]["movies"]]


# --- Em cartaz: a promessa da trilha (SC-003) -----------------------------


@pytest.mark.django_db
def test_em_cartaz_so_traz_filme_com_sessao_compravel(client, make_movie, make_screening):
    from apps.screening.models import Screening

    compravel = make_movie("Comprável")
    make_screening(compravel)

    make_screening(make_movie("Já Passou"), hours_from_now=-2)
    make_screening(make_movie("Rascunho"), status=Screening.Status.DRAFT)
    make_screening(make_movie("Cancelado"), status=Screening.Status.CANCELLED)
    make_movie("Sem Sessão")

    titulos = [m["title"] for m in _trilhas(client)["em-cartaz"]["movies"]]

    assert titulos == ["Comprável"]


@pytest.mark.django_db
def test_em_cartaz_nao_tem_o_limite_de_cinco_do_carrossel(client, make_movie, make_screening):
    """A trilha lista todos os compráveis; só o carrossel corta em 5."""
    for i in range(8):
        make_screening(make_movie(f"Filme {i}"), hours_from_now=i + 1)

    assert _trilhas(client)["em-cartaz"]["count"] == 8


# --- Em alta ---------------------------------------------------------------


@pytest.mark.django_db
def test_em_alta_limita_em_nove(client, make_movie):
    """FR-003, SC-002."""
    for i in range(14):
        make_movie(f"Alta {i}", is_trending=True)

    trilha = _trilhas(client)["em-alta"]

    assert trilha["count"] == 9
    assert len(trilha["movies"]) == 9


@pytest.mark.django_db
def test_em_alta_ignora_filme_inativo(client, make_movie):
    make_movie("Inativo", is_trending=True, is_active=False)

    assert "em-alta" not in _trilhas(client)


# --- Em breve: marca E data (R3) ------------------------------------------


@pytest.mark.django_db
def test_em_breve_exclui_filme_ja_estreado(client, make_movie):
    """Só a marca deixaria o filme preso na trilha até o próximo sync."""
    hoje = timezone.localdate()
    make_movie("Já Estreou", is_upcoming=True, release_date=hoje - timedelta(days=10))
    make_movie("Vai Estrear", is_upcoming=True, release_date=hoje + timedelta(days=10))

    titulos = [m["title"] for m in _trilhas(client)["em-breve"]["movies"]]

    assert titulos == ["Vai Estrear"]


@pytest.mark.django_db
def test_em_breve_exige_a_marca_alem_da_data(client, make_movie):
    """Só a data traria todo filme futuro do catálogo."""
    hoje = timezone.localdate()
    make_movie("Futuro Sem Marca", is_upcoming=False, release_date=hoje + timedelta(days=20))

    assert "em-breve" not in _trilhas(client)


@pytest.mark.django_db
def test_em_breve_ordena_da_estreia_mais_proxima(client, make_movie):
    hoje = timezone.localdate()
    make_movie("Distante", is_upcoming=True, release_date=hoje + timedelta(days=90))
    make_movie("Próximo", is_upcoming=True, release_date=hoje + timedelta(days=5))
    make_movie("Médio", is_upcoming=True, release_date=hoje + timedelta(days=30))

    titulos = [m["title"] for m in _trilhas(client)["em-breve"]["movies"]]

    assert titulos == ["Próximo", "Médio", "Distante"]


@pytest.mark.django_db
def test_desempate_por_titulo_e_deterministico(client, make_movie):
    hoje = timezone.localdate()
    estreia = hoje + timedelta(days=15)
    make_movie("Zebra", is_upcoming=True, release_date=estreia)
    make_movie("Alfa", is_upcoming=True, release_date=estreia)

    titulos = [m["title"] for m in _trilhas(client)["em-breve"]["movies"]]

    assert titulos == ["Alfa", "Zebra"]


# --- Contrato do cartão ---------------------------------------------------


@pytest.mark.django_db
def test_cartao_segue_o_contrato(client, make_movie, make_screening):
    make_screening(make_movie("Duna: Parte Dois"))

    cartao = _trilhas(client)["em-cartaz"]["movies"][0]

    assert set(cartao) == {
        "id",
        "slug",
        "title",
        "poster_url",
        "certification_br",
        "runtime_minutes",
        "release_date",
        "movie_path",
    }
    assert cartao["movie_path"] == "/filmes/duna-parte-dois"
    assert cartao["poster_url"].startswith("https://image.tmdb.org/t/p/w500")


@pytest.mark.django_db
def test_cartao_nao_traz_backdrop_nem_trailer(client, make_movie, make_screening):
    """O cartão é vertical e não reproduz nada — enviar os dois seria peso morto."""
    make_screening(make_movie("Qualquer"))

    cartao = _trilhas(client)["em-cartaz"]["movies"][0]

    assert "backdrop_url" not in cartao
    assert "trailer" not in cartao


@pytest.mark.django_db
def test_filme_sem_cartaz_devolve_nulo(client, make_movie, make_screening):
    make_screening(make_movie("Sem Cartaz", poster_path=""))

    assert _trilhas(client)["em-cartaz"]["movies"][0]["poster_url"] is None


# --- Gate do Princípio IV -------------------------------------------------


@pytest.mark.django_db
def test_endpoint_e_publico(client):
    assert client.get(reverse("catalog:home-rows")).status_code == 200


@pytest.mark.django_db
def test_nao_vaza_dado_de_gestao_nem_classificacao(client, make_movie, make_screening):
    """GATE DO PRINCÍPIO IV.

    A classificação entra na lista de proibidos junto com os dados de gestão:
    é mecânica interna, e o cliente recebe a trilha pronta.
    """
    filme = make_movie("Qualquer", is_trending=True, is_upcoming=True)
    make_screening(filme)

    bruto = json.dumps(client.get(reverse("catalog:home-rows")).json())

    proibidos = [
        "status",
        "capacity",
        "seats_taken",
        "cost",
        "username",
        "email",
        "draft",
        "cancelled",
        "is_trending",
        "is_upcoming",
        "catalog_synced_at",
    ]
    vazados = [campo for campo in proibidos if campo in bruto]
    assert not vazados, f"resposta pública vazou: {vazados}"


# --- Resiliência (Princípio VII, SC-004) ----------------------------------


@pytest.mark.django_db
def test_responde_sem_chave_do_tmdb(client, settings, make_movie, make_screening):
    settings.TMDB_API_KEY = ""
    make_screening(make_movie("Funciona Offline", is_trending=True))

    trilhas = _trilhas(client)

    assert trilhas["em-cartaz"]["count"] == 1
    assert trilhas["em-alta"]["count"] == 1


# --- Detalhe do filme ganhou release_date (FR-025) ------------------------


@pytest.mark.django_db
def test_detalhe_do_filme_devolve_release_date(client, make_movie):
    hoje = timezone.localdate()
    filme = make_movie("Estreia Futura", release_date=hoje + timedelta(days=20))

    corpo = client.get(reverse("catalog:movie-detail", args=[filme.slug])).json()

    assert corpo["release_date"] == (hoje + timedelta(days=20)).isoformat()


@pytest.mark.django_db
def test_detalhe_sem_data_devolve_nulo(client, make_movie):
    filme = make_movie("Sem Data", release_date=None)

    assert client.get(reverse("catalog:movie-detail", args=[filme.slug])).json()["release_date"] is None
