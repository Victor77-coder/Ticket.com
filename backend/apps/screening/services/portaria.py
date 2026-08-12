"""A validação do ingresso na entrada — os quatro desfechos.

POR QUE ESTE ARQUIVO NÃO É `services/ingressos.py`
--------------------------------------------------
Aquele módulo é PURO por decisão da 008: não importa modelo, não recebe
`request`, não toca o banco. A ausência não é estilo — é o que torna
verificável a exigência do Princípio III de conferir a assinatura antes de
qualquer consulta. A validação escreve. Se morasse lá, a garantia da 008
deixaria de vir da estrutura e passaria a depender de disciplina.

É a mesma separação que a 009 fez com `services/compartilhamento.py`, pelo
mesmo motivo, e a essa altura é padrão do projeto.

A ORDEM DAS ETAPAS NÃO É ESTILO. Trocar duas delas quebra uma garantia:

    1. assinatura confere?              não → INVÁLIDO   [sem tocar o banco]
    2. ingresso existe?                 não → INVÁLIDO
    3. o `s` do código bate com a
       sessão do ingresso no banco?     não → INVÁLIDO
    4. a sessão do ingresso é a
       sessão DA PORTA?                 não → SESSÃO ERRADA  [NÃO ESCREVE]
    5. UPDATE condicional               0 linhas → JÁ UTILIZADO
                                        1 linha  → VÁLIDO

**1 vem antes de tudo** por causa do Princípio III, e
`tests/test_gate_signature.py` fixa isso com `num_queries(0)`.

**2 e 3 devolvem o MESMO inválido**: quem apresenta não recebe pista sobre
onde o palpite chegou perto. O passo 3 é defesa em profundidade — o `s` é
assinado e confiável, mas comparar com o banco custa nada e transforma uma
inconsistência num desfecho em vez de numa exceção.

**4 vem antes de 5**, e é decisão de produto registrada na spec (FR-030): um
ingresso de outra sessão E já utilizado responde SESSÃO ERRADA, porque é essa
a informação que muda a ação do operador. A ordem inversa consumiria o
desfecho mais útil.

**4 não escreve** (FR-031). É o que faz o ingresso continuar valendo na porta
certa. Queimar um ingresso legítimo na porta errada seria pior do que não ter
a checagem.

**5 é a única escrita da feature inteira.**
"""

from dataclasses import dataclass

from django.db.models.functions import Now

from apps.screening.models import Screening, Ticket
from apps.screening.services import ingressos as ingressos_service

# Os quatro desfechos do Princípio III. Valores fixos, nunca frases: a frase é
# apresentação e muda numa revisão de redação; a tela escolhe símbolo e título
# por ESTE valor.
VALIDO = "valido"
INVALIDO = "invalido"
JA_UTILIZADO = "ja_utilizado"
SESSAO_ERRADA = "sessao_errada"


@dataclass(frozen=True)
class Resultado:
    """O desfecho de uma apresentação.

    `ingresso`, `sessao_do_ingresso` e `utilizado_em` são `None` em INVÁLIDO —
    e a ausência é requisito, não descuido: qualquer detalhe a mais entregaria
    a quem tenta adivinhar a informação que o desfecho existe para negar.
    """

    situacao: str
    ingresso: Ticket | None = None
    sessao_do_ingresso: Screening | None = None
    utilizado_em: object | None = None


def validar(codigo, sessao_id):
    """Valida um código contra a sessão que esta porta está recebendo.

    `sessao_id` é a SESSÃO DA PORTA, escolhida pelo operador. Sem ela o
    desfecho "sessão errada" seria impossível: o código diz a que sessão o
    ingresso pertence, e comparar esse valor com ele mesmo sempre dá igual.
    Ver a seção "A decisão de produto que a spec fixa" em spec.md.
    """
    # --- 1. Assinatura. NENHUMA consulta acontece nesta etapa. ---
    try:
        conteudo = ingressos_service.verificar_codigo(
            codigo.strip() if isinstance(codigo, str) else codigo
        )
    except ingressos_service.CodigoInvalido:
        return Resultado(situacao=INVALIDO)

    # --- 2. O ingresso existe? ---
    ingresso = (
        Ticket.objects.select_related(
            "reserved_seat__seat",
            "reserved_seat__screening__movie",
            "reserved_seat__screening__room",
        )
        .filter(public_id=conteudo["ticket"])
        .first()
    )
    if ingresso is None:
        # MESMO desfecho da assinatura ruim (FR-029).
        return Resultado(situacao=INVALIDO)

    sessao_do_ingresso = ingresso.reserved_seat.screening

    # --- 3. O código e o banco concordam? ---
    if conteudo["screening"] != sessao_do_ingresso.pk:
        # Inconsistência de dados. Vira desfecho, nunca exceção.
        return Resultado(situacao=INVALIDO)

    # --- 4. É esta porta? NÃO ESCREVE. ---
    if sessao_do_ingresso.pk != int(sessao_id):
        return Resultado(
            situacao=SESSAO_ERRADA,
            ingresso=ingresso,
            sessao_do_ingresso=sessao_do_ingresso,
        )

    # --- 5. A marcação. A ÚNICA escrita. ---
    #
    # UM `UPDATE` CONDICIONAL, e o número de linhas afetadas É O DESFECHO.
    #
    # ==================== NÃO TROQUE ISTO POR ISTO ====================
    #
    #     if ingresso.used_at is not None:
    #         return Resultado(situacao=JA_UTILIZADO)
    #     ingresso.used_at = timezone.now()
    #     ingresso.save(update_fields=["used_at"])
    #     return Resultado(situacao=VALIDO)
    #
    # É leitura seguida de escrita. Duas requisições leem `None`, ambas passam
    # pelo `if`, ambas escrevem — e DUAS PESSOAS ENTRAM COM O MESMO INGRESSO.
    #
    # É a versão mais perigosa desse erro em todo o projeto, por três razões
    # somadas:
    #
    #   1. passa em todo teste de UMA thread só;
    #   2. LÊ EXATAMENTE COMO A REGRA DA SPEC — "se já foi usado responda já
    #      utilizado, senão marque" é o texto do requisito, e uma revisão
    #      atenta aprova;
    #   3. o banco NÃO RECLAMA. Nas features 007, 008 e 009 havia uma
    #      constraint recusando a segunda escrita; aqui as duas são legais, e
    #      a segunda só sobrescreve o instante.
    #
    # A única defesa é `tests/test_gate_concurrency.py`. Ver T070 do tasks.md.
    # ==================================================================
    #
    # `Now()` é a função do BANCO, e não `timezone.now()`: o instante gravado é
    # o do servidor de banco, o mesmo relógio que serializa as duas escritas.
    linhas = Ticket.objects.filter(pk=ingresso.pk, used_at__isnull=True).update(
        used_at=Now()
    )

    if linhas == 0:
        # Outra validação venceu — nesta ou noutra porta. Reler é necessário
        # para informar QUANDO (FR-021), e é a única razão de reler.
        ingresso.refresh_from_db(fields=["used_at"])
        return Resultado(
            situacao=JA_UTILIZADO,
            ingresso=ingresso,
            sessao_do_ingresso=sessao_do_ingresso,
            utilizado_em=ingresso.used_at,
        )

    ingresso.refresh_from_db(fields=["used_at"])
    return Resultado(
        situacao=VALIDO,
        ingresso=ingresso,
        sessao_do_ingresso=sessao_do_ingresso,
        utilizado_em=ingresso.used_at,
    )
