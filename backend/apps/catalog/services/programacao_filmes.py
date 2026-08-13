"""Trazer um filme do TMDb pelo painel do organizador.

REUSA `sync_movie`, o MESMO mapeamento da sincronização de catálogo. Não
existe — e não pode nascer — um segundo mapeamento reduzido (FR-011a): a 012
construiu as abas Sobre e Trailers em cima de gêneros, classificação e
`Trailer`, e um filme trazido pelo painel não pode ser filme de segunda
classe, com aquelas abas vazias.

Custa UMA requisição ao TMDb: `movie_detail` já usa
`append_to_response=videos,release_dates`. Uma persistência mínima custaria o
mesmo e entregaria menos (R2).

`is_trending=False` e `is_upcoming=False` são passados de propósito, e por
construção de `sync_movie` (`movie.is_trending or is_trending`) NÃO desmarcam
um filme que já estava em alta: programar é operação de grade, não curadoria
de vitrine, e reimportar não pode rebaixar um filme na home (FR-046).
"""

from apps.catalog.models import Movie
from apps.catalog.services.tmdb_client import TMDBClient
from apps.catalog.services.tmdb_sync import sync_movie


def importar_filme(tmdb_id, cliente=None):
    """Traz o filme do TMDb e persiste localmente. Devolve `(filme, criado)`.

    `criado` distingue o `201` do `200` na resposta, e a distinção existe
    porque escolher um filme que já está no catálogo NÃO é erro: o organizador
    pediu um filme e recebeu um filme (FR-012). Um `409` aqui faria a
    interface exibir falha por uma ação que produziu exatamente o resultado
    desejado — é o mesmo argumento que a 009 registrou para o link de
    compartilhamento.

    A DUPLICATA É IMPEDIDA PELO BANCO, não por esta consulta prévia:
    `Movie.tmdb_id` é `unique`, e `sync_movie` usa `get_or_create` sobre ele. A
    leitura daqui serve só para saber o que responder — se ela errar, o pior
    que acontece é um `200` onde caberia `201`, e nenhum filme duplicado.
    """
    ja_existia = Movie.objects.filter(tmdb_id=tmdb_id).exists()

    detalhe = (cliente or TMDBClient()).movie_detail(tmdb_id)

    # UMA requisição ao TMDb: `movie_detail` já pede
    # `append_to_response=videos,release_dates`, então metadados, trailers e
    # classificação vêm juntos. Uma persistência reduzida custaria o mesmo e
    # entregaria um filme de segunda classe, com as abas Sobre e Trailers da
    # 012 vazias (FR-011a).
    filme = sync_movie(detalhe, is_trending=False, is_upcoming=False)

    return filme, not ja_existia


def ja_no_catalogo(resultados):
    """Os `tmdb_id` da página de busca que já existem localmente.

    UMA consulta com `__in` para a página inteira, nunca uma por linha: vinte
    resultados dariam vinte consultas numa tela que responde enquanto a pessoa
    digita.
    """
    ids = [item.get("id") for item in resultados if item.get("id")]
    return set(Movie.objects.filter(tmdb_id__in=ids).values_list("tmdb_id", flat=True))
