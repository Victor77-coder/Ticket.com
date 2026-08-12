"""O código do ingresso: assinar, verificar e desenhar.

ESTE MÓDULO É PURO. Não importa modelo, não recebe `request`, não toca o
banco — e a ausência não é estilo, é o que torna FR-034 verificável.

O Princípio III exige que a portaria confira a assinatura ANTES de qualquer
consulta ao banco. Escrever isso é fácil; violá-lo sem perceber também, porque
basta alguém acrescentar um `.exists()` de conveniência aqui dentro. Com o
módulo sem acesso a modelo, a garantia vem da estrutura em vez de vir da
disciplina — e `test_ticket_signature.py` fixa isso com
`django_assert_num_queries(0)`.

No dia em que este arquivo importar um modelo, a garantia deixa de existir.
"""

import base64
import json
from uuid import UUID

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.core import signing

# Separação de DOMÍNIO, que é diferente de separação de segredo.
#
# A chave (`TICKET_SIGNING_KEY`) é o que impede forjar. O salt é o que impede
# que uma assinatura de ingresso valha em outro contexto que venha a usar a
# mesma chave. Os dois são necessários e nenhum substitui o outro.
SALT = "ingresso.qr"


def _assinador():
    """`Signer`, e deliberadamente NÃO `TimestampSigner`.

    `signing.dumps()` seria o atalho óbvio e usa `TimestampSigner` por dentro —
    o que traz duas coisas indesejadas, e a segunda só apareceu ao rodar o e2e:

      1. VALIDADE TEMPORAL. Um ingresso não caduca por relógio; ele é
         consumido na portaria. Um `max_age` mal configurado invalidaria
         ingresso legítimo na fila da entrada.
      2. CÓDIGO INSTÁVEL. Com o instante dentro da assinatura, o MESMO
         ingresso produz um código diferente a cada renderização. Os dois
         verificariam — mas o ingresso deixaria de ter *um* código: quem
         imprimiu ou salvou o QR veria outro texto ao reabrir a confirmação, e
         comparar o que está no papel com o que está na tela ficaria
         impossível.

    `Signer` assina o mesmo conteúdo sempre. O ingresso tem um código, e ele é
    o mesmo hoje e amanhã.
    """
    return signing.Signer(key=settings.TICKET_SIGNING_KEY, salt=SALT)


class CodigoInvalido(Exception):
    """O código não foi assinado por este servidor, ou foi adulterado.

    Uma exceção só para as duas coisas, de propósito: para quem apresenta o
    código, "inventei" e "mexi num caractere" são o mesmo desfecho, e
    distinguir na resposta entregaria ao atacante um oráculo sobre onde o
    palpite chegou perto.
    """


def assinar_codigo(public_id, screening_id):
    """O conteúdo que vai para o QR.

    Dois campos, com nomes de uma letra: o QR cresce em densidade com o
    tamanho do conteúdo, e QR denso é o que falha de ler na câmera da
    portaria com pouca luz.

      t — identidade PÚBLICA do ingresso (uuid, nunca a chave primária:
          sequencial revelaria quantos ingressos existem e convidaria a
          tentar o vizinho — FR-032)
      s — identidade da SESSÃO. Está aqui por FR-033 e é para a feature
          seguinte: sem ela, um ingresso legítimo apresentado na porta errada
          seria indistinguível de um código forjado, e a portaria não teria
          como produzir o desfecho "sessão errada" que o Princípio III exige.

    O `s` entra agora, e não quando for consumido, porque acrescentá-lo depois
    mudaria a forma do conteúdo assinado e invalidaria todo código já emitido.
    """
    conteudo = json.dumps(
        {"s": int(screening_id), "t": str(public_id)},
        separators=(",", ":"),
        sort_keys=True,
    )
    return _assinador().sign(
        base64.urlsafe_b64encode(conteudo.encode("utf-8")).decode("ascii").rstrip("=")
    )


def verificar_codigo(codigo):
    """Devolve `{"ticket": UUID, "screening": int}`, ou levanta.

    Nenhuma consulta ao banco acontece aqui — nem para conferir que o
    ingresso existe. Isso é da camada de cima, e só depois de a assinatura
    passar.
    """
    if not isinstance(codigo, str) or not codigo:
        raise CodigoInvalido("código ausente")

    try:
        assinado = _assinador().unsign(codigo)
        preenchido = assinado + "=" * (-len(assinado) % 4)
        dados = json.loads(base64.urlsafe_b64decode(preenchido).decode("utf-8"))
    except signing.BadSignature as erro:
        # Assinatura que não confere: adulterado, inventado, ou assinado com
        # outra chave. Os três chegam aqui, e é correto que cheguem juntos.
        raise CodigoInvalido("assinatura inválida") from erro
    except Exception as erro:
        # Base64 quebrado, JSON quebrado, qualquer lixo. Também é código
        # inválido — nunca erro de sistema.
        raise CodigoInvalido("código ilegível") from erro

    if not isinstance(dados, dict) or "t" not in dados or "s" not in dados:
        raise CodigoInvalido("conteúdo incompleto")

    try:
        return {"ticket": UUID(str(dados["t"])), "screening": int(dados["s"])}
    except (ValueError, TypeError) as erro:
        raise CodigoInvalido("conteúdo malformado") from erro


def qr_data_uri(codigo):
    """O desenho do código, em SVG, pronto para entrar num `<img>`.

    SVG e não PNG: o ingresso precisa continuar legível em tela estreita, e
    vetor não pixeliza. Também dispensa Pillow — a saída raster arrastaria uma
    cadeia de bibliotecas de imagem para desenhar quadrados pretos.

    `data:` URI e não markup solto: entra em `<img src>` com `alt`, sem
    `dangerouslySetInnerHTML` no front. A imagem é REPRESENTAÇÃO do código; a
    verdade é o texto assinado, que viaja junto e é o que a portaria digita
    quando a câmera falha (FR-038).
    """
    imagem = qrcode.make(codigo, image_factory=qrcode.image.svg.SvgPathImage)

    bruto = imagem.to_string(encoding="unicode").encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(bruto).decode("ascii")
