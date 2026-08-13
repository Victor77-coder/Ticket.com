"""Cliente HTTP do TMDb.

Único ponto do sistema que fala com a API externa. O caminho de leitura da
home nunca passa por aqui — Princípio VII da constitution.
"""

import httpx
from django.conf import settings


class TMDBError(Exception):
    """Falha ao falar com o TMDb, com mensagem acionável em português."""


class TMDBClient:
    def __init__(self, api_key=None, timeout=None):
        self.api_key = api_key if api_key is not None else settings.TMDB_API_KEY
        self.timeout = timeout or settings.TMDB_TIMEOUT_SECONDS
        self.base_url = settings.TMDB_BASE_URL

    def _get(self, path, params=None):
        if not self.api_key:
            raise TMDBError(
                "TMDB_API_KEY não está configurada. Preencha a variável no arquivo .env "
                "antes de rodar a sincronização."
            )

        query = {"api_key": self.api_key, "language": settings.TMDB_LANGUAGE}
        query.update(params or {})

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}{path}", params=query)
        except httpx.TimeoutException as exc:
            raise TMDBError(
                f"O TMDb não respondeu em {self.timeout:.0f}s. Verifique a conexão e "
                "tente novamente."
            ) from exc
        except httpx.HTTPError as exc:
            raise TMDBError(f"Não foi possível falar com o TMDb: {exc}") from exc

        if response.status_code == 401:
            raise TMDBError(
                "O TMDb recusou a chave de API. Confira o valor de TMDB_API_KEY no .env."
            )
        if response.status_code == 404:
            raise TMDBError("Recurso não encontrado no TMDb.")
        if response.status_code >= 400:
            raise TMDBError(
                f"O TMDb respondeu com erro {response.status_code}. Tente novamente em "
                "alguns instantes."
            )

        return response.json()

    def now_playing(self, page=1):
        """Filmes em cartaz na região configurada."""
        return self._get(
            "/movie/now_playing",
            {"page": page, "region": settings.TMDB_REGION},
        )

    def trending(self, page=1):
        """Filmes em alta da semana.

        Semana e não dia: a lista diária oscila demais para uma vitrine que só
        é sincronizada manualmente (R6).
        """
        return self._get("/trending/movie/week", {"page": page})

    def upcoming(self, page=1):
        """Filmes com estreia futura na região configurada.

        A resposta traz também `dates.minimum` e `dates.maximum`, a janela que
        o próprio TMDb considerou — não impomos uma segunda regra por cima.
        """
        return self._get(
            "/movie/upcoming",
            {"page": page, "region": settings.TMDB_REGION},
        )

    def search_movies(self, query, page=1):
        """Busca por título, para o painel do organizador (013, R3).

        Passa por `_get` como todos os outros, e é isso que importa: chave,
        idioma, prazo e a tradução de erro para `TMDBError` em português já
        estão lá. Uma chamada HTTP escrita à mão aqui teria de repetir os
        quatro, e a que alguém corrigisse seria a outra.

        UMA PÁGINA POR BUSCA, sem paginação infinita: o objetivo é achar um
        filme para programar, não navegar o catálogo mundial. Uma página só
        mantém legível o estado vazio de "nada encontrado para este termo".

        `include_adult=False` porque não há propósito no domínio, e o
        contrário devolveria resultado que a interface teria de filtrar depois.
        """
        return self._get(
            "/search/movie",
            {"query": query, "page": page, "include_adult": False},
        )

    def movie_detail(self, tmdb_id):
        """Detalhe do filme com vídeos e datas de lançamento numa só chamada.

        `append_to_response` resolve metadados, trailer (R4) e classificação
        indicativa (R3) em uma requisição em vez de três.
        """
        return self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "videos,release_dates"},
        )
