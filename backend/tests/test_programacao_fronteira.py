"""A fronteira entre o painel e o público — proibição 1 do contrato.

A 013 CRIOU A SUPERFÍCIE ONDE OS CAMPOS DE GESTÃO APARECEM, e é justamente
por isso que este arquivo existe. Enquanto `status`, `capacity`, contagem de
vendidos e `tmdb_id` não eram expostos em lugar nenhum, o risco de vazarem era
teórico. Agora eles têm serializer, tipo de front e tela — e a pressão de
crescimento aponta para os dois lados.

A direção é uma: campo de gestão nasce nos serializers de programação e NUNCA
migra para os públicos. `test_highlights_api.py`, `test_home_rows_api.py`,
`test_search_api.py` e `test_seat_map_api.py` guardam cada superfície por
dentro; este arquivo guarda a REGRA, varrendo todas de uma vez com a mesma
lista de campos proibidos.
"""

import pytest

# O que é do painel e de mais ninguém (data-model.md §fronteira).
#
# `preco` NÃO está aqui, e a ausência é decisão: é o que o cliente paga, e o
# mapa de assentos o exibe desde a 007.
CAMPOS_DE_GESTAO = ["status", "capacity", "capacidade", "tmdb_id", "ocupacao", "vendidos"]


def _sem_campos_de_gestao(payload, caminho="raiz"):
    """Varre o corpo inteiro, e não só o primeiro nível.

    Um campo de gestão que vaze vai aparecer aninhado — dentro de `sala`, de
    `filme` ou de um item de lista —, que é exatamente onde uma verificação de
    chaves do topo não olharia.
    """
    if isinstance(payload, dict):
        for chave, valor in payload.items():
            assert chave not in CAMPOS_DE_GESTAO, f"{caminho}.{chave} vazou"
            _sem_campos_de_gestao(valor, f"{caminho}.{chave}")
    elif isinstance(payload, list):
        for indice, item in enumerate(payload):
            _sem_campos_de_gestao(item, f"{caminho}[{indice}]")


@pytest.fixture
def cenario(db, make_movie, make_screening, make_seats, room):
    """Um filme com sessão publicada e mapa — o que as telas públicas leem."""
    make_seats(room)
    filme = make_movie(title="A Odisseia", is_trending=True, is_upcoming=True)
    sessao = make_screening(filme, hours_from_now=6)
    return {"filme": filme, "sessao": sessao}


@pytest.mark.django_db
def test_nenhuma_superficie_publica_expoe_campo_de_gestao(client, cenario):
    """Uma varredura para todas — a lista de campos mora num lugar só."""
    caminhos = [
        "/api/v1/highlights/",
        "/api/v1/home/",
        "/api/v1/busca/?q=odisseia",
        f"/api/v1/filmes/{cenario['filme'].slug}/",
        f"/api/v1/sessoes/{cenario['sessao'].pk}/mapa/",
    ]

    for caminho in caminhos:
        resposta = client.get(caminho)
        assert resposta.status_code == 200, caminho
        _sem_campos_de_gestao(resposta.json(), caminho)


@pytest.mark.django_db
def test_o_mapa_continua_dizendo_esgotada_por_booleano(client, cenario):
    """A contagem de vendidos nunca é aberta ao cliente.

    `esgotada` responde "dá para comprar?" sem revelar operação — é a mesma
    escolha que `has_available_seats` fixou na 001, e a 013 não a reabre.
    """
    corpo = client.get(f"/api/v1/sessoes/{cenario['sessao'].pk}/mapa/").json()

    assert isinstance(corpo["esgotada"], bool)
    assert "ocupacao" not in corpo


@pytest.mark.django_db
def test_a_programacao_expoe_exatamente_o_que_o_publico_esconde(painel, cenario):
    """O outro lado da fronteira, para que ela seja uma LINHA e não um muro.

    Se este teste falhar junto com o de cima, a fronteira sumiu — os campos
    deixaram de existir em vez de terem ficado do lado certo.
    """
    linha = painel.get("/api/v1/programacao/sessoes/").json()["results"][0]
    sala = painel.get("/api/v1/programacao/salas/").json()["results"][0]
    filme = painel.get("/api/v1/programacao/filmes/").json()["results"][0]

    assert linha["estado"] == "published"
    assert linha["ocupacao"] == 0
    assert sala["capacidade"] > 0
    assert filme["tmdb_id"]
