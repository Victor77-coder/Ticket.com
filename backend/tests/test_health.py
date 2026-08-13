import pytest


# A sonda ABRE CONEXÃO de propósito (`config/health.py`): responder 200 com o
# Postgres fora do ar faria o orquestrador mandar tráfego para uma instância
# que não serve. O `django_db` é o que reconhece isso — sem ele o pytest-django
# bloqueia o acesso e o teste falha por política, não por defeito.
@pytest.mark.django_db
def test_healthz_responde_ok(client):
    resposta = client.get("/healthz")
    assert resposta.status_code == 200
    assert resposta.content == b"ok"
