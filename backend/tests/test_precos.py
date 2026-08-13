from decimal import Decimal

import pytest

from apps.screening.services import precos

# A TABELA DE CASOS É COMPARTILHADA com `frontend/tests/meia.test.ts`.
#
# Ela é o que faz a conta do servidor e o espelho do navegador concordarem por
# VERIFICAÇÃO, e não por presunção. Mudar um valor aqui sem mudar lá é o defeito
# que os dois arquivos existem para impedir — e é por isso que os dois trazem os
# mesmos pares, escritos na mesma ordem.
CASOS = [
    ("32.00", "16.00"),  # exato
    ("45.00", "22.50"),  # exato, ímpar em reais
    ("25.01", "12.50"),  # centavo ímpar → PARA BAIXO (12,505 → 12,50)
    ("25.03", "12.51"),  # o outro lado do mesmo ímpar (12,515 → 12,51)
    ("0.01", "0.00"),  # um centavo não tem metade em centavos
    ("0.00", "0.00"),  # sessão gratuita continua gratuita
    ("19.99", "9.99"),  # 9,995 → 9,99
]


@pytest.mark.parametrize("preco,esperado", CASOS)
def test_meia_e_metade_arredondada_para_baixo(preco, esperado):
    assert precos.valor_do_lugar(Decimal(preco), precos.TipoDeIngresso.MEIA) == Decimal(esperado)


@pytest.mark.parametrize("preco,_", CASOS)
def test_inteira_e_o_preco_da_sessao(preco, _):
    assert precos.valor_do_lugar(Decimal(preco), precos.TipoDeIngresso.INTEIRA) == Decimal(preco)


def test_arredonda_para_baixo_e_nao_pelo_padrao_do_decimal():
    """O padrão do `Decimal` é ROUND_HALF_EVEN, e ele erraria aqui.

    Com HALF_EVEN, 12,505 vira 12,50 (par) e 12,515 vira 12,52 (par) — dois
    ímpares vizinhos arredondando para lados diferentes. Correto
    estatisticamente, incompreensível numa tabela de preços exibida ao cliente.
    """
    assert precos.valor_do_lugar(Decimal("25.01"), precos.TipoDeIngresso.MEIA) == Decimal("12.50")
    assert precos.valor_do_lugar(Decimal("25.03"), precos.TipoDeIngresso.MEIA) == Decimal("12.51")


def test_o_valor_tem_sempre_duas_casas():
    """Duas casas exatas, porque é o que vai para a coluna.

    Um valor com mais casas gravado numa coluna de duas seria arredondado pelo
    banco — e aí "exibido" e "cobrado" divergiriam sem ninguém decidir isso.
    """
    valor = precos.valor_do_lugar(Decimal("25.01"), precos.TipoDeIngresso.MEIA)
    assert valor.as_tuple().exponent == -2


def test_tipo_desconhecido_e_erro_e_nao_meia_silenciosa():
    """Falhar alto, e não cobrar menos.

    Um tipo que ninguém reconhece caindo no ramo da meia seria desconto
    concedido por engano de digitação.
    """
    with pytest.raises(ValueError):
        precos.valor_do_lugar(Decimal("32.00"), "estudante")
