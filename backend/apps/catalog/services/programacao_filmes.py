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
