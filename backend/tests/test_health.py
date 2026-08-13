def test_healthz_responde_ok(client):
    resposta = client.get("/healthz")
    assert resposta.status_code == 200
    assert resposta.content == b"ok"
