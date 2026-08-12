import type { Papel } from "./types";

/**
 * A casa de cada papel — onde ele faz o que veio fazer.
 *
 * UMA TABELA, DOIS CONSUMIDORES: o item do menu da conta e o destino logo
 * depois da entrada. Manter os dois numa tabela só é o que impede o caso que já
 * aconteceu uma vez neste projeto — o menu ganhar um destino e o resto do
 * sistema não saber dele.
 *
 * `telaUnica` é UM fato com TRÊS consequências, e elas andam juntas de
 * propósito — separá-las em três campos seria convidá-las a divergir:
 *
 *   1. o papel **pousa** na tela dele ao entrar;
 *   2. o papel **não alcança** nenhuma outra página;
 *   3. o cabeçalho não oferece navegação que ele não pode usar.
 *
 * A PORTARIA tem tela única: ela fica na porta validando, não navega pelo
 * site, e o catálogo de filmes é a tela de quem compra. Oferecer o catálogo a
 * ela é oferecer uma viagem que termina em recusa.
 *
 * O CLIENTE não tem. A casa de trabalho dele é "Meus ingressos", mas ele
 * circula pelo site inteiro — e **pousa no catálogo**, porque entra para
 * COMPRAR e comprar vem antes de ter ingresso. Mandá-lo direto para a lista
 * faria um cliente novo aterrissar no estado vazio.
 *
 * `organizer` está AUSENTE de propósito. O painel dele ainda não existe, e
 * apontar para uma tela que recusa por papel é pior do que não apontar para
 * nada: o item viraria convite a um beco sem saída. Quando o painel existir,
 * ele entra aqui e as duas telas passam a conhecê-lo de graça.
 */
export const CASA_DO_PAPEL: Partial<
  Record<Papel, { href: string; rotulo: string; telaUnica: boolean }>
> = {
  customer: { href: "/meus-ingressos", rotulo: "Meus ingressos", telaUnica: false },
  gate: { href: "/portaria", rotulo: "Validar ingressos", telaUnica: true },
};

/** O papel tem uma tela só, e é lá que ele vive. */
export function temTelaUnica(papel: Papel): boolean {
  return CASA_DO_PAPEL[papel]?.telaUnica ?? false;
}

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
  return casa?.telaUnica ? casa.href : "/";
}

/**
 * Para onde devolver um papel de tela única que saiu da tela dele.
 *
 * Devolve `null` quando não há nada a fazer — papel sem tela única, ou já
 * está onde deveria.
 *
 * DENY POR PADRÃO: qualquer caminho que não seja a casa do papel devolve o
 * redirecionamento. É o oposto de uma lista de páginas proibidas, e é
 * deliberado — uma lista de proibidas esquece a página que alguém acrescentar
 * amanhã, e este projeto já foi mordido duas vezes por "esqueci de atualizar o
 * outro lugar".
 *
 * `/entrar` NÃO é exceção: um papel de tela única que abra a entrada já tendo
 * sessão volta para a tela dele, que é exatamente o que a própria página de
 * entrada já faz. Não há laço — a casa nunca redireciona para si mesma.
 *
 * ISTO É PRODUTO, NÃO SEGURANÇA, e a distinção importa para não dar a
 * impressão errada: o catálogo é PÚBLICO — um visitante vê as mesmas páginas.
 * Bloquear a portaria não protege nada; evita oferecer a ela uma viagem que
 * termina em recusa. A autorização de verdade continua onde sempre esteve, no
 * servidor, e é ela que devolve 403 quando a portaria tenta reservar ou pagar.
 */
export function devolverParaCasa(papel: Papel, caminho: string): string | null {
  const casa = CASA_DO_PAPEL[papel];
  if (!casa?.telaUnica) return null;

  const jaEstaEmCasa = caminho === casa.href || caminho.startsWith(`${casa.href}/`);
  return jaEstaEmCasa ? null : casa.href;
}
