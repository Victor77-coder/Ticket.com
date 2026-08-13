"""A grade e o ciclo de vida da sessão — US1, US2 e US5.

O que este arquivo protege, em uma frase: a programação é a ÚNICA superfície
que enxerga a grade inteira, e mexer nela nunca toca no que já foi vendido.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.screening.models import Screening

GRADE = "/api/v1/programacao/sessoes/"


def _horario(horas):
    return (timezone.now() + timedelta(hours=horas)).isoformat()


# --- A grade (US1) --------------------------------------------------------


@pytest.mark.django_db
def test_grade_vazia_devolve_200_e_nao_404(painel):
    """FR-007 — "nada programado" é uma tela, não a ausência de um recurso."""
    resposta = painel.get(GRADE)

    assert resposta.status_code == 200
    assert resposta.json() == {"count": 0, "results": []}


@pytest.mark.django_db
def test_grade_lista_os_tres_estados(painel, make_movie, make_screening, make_seats, room):
    """FR-029 — a única superfície do sistema que expõe estado de sessão."""
    make_seats(room)
    filme = make_movie()
    for horas, situacao in (
        (10, Screening.Status.DRAFT),
        (20, Screening.Status.PUBLISHED),
        (30, Screening.Status.CANCELLED),
    ):
        make_screening(filme, hours_from_now=horas, status=situacao)

    corpo = painel.get(GRADE).json()

    assert corpo["count"] == 3
    estados = {linha["estado"] for linha in corpo["results"]}
    assert estados == {"draft", "published", "cancelled"}

    # Rótulo em português junto do valor fixo: a interface distingue por
    # rótulo + forma, e o valor é o que ela usa para escolher a forma.
    rotulos = {linha["estado"]: linha["estado_rotulo"] for linha in corpo["results"]}
    assert rotulos == {
        "draft": "Rascunho",
        "published": "Publicada",
        "cancelled": "Cancelada",
    }


@pytest.mark.django_db
def test_a_linha_da_grade_traz_filme_sala_ocupacao_e_venda(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """O contrato da linha, campo a campo (contracts/programacao-api.md)."""
    lugares = make_seats(room)
    sessao = make_screening(make_movie(title="A Odisseia"))
    make_reservation(sessao, make_user(), lugares[:2])

    linha = painel.get(GRADE).json()["results"][0]

    assert linha["filme"]["titulo"] == "A Odisseia"
    assert linha["sala"]["nome"] == room.name
    assert linha["sala"]["lugares"] == len(lugares)
    assert linha["ocupacao"] == 2
    assert linha["a_venda"] is True
    assert linha["pode_editar"] is False
    assert linha["pode_cancelar"] is True


@pytest.mark.django_db
def test_ocupacao_da_grade_nao_conta_reserva_vencida(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """A regra é `Reservation.OCUPANDO`, consumida — não uma segunda leitura.

    Reserva vencida e não paga NÃO ocupa: o lugar voltou ao estoque. Se esta
    contagem divergisse do mapa de assentos, o painel mostraria uma sessão
    cheia que o cliente vê vazia.
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    make_reservation(sessao, make_user(), lugares[:3], minutes_left=-5)

    assert painel.get(GRADE).json()["results"][0]["ocupacao"] == 0


@pytest.mark.django_db
def test_a_grade_nao_faz_uma_consulta_por_sessao(
    painel, make_movie, make_screening, make_seats, room, django_assert_max_num_queries
):
    """R6 — o N+1 que `seats_taken` por linha causaria.

    O teto é fixado em consultas, e não em tempo: doze sessões que passam e
    trinta que não passariam é o tipo de regressão que só aparece na revisão
    final, quando não dá mais tempo de consertar.
    """
    make_seats(room)
    filme = make_movie()
    for horas in range(1, 13):
        make_screening(filme, hours_from_now=horas)

    # Sessão do Django, usuário, e a consulta da grade. Uma folga pequena
    # absorve o que a autenticação faz, e nunca uma consulta por linha.
    with django_assert_max_num_queries(6):
        assert painel.get(GRADE).json()["count"] == 12


@pytest.mark.django_db
def test_a_grade_nao_expoe_o_comprador(
    painel, make_movie, make_screening, make_seats, make_reservation, make_user, room
):
    """Gestão de grade não é lista de clientes.

    A ocupação é NÚMERO. Quem reservou é dado de outra tela, e o painel não
    tem motivo para conhecê-lo — expor aqui seria crescer por acúmulo.
    """
    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    cliente = make_user(username="fulano")
    make_reservation(sessao, cliente, lugares[:1])

    assert "fulano" not in painel.get(GRADE).content.decode()


# --- Criar (US2) ----------------------------------------------------------


def _corpo(filme, sala, horas=6, preco="32.00", publicar=True):
    return {
        "filme": filme.pk,
        "sala": sala.pk,
        "inicio": _horario(horas),
        "preco": preco,
        "publicar": publicar,
    }


@pytest.mark.django_db
def test_publica_uma_sessao_e_ela_entra_na_grade(painel, make_movie, make_seats, room):
    """US2 cenário 1 — a primeira grade com origem diferente do seed."""
    make_seats(room)
    filme = make_movie(title="A Odisseia")

    resposta = painel.post(
        GRADE, data=_corpo(filme, room), content_type="application/json"
    )

    assert resposta.status_code == 201
    linha = resposta.json()
    assert linha["estado"] == "published"
    assert linha["a_venda"] is True
    # A resposta de criar é uma LINHA DA GRADE: mesmos campos, mesmo formato.
    # Serializar o objeto cru devolveria ocupação e lugares faltando.
    assert linha["ocupacao"] == 0
    assert linha["sala"]["lugares"] == room.seats.count()

    assert painel.get(GRADE).json()["count"] == 1


@pytest.mark.django_db
def test_a_sessao_publicada_aparece_para_o_cliente(client, painel, make_movie, make_seats, room):
    """SC-002 — sem passo intermediário nenhum entre publicar e vender.

    O caminho do cliente é o mapa de assentos: se ele abre, a sessão está à
    venda de verdade. É a prova de que o painel não criou uma segunda noção de
    visibilidade.
    """
    make_seats(room)
    resposta = painel.post(
        GRADE, data=_corpo(make_movie(), room), content_type="application/json"
    )
    sessao_id = resposta.json()["id"]

    mapa = client.get(f"/api/v1/sessoes/{sessao_id}/mapa/")

    assert mapa.status_code == 200
    assert mapa.json()["id"] == sessao_id


@pytest.mark.django_db
def test_rascunho_nao_aparece_para_o_cliente(client, painel, make_movie, make_seats, room):
    """FR-032 — e sem filtro novo: `sellable()` já o exclui desde a 007."""
    make_seats(room)
    resposta = painel.post(
        GRADE,
        data=_corpo(make_movie(), room, publicar=False),
        content_type="application/json",
    )

    assert resposta.json()["estado"] == "draft"
    assert client.get(f"/api/v1/sessoes/{resposta.json()['id']}/mapa/").status_code == 404


@pytest.mark.django_db
def test_conflito_de_sala_e_horario_recusa_com_a_frase(painel, make_movie, make_seats, room):
    """US2 cenário 3 — a frase nomeia a sala e o horário, e nada é gravado."""
    make_seats(room)
    filme = make_movie()
    corpo = _corpo(filme, room)

    assert painel.post(GRADE, data=corpo, content_type="application/json").status_code == 201
    repetida = painel.post(GRADE, data=corpo, content_type="application/json")

    assert repetida.status_code == 409
    assert room.name in repetida.json()["detail"]
    assert "Escolha outro horário ou outra sala" in repetida.json()["detail"]
    assert painel.get(GRADE).json()["count"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("preco", ["0.00", "-5.00", None])
def test_preco_ausente_zero_ou_negativo_e_recusado(painel, make_movie, make_seats, room, preco):
    """FR-027 — os três são o mesmo problema: não há preço."""
    make_seats(room)
    corpo = _corpo(make_movie(), room, preco=preco)
    if preco is None:
        corpo.pop("preco")

    resposta = painel.post(GRADE, data=corpo, content_type="application/json")

    assert resposta.status_code == 400
    assert "preço maior que zero" in str(resposta.json()["preco"])


@pytest.mark.django_db
def test_publicar_no_passado_e_recusado(painel, make_movie, make_seats, room):
    """FR-026 — publicada no passado seria promessa que a loja não cumpre."""
    make_seats(room)

    resposta = painel.post(
        GRADE, data=_corpo(make_movie(), room, horas=-2), content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "horário futuro" in str(resposta.json()["inicio"])


@pytest.mark.django_db
def test_rascunho_no_passado_e_aceito(painel, make_movie, make_seats, room):
    """Um rascunho é anotação, não promessa — e por isso não tem essa recusa."""
    make_seats(room)

    resposta = painel.post(
        GRADE,
        data=_corpo(make_movie(), room, horas=-2, publicar=False),
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert resposta.json()["estado"] == "draft"


@pytest.mark.django_db
def test_publicar_em_sala_sem_lugares_e_recusado(painel, make_movie, room):
    """FR-028 — publicar algo que o mapa não consegue exibir é vender o nada."""
    resposta = painel.post(
        GRADE, data=_corpo(make_movie(), room), content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "ainda não tem lugares" in str(resposta.json()["sala"])


@pytest.mark.django_db
def test_filme_e_sala_inexistentes_saem_com_frase_do_campo(painel, make_seats, room):
    """Nada de texto de framework em inglês no meio de uma tela (Princípio V)."""
    make_seats(room)

    resposta = painel.post(
        GRADE,
        data={
            "filme": 99999,
            "sala": 99999,
            "inicio": _horario(6),
            "preco": "30.00",
            "publicar": False,
        },
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert "não está no catálogo" in str(resposta.json()["filme"])
    assert "não existe" in str(resposta.json()["sala"])


# --- Conduzir a grade (US5) -----------------------------------------------


def _criar(painel, filme, sala, **kwargs):
    return painel.post(
        GRADE, data=_corpo(filme, sala, **kwargs), content_type="application/json"
    ).json()


@pytest.mark.django_db
def test_editar_rascunho_grava_e_mantem_rascunho(painel, make_movie, make_seats, room):
    """FR-023 — editar não publica. Publicar é ação, com pré-condições."""
    make_seats(room)
    rascunho = _criar(painel, make_movie(), room, publicar=False)

    resposta = painel.patch(
        f"{GRADE}{rascunho['id']}/",
        data={
            "filme": rascunho["filme"]["id"],
            "sala": room.pk,
            "inicio": _horario(30),
            "preco": "45.00",
        },
        content_type="application/json",
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "draft"
    assert resposta.json()["preco"] == "45.00"


@pytest.mark.django_db
@pytest.mark.parametrize("situacao", ["published", "cancelled"])
def test_editar_publicada_ou_cancelada_e_recusado(
    painel, make_movie, make_seats, room, situacao
):
    """FR-024 — a fronteira da correção é a publicação, e a frase diz a saída."""
    make_seats(room)
    sessao = _criar(painel, make_movie(), room, publicar=(situacao == "published"))
    if situacao == "cancelled":
        painel.post(f"{GRADE}{sessao['id']}/cancelar/", content_type="application/json")

    resposta = painel.patch(
        f"{GRADE}{sessao['id']}/",
        data={
            "filme": sessao["filme"]["id"],
            "sala": room.pk,
            "inicio": _horario(30),
            "preco": "10.00",
        },
        content_type="application/json",
    )

    assert resposta.status_code == 409
    assert "só é possível alterar uma sessão em rascunho" in resposta.json()["detail"].lower()
    assert "cancele e programe outra" in resposta.json()["detail"]


@pytest.mark.django_db
def test_mover_rascunho_para_horario_ocupado_e_recusado(
    painel, make_movie, make_seats, room
):
    """US5 cenário 4 — o mesmo conflito da criação, pelo mesmo caminho."""
    make_seats(room)
    filme = make_movie()
    ocupada = _criar(painel, filme, room, horas=6)
    rascunho = _criar(painel, filme, room, horas=12, publicar=False)

    resposta = painel.patch(
        f"{GRADE}{rascunho['id']}/",
        data={
            "filme": filme.pk,
            "sala": room.pk,
            "inicio": ocupada["inicio"],
            "preco": "30.00",
        },
        content_type="application/json",
    )

    assert resposta.status_code == 409
    assert room.name in resposta.json()["detail"]
    # Nada gravado: o rascunho continua no horário dele.
    from apps.screening.models import Screening

    assert Screening.objects.get(pk=rascunho["id"]).starts_at.isoformat() != ocupada["inicio"]


@pytest.mark.django_db
def test_publicar_rascunho_coloca_a_venda(client, painel, make_movie, make_seats, room):
    """US5 cenário 5 — e a prova é o cliente alcançando o mapa."""
    make_seats(room)
    rascunho = _criar(painel, make_movie(), room, publicar=False)

    assert client.get(f"/api/v1/sessoes/{rascunho['id']}/mapa/").status_code == 404

    resposta = painel.post(
        f"{GRADE}{rascunho['id']}/publicar/", content_type="application/json"
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "published"
    assert client.get(f"/api/v1/sessoes/{rascunho['id']}/mapa/").status_code == 200


@pytest.mark.django_db
def test_publicar_rascunho_no_passado_e_recusado(painel, make_movie, make_seats, room):
    """FR-026 revalidado no servidor — `pode_publicar` é dica, não permissão."""
    make_seats(room)
    rascunho = _criar(painel, make_movie(), room, horas=-3, publicar=False)

    resposta = painel.post(
        f"{GRADE}{rascunho['id']}/publicar/", content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "horário futuro" in str(resposta.json()["inicio"])


@pytest.mark.django_db
def test_publicar_em_sala_sem_lugares_e_recusado_na_acao(painel, make_movie, room):
    """FR-028 pela outra porta: a sala perdeu os lugares depois do rascunho."""
    rascunho = _criar(painel, make_movie(), room, publicar=False)

    resposta = painel.post(
        f"{GRADE}{rascunho['id']}/publicar/", content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "ainda não tem lugares" in str(resposta.json()["sala"])


@pytest.mark.django_db
def test_publicar_o_que_ja_esta_publicado_e_409(painel, make_movie, make_seats, room):
    make_seats(room)
    sessao = _criar(painel, make_movie(), room)

    resposta = painel.post(
        f"{GRADE}{sessao['id']}/publicar/", content_type="application/json"
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Esta sessão já está publicada."


@pytest.mark.django_db
def test_cancelar_publicada_para_de_vender(client, painel, make_movie, make_seats, room):
    """US5 cenário 7 — deixa de aparecer, e nenhuma reserva nova é aceita."""
    make_seats(room)
    sessao = _criar(painel, make_movie(), room)

    resposta = painel.post(
        f"{GRADE}{sessao['id']}/cancelar/", content_type="application/json"
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "cancelled"
    assert resposta.json()["a_venda"] is False
    assert client.get(f"/api/v1/sessoes/{sessao['id']}/mapa/").status_code == 404


@pytest.mark.django_db
def test_cancelar_rascunho_nao_exige_ter_publicado(painel, make_movie, make_seats, room):
    """FR-030 — sem isto, um rascunho errado ficaria na grade para sempre."""
    make_seats(room)
    rascunho = _criar(painel, make_movie(), room, publicar=False)

    resposta = painel.post(
        f"{GRADE}{rascunho['id']}/cancelar/", content_type="application/json"
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "cancelled"


@pytest.mark.django_db
def test_cancelada_e_terminal(painel, make_movie, make_seats, room):
    """US5 cenário 10 — não há "descancelar", e não há edição."""
    make_seats(room)
    sessao = _criar(painel, make_movie(), room)
    painel.post(f"{GRADE}{sessao['id']}/cancelar/", content_type="application/json")

    de_novo = painel.post(
        f"{GRADE}{sessao['id']}/cancelar/", content_type="application/json"
    )
    voltar = painel.post(
        f"{GRADE}{sessao['id']}/publicar/", content_type="application/json"
    )

    assert de_novo.status_code == 409
    assert de_novo.json()["detail"] == "Esta sessão já foi cancelada."
    assert voltar.status_code == 409
    assert voltar.json()["detail"] == "Esta sessão foi cancelada e não pode voltar."


@pytest.mark.django_db
def test_cancelar_nao_toca_no_que_ja_foi_vendido(
    painel, client, make_movie, make_screening, make_seats, make_tickets, make_user, room
):
    """FR-031, SC-009 — cancelar muda UMA coluna, e é `status`.

    É a fronteira mais importante da US5: a 008 e a 010 fecharam pagamento e
    validação, e nada aqui pode reabri-los. Um cancelamento que apagasse
    ingresso destruiria histórico de venda por efeito colateral de uma
    operação de grade.
    """
    from apps.screening.models import Payment, ReservedSeat, Ticket

    lugares = make_seats(room)
    sessao = make_screening(make_movie())
    cliente = make_user(username="compradora")
    ingressos = make_tickets(sessao, cliente, lugares[:2])
    antes = {
        "ingressos": Ticket.objects.count(),
        "pagamentos": Payment.objects.count(),
        "ocupacoes": ReservedSeat.objects.count(),
        "usados": [t.used_at for t in Ticket.objects.all()],
    }

    painel.post(f"{GRADE}{sessao.pk}/cancelar/", content_type="application/json")

    assert Ticket.objects.count() == antes["ingressos"]
    assert Payment.objects.count() == antes["pagamentos"]
    assert ReservedSeat.objects.count() == antes["ocupacoes"]
    assert [t.used_at for t in Ticket.objects.all()] == antes["usados"]

    # E o cliente continua vendo o ingresso dele, com o mesmo comportamento
    # que a 009 entrega.
    client.force_login(cliente)
    meus = client.get("/api/v1/meus-ingressos/").json()
    assert len(meus["futuros"]) == len(ingressos)


@pytest.mark.django_db
def test_sessao_cancelada_nao_aparece_em_superficie_de_compra(
    painel, client, make_movie, make_seats, room
):
    """FR-032 — e sem filtro novo: `sellable()` já exclui as duas.

    A 007 registrou que rascunho, cancelada, iniciada e inexistente saem todas
    como o mesmo `404`, justamente para não revelar a grade interna.
    """
    make_seats(room)
    filme = make_movie(title="Só rascunho")
    sessao = _criar(painel, filme, room)
    painel.post(f"{GRADE}{sessao['id']}/cancelar/", content_type="application/json")

    detalhe = client.get(f"/api/v1/filmes/{filme.slug}/").json()

    assert detalhe["screenings"] == []
    assert client.get(f"/api/v1/sessoes/{sessao['id']}/mapa/").status_code == 404


@pytest.mark.django_db
def test_transicao_em_sessao_inexistente_devolve_404(painel):
    for caminho in ("publicar", "cancelar"):
        assert painel.post(
            f"{GRADE}99999/{caminho}/", content_type="application/json"
        ).status_code == 404
