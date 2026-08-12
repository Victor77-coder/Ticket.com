"""A prova do Princípio III na borda da portaria: o forjado não passa.

O princípio exige que "a portaria DEVE verificar essa assinatura antes de
qualquer consulta ao banco". A 008 tornou isso possível deixando
`services/ingressos.py` PURO — sem importar modelo, sem tocar o banco — e
fixou a ausência com `django_assert_num_queries(0)`.

Este arquivo verifica a mesma coisa um nível acima: o SERVIÇO DA PORTARIA,
que consulta o banco no caminho feliz, não consulta nada quando a assinatura
não confere.

A MEDIÇÃO É NO SERVIÇO, NÃO NA VIEW, e a escolha tem motivo: na view a
contagem seria falsa por algo que não tem a ver com a feature — a
autenticação por sessão consulta o banco antes de qualquer código nosso
rodar. Medir ali obrigaria a uma contagem "esperada" que ninguém sabe
defender e que muda quando o Django muda. Por isso a spec está escrita como
"antes de qualquer consulta ao REGISTRO DE INGRESSOS".
"""

import pytest
from django.conf import settings
from django.core import signing

from apps.screening.services import ingressos as ingressos_service
from apps.screening.services import portaria


@pytest.fixture
def ingresso_valido(make_movie, make_screening, seats, room, make_user, make_tickets):
    sessao = make_screening(make_movie("A Odisseia"), hours_from_now=2)
    cliente = make_user(username="dono_do_ingresso")
    lugares = list(room.seats.filter(kind="common")[:1])
    ingresso = make_tickets(sessao, cliente, lugares, minutes_left=10)[0]
    return {
        "ingresso": ingresso,
        "sessao": sessao,
        "codigo": ingressos_service.assinar_codigo(ingresso.public_id, sessao.pk),
    }


# --- Os códigos que não passam -------------------------------------------


@pytest.mark.django_db
def test_codigo_adulterado_e_invalido(ingresso_valido):
    """FR-028 — um caractere trocado basta."""
    codigo = ingresso_valido["codigo"]
    adulterado = codigo[:-1] + ("X" if codigo[-1] != "X" else "Y")

    resultado = portaria.validar(codigo=adulterado, sessao_id=ingresso_valido["sessao"].pk)

    assert resultado.situacao == "invalido"


@pytest.mark.django_db
def test_codigo_inventado_e_invalido(ingresso_valido):
    resultado = portaria.validar(
        codigo="eu-inventei-isso:aqui:agora", sessao_id=ingresso_valido["sessao"].pk
    )

    assert resultado.situacao == "invalido"


@pytest.mark.django_db
def test_codigo_assinado_com_outra_chave_e_invalido(ingresso_valido):
    """FR-028 — a chave é o que impede forjar."""
    outro = signing.Signer(key="chave-de-atacante", salt="ingresso.qr").sign(
        "eyJzIjoxLCJ0IjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIn0"
    )

    resultado = portaria.validar(codigo=outro, sessao_id=ingresso_valido["sessao"].pk)

    assert resultado.situacao == "invalido"


@pytest.mark.django_db
def test_codigo_assinado_com_a_secret_key_do_django_e_invalido(ingresso_valido):
    """A razão de a chave do ingresso ser SEPARADA da chave da aplicação.

    Se as duas fossem a mesma, quem obtivesse a `SECRET_KEY` — que circula em
    muito mais lugares — passaria a emitir ingressos. Este teste é o que
    documenta que elas não são a mesma.
    """
    com_a_chave_errada = signing.Signer(
        key=settings.SECRET_KEY, salt="ingresso.qr"
    ).sign("eyJzIjoxLCJ0IjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIn0")

    resultado = portaria.validar(
        codigo=com_a_chave_errada, sessao_id=ingresso_valido["sessao"].pk
    )

    assert resultado.situacao == "invalido"


@pytest.mark.django_db
def test_codigo_vazio_e_invalido(ingresso_valido):
    """A view recusa antes com `400`; o serviço não pode estourar."""
    for vazio in ("", "   ", None):
        assert (
            portaria.validar(codigo=vazio, sessao_id=ingresso_valido["sessao"].pk).situacao
            == "invalido"
        )


# --- A prova que importa: nenhuma consulta ao registro de ingressos -------


@pytest.mark.django_db
def test_assinatura_invalida_e_rejeitada_sem_tocar_o_banco(
    ingresso_valido, django_assert_num_queries
):
    """FR-027, SC-008 — Princípio III, verbatim.

    "a portaria DEVE verificar essa assinatura antes de qualquer consulta ao
    banco". Escrever isso é fácil; violá-lo sem perceber também, porque basta
    alguém buscar o ingresso antes de conferir a assinatura "para simplificar".

    Com `num_queries(0)` a garantia deixa de depender de disciplina.
    """
    with django_assert_num_queries(0):
        resultado = portaria.validar(
            codigo="assinatura:que:nao:confere", sessao_id=ingresso_valido["sessao"].pk
        )

    assert resultado.situacao == "invalido"


# --- Bem assinado, mas sem ingresso: o MESMO desfecho ---------------------


@pytest.mark.django_db
def test_codigo_bem_assinado_sem_ingresso_correspondente_e_invalido(ingresso_valido):
    """FR-029 — nenhuma pista de onde o palpite chegou perto.

    Um código legitimamente assinado por este servidor, mas apontando para um
    ingresso que não existe, sai igual a um código forjado. Distinguir daria
    um oráculo: "este `public_id` existe" é exatamente o que não pode vazar.
    """
    fantasma = ingressos_service.assinar_codigo(
        "00000000-0000-0000-0000-000000000000", ingresso_valido["sessao"].pk
    )

    resultado = portaria.validar(codigo=fantasma, sessao_id=ingresso_valido["sessao"].pk)

    assert resultado.situacao == "invalido"


@pytest.mark.django_db
def test_invalido_nao_traz_nenhum_campo_extra(ingresso_valido):
    """A resposta do inválido é só o desfecho.

    Qualquer detalhe a mais — sessão, lugar, instante — entregaria a quem
    tenta adivinhar a informação que o desfecho existe para negar.
    """
    resultado = portaria.validar(codigo="lixo:total", sessao_id=ingresso_valido["sessao"].pk)

    assert resultado.situacao == "invalido"
    assert resultado.ingresso is None
    assert resultado.sessao_do_ingresso is None
    assert resultado.utilizado_em is None


@pytest.mark.django_db
def test_payload_divergente_do_banco_e_invalido(
    ingresso_valido, make_movie, make_screening, make_seats
):
    """R4, passo 3 — defesa em profundidade, e nunca uma exceção.

    O `s` do código é assinado e confiável. Compará-lo com a sessão do
    ingresso no banco custa nada e transforma uma inconsistência de dados num
    desfecho claro, em vez de num erro 500.
    """
    from apps.screening.models import Room

    outra_sala = Room.objects.create(name="Sala divergente", capacity=5)
    make_seats(outra_sala, acessiveis=0)
    outra_sessao = make_screening(
        make_movie("Outro filme"), hours_from_now=3, room_obj=outra_sala
    )

    # Código assinado com a sessão ERRADA para aquele ingresso.
    divergente = ingressos_service.assinar_codigo(
        ingresso_valido["ingresso"].public_id, outra_sessao.pk
    )

    resultado = portaria.validar(codigo=divergente, sessao_id=outra_sessao.pk)

    assert resultado.situacao == "invalido"
