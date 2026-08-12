"""A negação por papel, endpoint a endpoint — FR-034, FR-035, FR-036, SC-005.

É uma das três provas de recorte da 013, e a que o Princípio IV cobra: a
autorização é do SERVIDOR. Esconder o botão na interface não conta, então
cada endpoint é chamado direto, sem passar pelo front.

A DISTINÇÃO QUE ESTE ARQUIVO EXISTE PARA FIXAR: quem não entrou recebe `401`,
quem entrou com o papel errado recebe `403`. Confundir os dois faria o front
conduzir um cliente à tela de entrada por uma recusa que entrar de novo não
resolve — caminho sem saída, porque a entrada não muda o papel. É a mesma
distinção que 007, 008, 009 e 010 já aplicam, agora do lado da programação.

A LISTA É A DO CONTRATO INTEIRO, de propósito: um endpoint de programação que
nasça sem cobertura aqui é falha de FR-034, e o jeito de perceber isso é ter
a lista escrita num lugar só. Ver `contracts/programacao-api.md`.
"""

import pytest

RECUSA_POR_PAPEL = "Apenas organizadores programam sessões."


def _endpoints(sala_id, sessao_id):
    """(método, caminho, corpo) de TODA escrita e leitura de programação.

    O corpo é irrelevante para a autorização — a permissão é avaliada antes da
    validação —, e é justamente por isso que ele vai propositalmente pobre: se
    algum destes passar por causa de um corpo bem formado, a recusa está no
    lugar errado.
    """
    return [
        ("get", "/api/v1/programacao/filmes/", None),
        ("get", "/api/v1/programacao/filmes/busca/?q=duna", None),
        ("post", "/api/v1/programacao/filmes/", {"tmdb_id": 693134}),
        ("get", "/api/v1/programacao/salas/", None),
        ("post", "/api/v1/programacao/salas/", {"nome": "Sala X", "capacidade": 20}),
        ("patch", f"/api/v1/programacao/salas/{sala_id}/", {"nome": "Outro nome"}),
        ("get", "/api/v1/programacao/sessoes/", None),
        ("post", "/api/v1/programacao/sessoes/", {"filme": 1, "sala": sala_id}),
        ("patch", f"/api/v1/programacao/sessoes/{sessao_id}/", {"preco": "10.00"}),
        ("post", f"/api/v1/programacao/sessoes/{sessao_id}/publicar/", {}),
        ("post", f"/api/v1/programacao/sessoes/{sessao_id}/cancelar/", {}),
    ]


def _chamar(client, metodo, caminho, corpo):
    funcao = getattr(client, metodo)
    if corpo is None:
        return funcao(caminho)
    return funcao(caminho, data=corpo, content_type="application/json")


@pytest.fixture
def alvos(db, room, make_movie, make_screening):
    """Uma sala e uma sessão reais, para os caminhos com identificador.

    Existem para que um `404` não possa ser confundido com a recusa que este
    arquivo mede.
    """
    sessao = make_screening(make_movie())
    return _endpoints(room.pk, sessao.pk)


@pytest.mark.django_db
def test_visitante_recebe_401_em_toda_a_programacao(client, alvos):
    """Sem sessão é `401` — e a frase convida a entrar, não acusa de papel."""
    for metodo, caminho, corpo in alvos:
        resposta = _chamar(client, metodo, caminho, corpo)

        assert resposta.status_code == 401, f"{metodo.upper()} {caminho}"
        assert "detail" in resposta.json()


@pytest.mark.django_db
def test_cliente_autenticado_recebe_403_em_toda_a_programacao(
    client, comprador, alvos
):
    """FR-035 — o cliente ENTROU. A recusa é de papel, nunca de autenticação."""
    client.force_login(comprador)

    for metodo, caminho, corpo in alvos:
        resposta = _chamar(client, metodo, caminho, corpo)

        assert resposta.status_code == 403, f"{metodo.upper()} {caminho}"
        assert resposta.json()["detail"] == RECUSA_POR_PAPEL


@pytest.mark.django_db
def test_portaria_autenticada_recebe_403_em_toda_a_programacao(
    client, porteiro_de_programacao, alvos
):
    """FR-036 — o segundo papel exigido pela suíte, pelo mesmo motivo."""
    client.force_login(porteiro_de_programacao)

    for metodo, caminho, corpo in alvos:
        resposta = _chamar(client, metodo, caminho, corpo)

        assert resposta.status_code == 403, f"{metodo.upper()} {caminho}"
        assert resposta.json()["detail"] == RECUSA_POR_PAPEL


@pytest.mark.django_db
def test_a_recusa_de_papel_nao_e_302(client, comprador, alvos):
    """Nenhuma recusa pode virar redirecionamento.

    Um `302` para a entrada faria o front tratar papel errado como sessão
    vencida, e a pessoa entraria de novo para receber a mesma recusa.
    """
    client.force_login(comprador)

    for metodo, caminho, corpo in alvos:
        resposta = _chamar(client, metodo, caminho, corpo)
        assert resposta.status_code != 302, f"{metodo.upper()} {caminho}"


@pytest.mark.django_db
def test_organizador_atravessa_a_permissao(painel, alvos):
    """O organizador nunca é recusado POR PAPEL.

    Ele pode receber `400`, `404` ou `409` — são desfechos de negócio, e cada
    um tem teste próprio. O que ele não pode receber é `401` ou `403`: seria a
    permissão negando quem a feature existe para servir.
    """
    for metodo, caminho, corpo in alvos:
        resposta = _chamar(painel, metodo, caminho, corpo)

        assert resposta.status_code not in (401, 403), f"{metodo.upper()} {caminho}"
