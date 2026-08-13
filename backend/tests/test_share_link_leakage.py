"""A prova de FR-042: a página compartilhada não conta nada além do ingresso.

REQUISITO DA CONSTITUIÇÃO, NÃO DIFERENCIAL. O Princípio III é explícito: "o
link de compartilhamento de ingresso DEVE conceder apenas visualização do
ingresso — ele nunca expõe a conta do comprador, o histórico de compras ou
qualquer dado de pagamento". Este arquivo é a prova, no mesmo espírito do que
`test_seat_map_api.py` já faz com o mapa público da 007.

A INSPEÇÃO É POR VALOR, NÃO POR NOME DE CAMPO, e a diferença é o que faz o
teste valer alguma coisa. Conferir que a chave `"comprador"` não existe não
pega o dia em que alguém a chama de `"cliente"`, `"usuario"` ou a aninha
dentro de outro objeto. Conferir que a STRING "compradora_secreta" não aparece
em lugar nenhum da resposta pega os três casos.

Por isso a fixture usa valores propositalmente improváveis: um nome, um
e-mail, um preço e um final de cartão que não aparecem por acaso.
"""

import json
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.screening.models import Payment, Room

User = get_user_model()

# Valores que não aparecem por acaso numa resposta.
NOME_DO_COMPRADOR = "compradora-secreta-zxq"
EMAIL_DO_COMPRADOR = "nao-pode-vazar-zxq@exemplo.test"
PRECO = Decimal("77.77")
FINAL_DO_CARTAO = "9137"
BANDEIRA = "bandeira-zxq"


@pytest.fixture
def compra_de_tres(db, make_movie, make_screening, make_seats, make_reservation):
    """Uma compra de TRÊS lugares, com valores rastreáveis."""
    from apps.screening.models import Reservation, Ticket

    comprador = User.objects.create_user(
        username=NOME_DO_COMPRADOR,
        email=EMAIL_DO_COMPRADOR,
        password="desafio2026",
        role=User.Role.CUSTOMER,
    )
    sala = Room.objects.create(name="Sala vazamento", capacity=10)
    lugares = make_seats(sala, acessiveis=0)[:3]
    sessao = make_screening(
        make_movie("Filme do vazamento"), hours_from_now=24, room_obj=sala
    )
    sessao.price = PRECO
    sessao.save(update_fields=["price"])

    reserva = make_reservation(sessao, comprador, lugares)
    reserva.status = Reservation.Status.PAID
    reserva.save(update_fields=["status"])

    pagamento = Payment.objects.create(
        reservation=reserva,
        status=Payment.Status.APPROVED,
        amount=PRECO * 3,
        card_last4=FINAL_DO_CARTAO,
        card_brand=BANDEIRA,
    )
    ingressos = Ticket.objects.bulk_create(
        [Ticket(reserved_seat=o, payment=pagamento) for o in reserva.seats.all()]
    )
    return {
        "comprador": comprador,
        "reserva": reserva,
        "pagamento": pagamento,
        "ingressos": list(Ticket.objects.filter(payment=pagamento)),
    }


def _link_de(client, compra, indice=0):
    """Gera o link do ingresso `indice` e devolve o token."""
    client.force_login(compra["comprador"])
    ingresso = compra["ingressos"][indice]
    corpo = client.post(
        reverse("screening:ticket-share-link", args=[ingresso.public_id])
    ).json()
    client.logout()
    return corpo["endereco"].rsplit("/", 1)[-1]


def _resposta_publica(client, token):
    return client.get(reverse("screening:shared-ticket", args=[token]))


# --- A prova ---------------------------------------------------------------


@pytest.mark.django_db
def test_resposta_publica_nao_contem_nenhum_valor_proibido(client, compra_de_tres):
    """FR-038 a FR-042 — a lista inteira, de uma vez, por VALOR.

    Se este teste falhar depois de alguém acrescentar um campo, o campo foi
    para o lugar errado: os campos da área do dono vivem em
    `MeuIngressoSerializer`, não no `TicketSerializer`.
    """
    token = _link_de(client, compra_de_tres)
    resposta = _resposta_publica(client, token)
    corpo = resposta.content.decode()

    assert resposta.status_code == 200

    proibidos = {
        # Quem comprou (FR-038)
        "nome do comprador": NOME_DO_COMPRADOR,
        "e-mail do comprador": EMAIL_DO_COMPRADOR,
        "id do comprador": f'"{compra_de_tres["comprador"].pk}"',
        # Dado de pagamento (FR-040)
        "final do cartão": FINAL_DO_CARTAO,
        "bandeira": BANDEIRA,
        "valor unitário": str(PRECO),
        "valor total": str(PRECO * 3),
        # Identificadores reaproveitáveis (FR-041)
        "id da reserva": f'"reserva": {compra_de_tres["reserva"].pk}',
        "id do pagamento": f'"pagamento": {compra_de_tres["pagamento"].pk}',
        # Estado da compra, não do ingresso
        "prazo da reserva": "expira_em",
        "situação da reserva": "situacao",
        # Estado de USO, criado pela 010. O campo existe no modelo desde a
        # feature da portaria, e acrescentá-lo ao serializer é UMA LINHA — a
        # partir daí "utilizado" apareceria nesta página, que é PÚBLICA.
        # Verificado em T072: com o campo no `TicketSerializer`, o teste de
        # campos autorizados falha. Esta entrada é a segunda linha de defesa,
        # para o caso de alguém alargar aquela lista em vez de recuar.
        "estado de uso": "utilizado_em",
        "estado de uso (coluna)": "used_at",
        # Dado de gestão (a 007 já proíbe no mapa público)
        "capacidade da sala": "capacidade",
        "status da sessão": "published",
        # O segredo (Princípio III)
        "chave de assinatura": settings.TICKET_SIGNING_KEY,
    }

    vazaram = [rotulo for rotulo, valor in proibidos.items() if valor in corpo]
    assert vazaram == [], f"A resposta pública vazou: {vazaram}"


@pytest.mark.django_db
def test_resposta_publica_tem_exatamente_os_campos_autorizados(client, compra_de_tres):
    """FR-037 — definido por INCLUSÃO.

    A lista de proibidos do teste acima é a rede de segurança; esta asserção é
    o contrato. Um campo novo em `TicketSerializer` quebra aqui mesmo que
    ninguém tenha pensado em proibi-lo.
    """
    token = _link_de(client, compra_de_tres)

    corpo = json.loads(_resposta_publica(client, token).content)

    # `tipo` entrou na 014 por DECISÃO, e não por descuido: é informação do
    # ingresso, não do comprador — quem recebe o link vai apresentar o mesmo
    # documento na porta, e esconder que a entrada é meia faria a pessoa
    # descobrir isso na catraca. A inspeção continua sendo por INCLUSÃO: campo
    # novo que ninguém autorizou quebra aqui.
    assert set(corpo) == {"codigo", "qr_svg", "filme", "sessao", "sala", "assento", "tipo"}
    assert set(corpo["assento"]) == {"fileira", "numero"}


@pytest.mark.django_db
def test_um_link_da_acesso_a_um_ingresso_so(client, compra_de_tres):
    """FR-039 — os outros dois da mesma compra não aparecem nem são alcançáveis."""
    token = _link_de(client, compra_de_tres, indice=0)
    corpo = _resposta_publica(client, token).content.decode()

    outros = compra_de_tres["ingressos"][1:]
    assert len(outros) == 2

    for outro in outros:
        assert str(outro.public_id) not in corpo
        # Nem o lugar dos outros: a resposta traz UM assento.
        lugar = outro.reserved_seat.seat
        assert f'"numero": {lugar.number}' not in corpo or lugar.number == (
            compra_de_tres["ingressos"][0].reserved_seat.seat.number
        )


@pytest.mark.django_db
def test_cada_ingresso_da_compra_tem_link_proprio_e_distinto(client, compra_de_tres):
    """FR-039 — três links, três ingressos, sem cruzamento."""
    tokens = [_link_de(client, compra_de_tres, i) for i in range(3)]

    assert len(set(tokens)) == 3

    lugares = set()
    for token in tokens:
        corpo = json.loads(_resposta_publica(client, token).content)
        lugares.add((corpo["assento"]["fileira"], corpo["assento"]["numero"]))

    assert len(lugares) == 3


@pytest.mark.django_db
def test_public_id_nao_aparece_como_campo_reaproveitavel(client, compra_de_tres):
    """FR-041, com a ressalva registrada.

    O `public_id` VIAJA DENTRO do código assinado — é assim desde a 008, e é
    o que permite à portaria identificar o ingresso. O que não pode existir é
    ele como CAMPO da resposta, em texto, ao lado do QR: aí seria
    identificador reaproveitável e a metade não secreta do par entregue de
    graça.

    A distinção importa e por isso está escrita: quem lê o teste precisa saber
    que a asserção é sobre a forma da resposta, não sobre o conteúdo assinado.
    """
    token = _link_de(client, compra_de_tres)
    corpo = json.loads(_resposta_publica(client, token).content)

    assert "id" not in corpo
    assert str(compra_de_tres["ingressos"][0].public_id) not in json.dumps(
        {k: v for k, v in corpo.items() if k != "codigo"}
    )


@pytest.mark.django_db
def test_pagina_publica_nao_pede_conta_nem_reconhece_sessao(client, compra_de_tres):
    """FR-036 — a resposta é a mesma com e sem sessão ativa.

    `authentication_classes = []` na view faz disto estrutura: não existe
    caminho pelo qual ela enxergue um usuário.
    """
    token = _link_de(client, compra_de_tres)

    sem_sessao = _resposta_publica(client, token)

    client.force_login(compra_de_tres["comprador"])
    com_sessao = _resposta_publica(client, token)

    assert sem_sessao.status_code == com_sessao.status_code == 200
    assert sem_sessao.content == com_sessao.content
