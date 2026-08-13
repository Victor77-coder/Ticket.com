"""Criar, editar, publicar e cancelar sessão — as escritas do painel.

O CONFLITO DE (SALA, HORÁRIO) VEM DO BANCO. A garantia é a constraint
`uma_sessao_por_sala_e_horario`, capturada como `IntegrityError` e reconhecida
pelo NOME. Uma consulta `Screening.objects.filter(room=..., starts_at=...).
exists()` antes do INSERT é o padrão que a concorrência quebra — as duas
requisições verificam, nenhuma encontra, ambas gravam — e este projeto já o
rejeitou três vezes (007, 008, 009). O comentário de
`Reservation.idempotency_key` o descreve por escrito.

`test_programacao_concorrencia.py` prova o resultado; a revisão de código
prova o caminho (FR-025, R4).

O QUE CANCELAR NÃO FAZ (FR-031): não estorna pagamento, não apaga ingresso,
não apaga ocupação, não mexe em `used_at`, não devolve ao estoque lugar já
pago. Muda UMA coluna: `status`.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.screening.models import Screening

# O nome é NOSSO e está no modelo — por isso é ele que identifica a violação,
# e não a mensagem do PostgreSQL, que muda entre versões e locales.
CONSTRAINT_DE_HORARIO = "uma_sessao_por_sala_e_horario"


class ConflitoDeHorario(Exception):
    """Aquela (sala, horário) já tem sessão.

    A frase nomeia a sala E o horário: "já existe sessão nesse horário" sem os
    dois obriga a pessoa a tentar de novo às cegas até acertar qual conflito
    ela criou. É a mesma exigência que a 007 fixou para o lugar perdido.
    """

    def __init__(self, sala, inicio):
        self.sala = sala
        self.inicio = inicio
        super().__init__(self.mensagem)

    @property
    def mensagem(self):
        quando = timezone.localtime(self.inicio)
        return (
            f"A {self.sala.name} já tem sessão às {quando:%H:%M} de {quando:%d/%m}. "
            "Escolha outro horário ou outra sala."
        )


def criar_sessao(*, filme, sala, inicio, preco, publicar):
    """Grava a sessão, em rascunho ou publicada.

    O `transaction.atomic()` INTERNO é obrigatório e não decorativo: sem ele, a
    transação inteira fica marcada como inutilizável depois do `IntegrityError`
    e a primeira consulta seguinte estoura `TransactionManagementError` — o
    `except` não conseguiria nem montar a mensagem, porque montá-la toca a
    sala.

    Não há `exists()` antes do INSERT, e a ausência é o ponto: duas requisições
    simultâneas verificariam, nenhuma encontraria, e ambas gravariam. Quem
    recusa é o banco (FR-025, SC-004).
    """
    situacao = Screening.Status.PUBLISHED if publicar else Screening.Status.DRAFT

    try:
        with transaction.atomic():
            return Screening.objects.create(
                movie=filme,
                room=sala,
                starts_at=inicio,
                price=preco,
                status=situacao,
            )
    except IntegrityError as exc:
        if CONSTRAINT_DE_HORARIO in str(exc):
            raise ConflitoDeHorario(sala, inicio) from exc
        # Qualquer outra violação é defeito, não desfecho de negócio: subir
        # inteira é o que impede uma falha desconhecida virar "conflito de
        # horário" na tela de quem programa.
        raise


# --- Pré-condições de publicação, em UM lugar -----------------------------
#
# As duas frases abaixo aparecem em DOIS caminhos: criar com `publicar: true` e
# `POST .../publicar/`. Escrevê-las nos dois lugares faria a redação divergir na
# primeira revisão — e a interface desabilita o botão com base num terceiro
# ponto (`pode_publicar` no serializer da grade), que é dica, não garantia.
# Aqui é a garantia, e ela é uma.

HORARIO_PASSADO = (
    "Não dá para publicar uma sessão que já começou. Escolha um horário futuro."
)
PRECO_INVALIDO = "Informe um preço maior que zero."


def _frase_sem_lugares(sala):
    return (
        f"A {sala.name} ainda não tem lugares. Defina a capacidade antes de publicar."
    )


def erros_para_publicar(sala, inicio):
    """`{campo: frase}` — vazio quando dá para publicar.

    Uma sessão publicada no passado não é vendável (`sellable()` já a exclui) e
    apareceria no painel como promessa que a loja não cumpre. Uma sessão numa
    sala sem lugares é pior: o mapa não consegue exibi-la, então ela seria algo
    à venda que ninguém consegue comprar.

    Rascunho no passado é ACEITO — um rascunho é anotação, não promessa.
    """
    erros = {}

    if inicio <= timezone.now():
        erros["inicio"] = HORARIO_PASSADO

    if not sala.seats.exists():
        erros["sala"] = _frase_sem_lugares(sala)

    return erros


# --- Transições (US5) -----------------------------------------------------
#
# A FRONTEIRA DA CORREÇÃO É A PUBLICAÇÃO, e ela é deliberada. Enquanto a sessão
# é rascunho, nenhum cliente a viu e nada pode ter sido comprado — corrigir não
# muda nada sob ninguém. Depois de publicada, filme, sala, horário e preço
# ficam imutáveis: mudar qualquer um reabriria "o que acontece com quem já
# comprou", que é regra de negócio nova, e esta feature declara não reabrir
# nenhuma. O caminho para uma sessão publicada errada é cancelar e programar
# outra (FR-024).


class EstadoInvalido(Exception):
    """A transição pedida não existe a partir do estado atual.

    A frase diz o estado E a saída: "não é possível" sozinho deixa a pessoa
    sem saber se ela errou o botão ou se o sistema quebrou.
    """

    def __init__(self, mensagem):
        self.mensagem = mensagem
        super().__init__(mensagem)


class CondicoesDePublicacao(Exception):
    """As pré-condições de publicação, como erro de CAMPO.

    Carrega `{campo: frase}` porque a interface destaca o campo errado — o
    horário ou a sala —, e um `detail` solto obrigaria a pessoa a descobrir
    qual dos dois consertar.
    """

    def __init__(self, erros):
        self.erros = erros
        super().__init__(str(erros))


SO_RASCUNHO_E_EDITAVEL = (
    "Só é possível alterar uma sessão em rascunho. "
    "Para mudar esta, cancele e programe outra."
)
JA_PUBLICADA = "Esta sessão já está publicada."
CANCELADA_NAO_VOLTA = "Esta sessão foi cancelada e não pode voltar."
JA_CANCELADA = "Esta sessão já foi cancelada."


def editar_rascunho(sessao, *, filme, sala, inicio, preco):
    """Altera filme, sala, horário e preço — e a sessão CONTINUA em rascunho.

    Editar não publica. Publicar é uma ação com pré-condições próprias, e
    deixá-la acontecer por efeito colateral de uma edição esconderia essas
    pré-condições dentro de um formulário (FR-023).

    O conflito de `(sala, horário)` é recusado pelo MESMO caminho da criação: a
    constraint do banco, capturada pelo nome. Mover um rascunho para um horário
    ocupado é exatamente a mesma colisão, e merecia o mesmo dono.
    """
    if sessao.status != Screening.Status.DRAFT:
        raise EstadoInvalido(SO_RASCUNHO_E_EDITAVEL)

    sessao.movie = filme
    sessao.room = sala
    sessao.starts_at = inicio
    sessao.price = preco

    try:
        with transaction.atomic():
            sessao.save(update_fields=["movie", "room", "starts_at", "price"])
    except IntegrityError as exc:
        if CONSTRAINT_DE_HORARIO in str(exc):
            raise ConflitoDeHorario(sala, inicio) from exc
        raise

    return sessao


def publicar(sessao):
    """Coloca o rascunho à venda, revalidando as pré-condições no servidor.

    A interface já recebeu `pode_publicar` na grade e desabilitou o botão — e
    isso é conveniência, nunca autorização. As três condições são conferidas
    aqui de novo, com os mesmos `erros_para_publicar` que a criação usa
    (FR-030, FR-037).
    """
    if sessao.status == Screening.Status.PUBLISHED:
        raise EstadoInvalido(JA_PUBLICADA)
    if sessao.status == Screening.Status.CANCELLED:
        raise EstadoInvalido(CANCELADA_NAO_VOLTA)

    erros = erros_para_publicar(sessao.room, sessao.starts_at)
    if erros:
        raise CondicoesDePublicacao(erros)

    sessao.status = Screening.Status.PUBLISHED
    sessao.save(update_fields=["status"])
    return sessao


def cancelar(sessao):
    """Para de vender. E MAIS NADA.

    Vale para rascunho E para publicada (FR-030): sem o cancelamento de
    rascunho, um rascunho errado ficaria na grade para sempre, já que apagar
    sessão está fora de escopo.

    O QUE ESTA FUNÇÃO NÃO FAZ, e nenhum teste pode afrouxar (FR-031): não
    estorna `Payment`, não apaga `Ticket`, não apaga `ReservedSeat`, não mexe
    em `used_at`, não devolve ao estoque lugar já pago. Ela muda UMA coluna.

    O ingresso de uma sessão cancelada continua no histórico do cliente (009) e
    sai como "sessão errada" na portaria, com o aviso do cancelamento (010) —
    os dois comportamentos já existem e não são reabertos aqui.

    Cancelada é TERMINAL: não há "descancelar". Reabrir a venda de uma sessão
    que já foi anunciada como cancelada é uma promessa nova para quem leu a
    primeira, e ninguém pediu essa.
    """
    if sessao.status == Screening.Status.CANCELLED:
        raise EstadoInvalido(JA_CANCELADA)

    sessao.status = Screening.Status.CANCELLED
    sessao.save(update_fields=["status"])
    return sessao
