/**
 * A metade do preço, no navegador — e a palavra "prévia" é o contrato inteiro.
 *
 * ESTE ARQUIVO É ESPELHO, NUNCA FONTE. Quem decide quanto custa é
 * `backend/apps/screening/services/precos.py`, e nenhum valor calculado aqui é
 * enviado ao servidor. Depois que a reserva existe, todo valor exibido vem dela.
 *
 * A alternativa honesta seria não exibir total nenhum antes de reservar, e ela é
 * pior: a pessoa marca duas meias e não vê o efeito antes de se comprometer.
 * Então o espelho existe, e o que impede a divergência de virar defeito de
 * cobrança são duas coisas:
 *
 *   1. o servidor ignora qualquer total vindo do cliente — a prévia não tem
 *      caminho para virar cobrança nem "só para conferência";
 *   2. `tests/meia.test.ts` e `backend/tests/test_precos.py` compartilham a
 *      MESMA tabela de casos. Os dois lados concordarem é verificado.
 *
 * Sem formatação aqui: escrever "R$" é de `lib/moeda.ts`, que já tem dono.
 */

/** Os dois tipos de ingresso. Fechado de propósito: não é catálogo. */
export type TipoDeIngresso = "inteira" | "meia";

/**
 * O valor de um lugar, em centavos inteiros.
 *
 * Centavos e não reais porque o binário do JavaScript não representa 0,1 — e
 * `32.10 / 2` já sai com cauda. Inteiro divide exato, e o descarte da divisão
 * inteira JÁ É o arredondamento para baixo que a regra pede.
 */
export function centavosDoLugar(precoDaSessao: string | number, tipo: TipoDeIngresso): number {
  const centavos = Math.round(Number(precoDaSessao) * 100);
  return tipo === "meia" ? Math.floor(centavos / 2) : centavos;
}

/** O mesmo valor em reais, para quem vai formatar. */
export function valorDoLugar(precoDaSessao: string | number, tipo: TipoDeIngresso): number {
  return centavosDoLugar(precoDaSessao, tipo) / 100;
}

/** A soma da seleção — a prévia que o resumo exibe antes de reservar. */
export function totalPrevisto(
  precoDaSessao: string | number,
  tipos: readonly TipoDeIngresso[],
): number {
  const centavos = tipos.reduce((soma, tipo) => soma + centavosDoLugar(precoDaSessao, tipo), 0);
  return centavos / 100;
}
