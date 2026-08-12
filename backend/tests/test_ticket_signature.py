"""A prova do Princípio III — o código do ingresso não se forja.

O princípio exige três coisas deste código, e cada uma tem teste aqui:

  1. não pode ser identificador adivinhável (nem sequencial, nem id cru);
  2. tem de ser assinado por um segredo que nunca sai do backend;
  3. a assinatura tem de ser verificada ANTES de qualquer consulta ao banco.

A terceira é a mais fácil de escrever e a mais fácil de violar sem perceber —
basta alguém acrescentar um `.exists()` de conveniência dentro do serviço. Por
isso ela é testada com `django_assert_num_queries(0)`: uma afirmação sobre
AUSÊNCIA só vale se algo falhar quando a ausência acabar.
"""

import uuid

import pytest
from django.conf import settings
from django.core import signing
from django.urls import reverse

from apps.screening.services import ingressos

SESSAO_ID = 12


@pytest.fixture
def codigo_valido():
    return ingressos.assinar_codigo(uuid.uuid4(), SESSAO_ID)


# --- Adulteração (FR-035, SC-010) -------------------------------------------


def test_codigo_valido_e_aceito_e_devolve_o_conteudo():
    identidade = uuid.uuid4()
    codigo = ingressos.assinar_codigo(identidade, SESSAO_ID)

    assert ingressos.verificar_codigo(codigo) == {
        "ticket": identidade,
        "screening": SESSAO_ID,
    }


@pytest.mark.parametrize("posicao", [0, 5, 20, -10, -2, -1])
def test_um_caractere_alterado_e_rejeitado(codigo_valido, posicao):
    """Em qualquer posição — conteúdo ou assinatura, tanto faz."""
    original = codigo_valido[posicao]
    trocado = "A" if original != "A" else "B"
    adulterado = codigo_valido[:posicao] + trocado + codigo_valido[posicao + 1 :]

    if adulterado == codigo_valido:  # pragma: no cover - guarda do próprio teste
        pytest.skip("a troca não mudou o código")

    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(adulterado)


@pytest.mark.parametrize(
    "lixo",
    ["", "   ", "não é código", "a:b:c", "eyJ0IjoiZm9ybWF0byI6MX0", None, 12345],
)
def test_lixo_e_rejeitado_sem_estourar(lixo):
    """Entrada arbitrária é código inválido, nunca erro de sistema.

    A portaria vai receber o que a câmera ler e o que a pessoa digitar — os
    dois produzem lixo com frequência, e nenhum pode virar 500.
    """
    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(lixo)


def test_assinatura_truncada_e_rejeitada(codigo_valido):
    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(codigo_valido.rsplit(":", 1)[0])


# --- Outro segredo (FR-036, SC-010) -----------------------------------------


def test_codigo_assinado_com_outro_segredo_e_rejeitado():
    """O conteúdo é perfeitamente bem formado. Só a chave é outra.

    É o cenário de quem leu o repositório, entendeu o formato, e não tem o
    segredo. Se este teste falhar, a chave própria não está sendo usada — e o
    QR é forjável por qualquer pessoa que conheça o código-fonte.
    """
    forjado = signing.dumps(
        {"t": str(uuid.uuid4()), "s": SESSAO_ID},
        key="chave-do-atacante",
        salt=ingressos.SALT,
        compress=True,
    )

    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(forjado)


def test_codigo_assinado_com_a_secret_key_do_django_e_rejeitado():
    """FR-031 — a razão de a chave ser PRÓPRIA e não a da aplicação.

    Se este teste falhar, os dois segredos foram amarrados: quem vazar a
    `SECRET_KEY` — que assina sessão e mais um punhado de coisas — passa a
    poder emitir ingresso. Um incidente viraria dois.
    """
    forjado = signing.dumps(
        {"t": str(uuid.uuid4()), "s": SESSAO_ID},
        key=settings.SECRET_KEY,
        salt=ingressos.SALT,
        compress=True,
    )

    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(forjado)


def test_codigo_assinado_com_a_chave_certa_e_outro_salt_e_rejeitado():
    """O salt é separação de DOMÍNIO — diferente de separação de segredo.

    Impede que uma assinatura feita para outro fim, com a mesma chave, valha
    como ingresso.
    """
    forjado = signing.dumps(
        {"t": str(uuid.uuid4()), "s": SESSAO_ID},
        key=settings.TICKET_SIGNING_KEY,
        salt="outro.proposito",
        compress=True,
    )

    with pytest.raises(ingressos.CodigoInvalido):
        ingressos.verificar_codigo(forjado)


# --- Antes do banco (FR-034, R7) --------------------------------------------


@pytest.mark.django_db
def test_verificacao_de_codigo_adulterado_nao_consulta_o_banco(
    django_assert_num_queries, codigo_valido
):
    """A prova de FR-034.

    Se alguém acrescentar uma consulta ao serviço — nem que seja um
    `.exists()` de conveniência —, este teste quebra e diz por quê.
    """
    adulterado = codigo_valido[:-1] + ("A" if codigo_valido[-1] != "A" else "B")

    with django_assert_num_queries(0):
        with pytest.raises(ingressos.CodigoInvalido):
            ingressos.verificar_codigo(adulterado)


@pytest.mark.django_db
def test_verificacao_de_codigo_valido_tambem_nao_consulta_o_banco(
    django_assert_num_queries, codigo_valido
):
    """Vale para o caminho feliz também.

    A assinatura é conferida sozinha; buscar o ingresso é da camada de cima, e
    só depois. É essa ordem que o Princípio III exige da portaria.
    """
    with django_assert_num_queries(0):
        ingressos.verificar_codigo(codigo_valido)


def test_o_modulo_de_assinatura_nao_importa_modelo():
    """A garantia estrutural por trás dos dois testes acima.

    Enquanto este módulo não alcançar modelo nenhum, `num_queries == 0` é
    consequência da estrutura. No dia em que importar, passa a depender de
    disciplina — e disciplina não é garantia.
    """
    import inspect

    fonte = inspect.getsource(ingressos)

    assert "from apps." not in fonte, "o módulo puro passou a importar do domínio"
    assert "import apps." not in fonte
    assert ".objects" not in fonte, "o módulo puro passou a consultar o banco"


# --- Conteúdo do código (FR-032, FR-033) ------------------------------------


def test_o_codigo_carrega_a_identidade_da_sessao():
    """FR-033 — é o que vai permitir à portaria dizer "sessão errada".

    Sem a sessão dentro do conteúdo assinado, um ingresso legítimo apresentado
    na porta errada seria indistinguível de um código forjado, e a feature
    seguinte não teria como produzir esse desfecho.
    """
    conteudo = ingressos.verificar_codigo(ingressos.assinar_codigo(uuid.uuid4(), 77))

    assert conteudo["screening"] == 77


def test_a_identidade_do_ingresso_e_uuid_e_nao_sequencial():
    """FR-032 — sequencial revelaria o volume e convidaria a tentar o vizinho."""
    identidade = uuid.uuid4()

    conteudo = ingressos.verificar_codigo(
        ingressos.assinar_codigo(identidade, SESSAO_ID)
    )

    assert conteudo["ticket"] == identidade
    assert isinstance(conteudo["ticket"], uuid.UUID)


def test_o_codigo_nao_contem_o_uuid_em_texto_claro():
    """Não é sigilo, é higiene: o conteúdo é assinado, não cifrado.

    O que este teste fixa é que ninguém troque a assinatura por uma
    concatenação de dados do pedido — que é exatamente o que o Princípio III
    proíbe ao dizer "nem dado do pedido concatenado".
    """
    identidade = uuid.uuid4()

    codigo = ingressos.assinar_codigo(identidade, SESSAO_ID)

    assert str(identidade) not in codigo
    assert ":" in codigo, "o código perdeu a assinatura separada do conteúdo"


def test_o_mesmo_ingresso_produz_sempre_o_mesmo_codigo():
    """O ingresso tem UM código, e ele é o mesmo hoje e amanhã.

    Encontrado pelo e2e: `signing.dumps()` usa `TimestampSigner` por dentro, e
    com o instante embutido o mesmo ingresso rendia um texto diferente a cada
    renderização. Os dois verificavam — mas quem imprimiu o QR veria outro
    código ao reabrir a confirmação, e comparar papel com tela ficaria
    impossível.

    Este teste é o que impede a volta ao atalho.
    """
    identidade = uuid.uuid4()

    codigos = {ingressos.assinar_codigo(identidade, SESSAO_ID) for _ in range(5)}

    assert len(codigos) == 1, "o código do ingresso mudou entre chamadas"


def test_o_codigo_nao_carrega_carimbo_de_tempo():
    """`Signer`, não `TimestampSigner` — e a diferença é observável.

    Um código com carimbo tem três segmentos separados por `:`; sem carimbo,
    dois. O carimbo traria validade temporal a um ingresso que não caduca por
    relógio: ele é consumido na portaria, e um `max_age` mal configurado
    invalidaria ingresso legítimo na fila da entrada.
    """
    codigo = ingressos.assinar_codigo(uuid.uuid4(), SESSAO_ID)

    assert codigo.count(":") == 1, f"o código ganhou um carimbo de tempo: {codigo}"


def test_dois_ingressos_tem_codigos_distintos_e_independentes():
    """FR-037 — e um não permite deduzir o outro."""
    a = ingressos.assinar_codigo(uuid.uuid4(), SESSAO_ID)
    b = ingressos.assinar_codigo(uuid.uuid4(), SESSAO_ID)

    assert a != b
    # Nem o prefixo: se os códigos compartilhassem começo, o vizinho seria
    # adivinhável a partir de um só.
    assert a[:20] != b[:20]


# --- O desenho --------------------------------------------------------------


def test_qr_e_svg_em_data_uri(codigo_valido):
    """R11 — entra num `<img>` com `alt`, sem markup solto no DOM."""
    uri = ingressos.qr_data_uri(codigo_valido)

    assert uri.startswith("data:image/svg+xml;base64,")
    import base64

    svg = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
    assert svg.lstrip().startswith("<?xml") or svg.lstrip().startswith("<svg")
    assert "<svg" in svg


@pytest.mark.django_db
def test_o_codigo_emitido_de_verdade_e_verificavel(
    make_movie, make_screening, seats, make_reservation, make_user, client
):
    """A ponta a ponta curta: o que a API devolve passa na verificação.

    Sem este teste, os dois lados poderiam estar certos separadamente e
    incompatíveis entre si.
    """
    sessao = make_screening(make_movie("A Odisseia"))
    cliente = make_user(username="comprador")
    lugar = sessao.room.seats.filter(kind="common").first()
    reserva = make_reservation(sessao, cliente, [lugar])

    client.force_login(cliente)
    corpo = client.post(
        reverse("screening:payment-create", args=[reserva.pk]),
        data={
            "numero": "4242424242424242",
            "nome": "MARIA DE SOUZA",
            "validade": "12/2030",
            "cvv": "123",
        },
        content_type="application/json",
    ).json()

    from apps.screening.models import Ticket

    conteudo = ingressos.verificar_codigo(corpo["ingressos"][0]["codigo"])

    assert conteudo["screening"] == sessao.pk
    assert Ticket.objects.filter(public_id=conteudo["ticket"]).exists()
