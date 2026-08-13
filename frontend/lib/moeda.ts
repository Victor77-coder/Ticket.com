/**
 * O preço em real, com dono único.
 *
 * A mesma chamada de `Intl.NumberFormat` estava copiada em cinco arquivos — o
 * resumo da compra, a seleção de assentos, a página da sessão, a grade do
 * organizador e a confirmação do pagamento. Copiada, ela é o tipo de regra que
 * diverge em silêncio: basta alguém trocar a moeda ou o locale num lugar para a
 * mesma quantia sair escrita de dois jeitos em duas telas do mesmo fluxo.
 *
 * A API manda decimal como string ("32.00") para não perder precisão no
 * caminho. Converter aqui dentro é o que permite chamar isto com o que a
 * resposta entrega, sem cada consumidor lembrar do `Number()`.
 */
export function formatarPreco(valor: string | number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(valor));
}
