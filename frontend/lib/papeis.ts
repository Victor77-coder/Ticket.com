import type { Papel } from "./types";

/**
 * A casa de cada papel — onde ele faz o que veio fazer.
 *
 * UMA TABELA, DOIS CONSUMIDORES: o item do menu da conta e o destino logo
 * depois da entrada. Manter os dois numa tabela só é o que impede o caso que já
 * aconteceu uma vez neste projeto — o menu ganhar um destino e o resto do
 * sistema não saber dele.
 *
 * `entraDireto` separa dois fatos que só coincidem para alguns papéis:
 *
 *   - o **destino de trabalho** (o item do menu) é onde o papel faz o que veio
 *     fazer;
 *   - o **pouso após a entrada** é onde ele começa.
 *
 * Para a PORTARIA os dois são o mesmo lugar, porque ela tem uma tela só: não
 * navega pelo site, fica na porta validando. Cair no catálogo de filmes depois
 * de entrar é cair no lugar errado.
 *
 * Para o CLIENTE eles diferem, e é por isso que o campo existe. A casa de
 * trabalho dele é "Meus ingressos", mas o pouso é o catálogo — ele entra para
 * COMPRAR, e comprar vem antes de ter ingresso. Mandá-lo direto para a lista
 * faria um cliente novo aterrissar no estado vazio.
 *
 * `organizer` está AUSENTE de propósito. O painel dele ainda não existe, e
 * apontar para uma tela que recusa por papel é pior do que não apontar para
 * nada: o item viraria convite a um beco sem saída. Quando o painel existir,
 * ele entra aqui e as duas telas passam a conhecê-lo de graça.
 */
export const CASA_DO_PAPEL: Partial<
  Record<Papel, { href: string; rotulo: string; entraDireto: boolean }>
> = {
  customer: { href: "/meus-ingressos", rotulo: "Meus ingressos", entraDireto: false },
  gate: { href: "/portaria", rotulo: "Validar ingressos", entraDireto: true },
};

/**
 * Para onde levar alguém logo depois da entrada.
 *
 * UM DESTINO PEDIDO EXPLICITAMENTE SEMPRE VENCE. Quem foi conduzido à entrada
 * ao tentar abrir uma página quer voltar àquela página — mandá-lo para a casa
 * do papel dele descartaria a intenção que o trouxe até aqui, e quebraria o
 * retorno seguro que a 003 entregou.
 *
 * `caminhoDeRetorno` já vem validado por `caminhoDeRetornoSeguro` (FR-011): um
 * destino externo nunca chega até aqui.
 */
export function destinoAposEntrada(papel: Papel, caminhoDeRetorno: string): string {
  // "/" é o que `caminhoDeRetornoSeguro` devolve quando NÃO houve pedido — é
  // por isso que ele significa "sem destino", e não "leve-me à home".
  if (caminhoDeRetorno !== "/") return caminhoDeRetorno;

  const casa = CASA_DO_PAPEL[papel];
  return casa?.entraDireto ? casa.href : "/";
}
