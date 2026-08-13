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


# --- Busca no TMDb (US3) --------------------------------------------------

BUSCA = "/api/v1/programacao/filmes/busca/"


def _resultado_tmdb(tmdb_id=693134, titulo="Duna: Parte Dois", ano="2024-02-27"):
    return {
        "id": tmdb_id,
        "title": titulo,
        "release_date": ano,
        "poster_path": "/xyz.jpg",
    }


def _detalhe_tmdb(tmdb_id=693134, titulo="Duna: Parte Dois"):
    """O payload de `movie_detail`, com o que `append_to_response` já traz."""
    return {
        "id": tmdb_id,
        "title": titulo,
        "overview": "Paul Atreides se une aos Fremen.",
        "runtime": 166,
        "release_date": "2024-02-27",
        "poster_path": "/xyz.jpg",
        "backdrop_path": "/abc.jpg",
        "genres": [{"id": 878, "name": "Ficção científica"}],
        "videos": {
            "results": [
                {
                    "key": "abc123",
                    "name": "Trailer oficial",
                    "site": "YouTube",
                    "type": "Trailer",
                    "iso_639_1": "pt",
                    "official": True,
                    "published_at": "2024-01-01T00:00:00.000Z",
                }
            ]
        },
        "release_dates": {
            "results": [
                {
                    "iso_3166_1": "BR",
                    "release_dates": [{"certification": "14", "type": 3}],
                }
            ]
        },
    }


@pytest.fixture
def tmdb_falso(monkeypatch):
    """Um TMDb previsível, para os testes não dependerem da internet.

    O que é trocado é o CLIENTE, e não `sync_movie`: o mapeamento é justamente
    o que a feature promete reusar inteiro, e um duplo dele faria os testes
    passarem sem provar FR-011a.
    """
    from apps.catalog.services import programacao_filmes
    from apps.catalog.services import tmdb_client as modulo

    class ClienteFalso:
        buscas = []
        detalhes = []
        resposta = {"results": [_resultado_tmdb()]}
        detalhe = _detalhe_tmdb()
        falha = None

        def search_movies(self, query, page=1):
            ClienteFalso.buscas.append(query)
            if ClienteFalso.falha:
                raise modulo.TMDBError(ClienteFalso.falha)
            return ClienteFalso.resposta

        def movie_detail(self, tmdb_id):
            ClienteFalso.detalhes.append(tmdb_id)
            if ClienteFalso.falha:
                raise modulo.TMDBError(ClienteFalso.falha)
            return ClienteFalso.detalhe

    ClienteFalso.buscas = []
    ClienteFalso.detalhes = []
    ClienteFalso.falha = None

    monkeypatch.setattr("apps.catalog.views.TMDBClient", ClienteFalso)
    monkeypatch.setattr(programacao_filmes, "TMDBClient", ClienteFalso)
    return ClienteFalso


@pytest.mark.django_db
def test_busca_devolve_resultados_com_marca_do_catalogo(painel, make_movie, tmdb_falso):
    """US3 cenário 1 — cada resultado diz se já está no catálogo local."""
    make_movie(title="Duna: Parte Dois", tmdb_id=693134)

    corpo = painel.get(f"{BUSCA}?q=duna").json()

    assert corpo["termo"] == "duna"
    assert corpo["count"] == 1
    linha = corpo["results"][0]
    assert linha["titulo"] == "Duna: Parte Dois"
    assert linha["ano"] == 2024
    assert linha["ja_no_catalogo"] is True


@pytest.mark.django_db
def test_marca_do_catalogo_sai_em_uma_consulta(painel, tmdb_falso, django_assert_max_num_queries):
    """Uma consulta `__in` para a página inteira, nunca uma por linha."""
    tmdb_falso.resposta = {
        "results": [_resultado_tmdb(tmdb_id=900 + i, titulo=f"Filme {i}") for i in range(20)]
    }

    with django_assert_max_num_queries(5):
        assert painel.get(f"{BUSCA}?q=filme").json()["count"] == 20


@pytest.mark.django_db
def test_termo_vazio_nao_e_erro_e_nao_chama_o_tmdb(painel, tmdb_falso):
    """`200` com lista vazia — a tela abre com o campo em branco."""
    resposta = painel.get(f"{BUSCA}?q=   ")

    assert resposta.status_code == 200
    assert resposta.json() == {"termo": "", "count": 0, "results": []}
    assert tmdb_falso.buscas == []


@pytest.mark.django_db
def test_busca_sem_resultado_devolve_lista_vazia(painel, tmdb_falso):
    """US3 cenário 7 — o estado vazio é da interface, não um erro da API."""
    tmdb_falso.resposta = {"results": []}

    corpo = painel.get(f"{BUSCA}?q=asdfghjkl").json()

    assert corpo["count"] == 0
    assert corpo["termo"] == "asdfghjkl"


@pytest.mark.django_db
def test_tmdb_fora_do_ar_devolve_502_com_a_frase_do_cliente(painel, tmdb_falso):
    """US3 cenário 6 — a frase é a do `TMDBError`, não uma segunda redação."""
    tmdb_falso.falha = "O TMDb não respondeu em 10s. Verifique a conexão e tente novamente."

    resposta = painel.get(f"{BUSCA}?q=duna")

    assert resposta.status_code == 502
    assert "não respondeu em 10s" in resposta.json()["detail"]


@pytest.mark.django_db
def test_o_catalogo_local_continua_de_pe_com_o_tmdb_fora(painel, make_movie, tmdb_falso):
    """FR-014 — a indisponibilidade degrada a busca, e só ela."""
    tmdb_falso.falha = "O TMDb recusou a chave de API."
    make_movie(title="A Odisseia")

    assert painel.get(f"{BUSCA}?q=duna").status_code == 502
    assert painel.get(FILMES).json()["count"] == 1


@pytest.mark.django_db
def test_nenhuma_resposta_carrega_a_chave_do_tmdb(painel, settings, tmdb_falso, make_movie):
    """FR-010, SC-008 — a chave não aparece em corpo nem em cabeçalho."""
    settings.TMDB_API_KEY = "chave-secreta-de-teste"

    for resposta in (
        painel.get(f"{BUSCA}?q=duna"),
        painel.get(FILMES),
        painel.post(FILMES, data={"tmdb_id": 693134}, content_type="application/json"),
    ):
        conteudo = resposta.content.decode()
        assert "chave-secreta-de-teste" not in conteudo
        assert "api_key" not in conteudo
        assert all(
            "chave-secreta-de-teste" not in str(valor) for valor in resposta.headers.values()
        )


# --- Importação (US3) -----------------------------------------------------


@pytest.mark.django_db
def test_importar_traz_o_filme_completo(painel, tmdb_falso):
    """FR-011a — o MESMO mapeamento da sincronização, não um reduzido.

    Se este teste passar com gêneros ou trailers vazios, a importação escreveu
    uma segunda persistência e as abas Sobre e Trailers da 012 nascem vazias só
    para os filmes trazidos pelo painel.
    """
    from apps.catalog.models import Movie

    resposta = painel.post(
        FILMES, data={"tmdb_id": 693134}, content_type="application/json"
    )

    assert resposta.status_code == 201
    filme = Movie.objects.get(tmdb_id=693134)
    assert filme.title == "Duna: Parte Dois"
    assert filme.runtime_minutes == 166
    assert filme.synopsis
    assert filme.certification_br == "14"
    assert [g.name for g in filme.genres.all()] == ["Ficção científica"]
    assert filme.trailers.filter(is_primary=True).count() == 1


@pytest.mark.django_db
def test_importar_filme_que_ja_existe_devolve_200_e_nao_duplica(painel, make_movie, tmdb_falso):
    """FR-012 — escolher de novo não é erro, e não cria um segundo registro."""
    from apps.catalog.models import Movie

    make_movie(title="Duna: Parte Dois", tmdb_id=693134)

    resposta = painel.post(
        FILMES, data={"tmdb_id": 693134}, content_type="application/json"
    )

    assert resposta.status_code == 200
    assert Movie.objects.filter(tmdb_id=693134).count() == 1


@pytest.mark.django_db
def test_importar_nao_marca_o_filme_como_em_alta_nem_em_breve(painel, tmdb_falso):
    """FR-046 — programar é operação de grade, não curadoria de vitrine."""
    from apps.catalog.models import Movie

    painel.post(FILMES, data={"tmdb_id": 693134}, content_type="application/json")

    filme = Movie.objects.get(tmdb_id=693134)
    assert filme.is_trending is False
    assert filme.is_upcoming is False


@pytest.mark.django_db
def test_reimportar_nao_rebaixa_um_filme_que_ja_estava_em_alta(painel, make_movie, tmdb_falso):
    """R2 — `sync_movie` é aditivo, e a importação não pode desfazer a home.

    Passar `False` não desmarca: quem decide as trilhas é a sincronização de
    catálogo, e reimportar um filme pelo painel não pode tirá-lo da vitrine.
    """
    from apps.catalog.models import Movie

    make_movie(title="Duna", tmdb_id=693134, is_trending=True, is_upcoming=True)

    painel.post(FILMES, data={"tmdb_id": 693134}, content_type="application/json")

    filme = Movie.objects.get(tmdb_id=693134)
    assert filme.is_trending is True
    assert filme.is_upcoming is True


@pytest.mark.django_db
def test_importar_com_tmdb_fora_do_ar_devolve_502(painel, tmdb_falso):
    tmdb_falso.falha = "O TMDb recusou a chave de API. Confira o valor de TMDB_API_KEY no .env."

    resposta = painel.post(
        FILMES, data={"tmdb_id": 693134}, content_type="application/json"
    )

    assert resposta.status_code == 502
    assert "TMDB_API_KEY" in resposta.json()["detail"]


@pytest.mark.django_db
def test_importar_sem_tmdb_id_recusa_com_frase(painel, tmdb_falso):
    resposta = painel.post(FILMES, data={}, content_type="application/json")

    assert resposta.status_code == 400
    assert "Escolha um filme da busca" in str(resposta.json()["tmdb_id"])


@pytest.mark.django_db
def test_filme_importado_fica_publico_de_imediato(client, painel, tmdb_falso):
    """FR-045 — sem conceito novo de visibilidade: a página dele abre.

    Sem sessão, a área de sessões usa o estado vazio que a 012 já entrega —
    esta é a metade que o back-end responde.
    """
    from apps.catalog.models import Movie

    painel.post(FILMES, data={"tmdb_id": 693134}, content_type="application/json")
    filme = Movie.objects.get(tmdb_id=693134)

    publico = client.get(f"/api/v1/filmes/{filme.slug}/")

    assert publico.status_code == 200
    assert publico.json()["title"] == "Duna: Parte Dois"
    assert publico.json()["screenings"] == []
