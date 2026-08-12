"""Gerar e revogar o link de compartilhamento de um ingresso.

POR QUE ESTE ARQUIVO NÃO É `services/ingressos.py`
--------------------------------------------------
Aquele módulo é **puro** por decisão da 008: não importa modelo, não recebe
`request`, não toca o banco. A ausência não é estilo — é o que torna
verificável a exigência do Princípio III de que a portaria confira a
assinatura ANTES de qualquer consulta, e `test_ticket_signature.py` a fixa com
`django_assert_num_queries(0)`.

Gerar e revogar link escrevem no banco. Se morassem lá, a garantia da 008
deixaria de vir da estrutura e passaria a depender de disciplina.

O SEGUNDO SEGREDO
-----------------
O token daqui **não** é o código do QR e não deriva dele. Este módulo não
conhece a `TICKET_SIGNING_KEY`, e `services/ingressos.py` não conhece a
existência de link nenhum. Revogar um convite não pode queimar uma entrada
paga; o ingresso não pode depender de link para valer na catraca.
`test_ticket_signature.py` compara o código antes e depois de revogar — é o
teste que pega o dia em que alguém "simplificar" fundindo os dois.
"""

import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.screening.models import TicketShareLink

# 32 bytes → 256 bits, 43 caracteres em base64 url-safe.
#
# O link é CREDENCIAL AO PORTADOR: quem o tem, tem o ingresso. Adivinhar
# precisa ser inviável por qualquer margem que importe (FR-025), e o token não
# pode derivar de nada — nem da chave primária, nem do `public_id`, nem da
# reserva, nem do pagamento, nem do código assinado (FR-026, FR-027).
BYTES_DO_TOKEN = 32


def _novo_token():
    return secrets.token_urlsafe(BYTES_DO_TOKEN)


def link_ativo(ingresso):
    """O link ativo daquele ingresso, ou `None`."""
    return ingresso.share_links.filter(revoked_at__isnull=True).first()


def gerar_link(ingresso):
    """Devolve `(link, criou)`. IDEMPOTENTE do ponto de vista de quem pede.

    Já havendo link ativo, devolve o mesmo — nunca um segundo em paralelo
    (FR-028). Vários links ativos multiplicariam credenciais que o dono teria
    de revogar uma a uma, achando que revogou tudo ao revogar a que vê.

    A CORRIDA, que é o ponto:

        1. procurar link ativo → achou? devolve.
        2. não achou → INSERT dentro de atomic().
        3. `IntegrityError` na constraint? Outra requisição venceu entre 1 e
           2. Relê e devolve o link DELA.

    O passo 3 não é tratamento de erro, é a feature. "Consultar se existe e
    criar se não" é o padrão exato que a concorrência quebra: duas requisições
    consultam, nenhuma encontra, ambas criam. Quem perde não vê erro — vê
    idempotência, que é o que pediu.

    NÃO HÁ `SELECT FOR UPDATE`, e a ausência é escolha. Na 007 o bloqueio era
    necessário porque havia leitura-antes-de-escrita sobre linhas de
    TERCEIROS (ocupações vencidas de outras reservas). Aqui a única linha em
    jogo é a que está sendo criada, e a constraint resolve sozinha.
    Acrescentar bloqueio moveria a garantia do banco para a aplicação — o
    oposto do que o Princípio II pede.
    """
    existente = link_ativo(ingresso)
    if existente is not None:
        return existente, False

    try:
        # `atomic` próprio: sem ele, o `IntegrityError` marcaria a transação
        # externa como quebrada e a releitura abaixo falharia.
        with transaction.atomic():
            return (
                TicketShareLink.objects.create(
                    ticket=ingresso, token=_novo_token()
                ),
                True,
            )
    except IntegrityError:
        vencedor = link_ativo(ingresso)
        if vencedor is None:
            # Colisão de `token`, não de ingresso — probabilidade
            # desprezível em 256 bits, mas engolir a exceção aqui
            # transformaria o improvável em silencioso.
            raise
        return vencedor, False


def revogar_link(ingresso):
    """Revoga o link ativo. Idempotente, e devolve o estado final (`None`).

    `UPDATE` CONDICIONAL, não leitura seguida de escrita: a condição
    `revoked_at IS NULL` mora no próprio `WHERE`. Duas revogações simultâneas
    resultam em uma linha afetada e uma não afetada, e as duas respondem
    "revogado" — que é o estado que ambas queriam.

    A LINHA NUNCA É APAGADA (FR-031, FR-043). Preservá-la faz duas coisas:

      - o token morto continua ocupando o espaço dele sob a `UNIQUE` da
        coluna, então nem o gerador nem um bug de reatribuição conseguem
        ressuscitá-lo;
      - a consulta pública responde a um token revogado exatamente como a um
        que nunca existiu, sem depender de sorte.

    E NADA EM `Ticket` É TOCADO. O código do QR é derivado de `public_id` +
    sessão num módulo que não sabe que este arquivo existe.
    """
    ingresso.share_links.filter(revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    return None
