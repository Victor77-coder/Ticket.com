import type { Papel } from "./types";

/**
 * A casa de cada papel — onde ele faz o que veio fazer.
 *
 * UMA TABELA, DOIS CONSUMIDORES: o item do menu da conta e o destino logo
 * depois da entrada. Manter os dois numa tabela só é o que impede o caso que já
 * aconteceu uma vez neste projeto — o menu ganhar um destino e o resto do
 * sistema não saber dele.
 *
 * DOIS FATOS, E ELES SE SEPARARAM NA 013. Até a portaria ser o único papel
 * confinado, "pousa aqui ao entrar" e "não alcança mais nada" andavam juntos, e
 * este arquivo afirmava que separá-los seria convidá-los a divergir. O
 * organizador é o contraexemplo que dividiu a afirmação:
 *
 *   `pousa`      — o papel aterrissa na tela dele ao entrar;
 *   `telaUnica`  — o papel não alcança nenhuma outra página, e o cabeçalho não
 *                  lhe oferece navegação que ele não pode usar.
 *
 * A PORTARIA tem os dois. Ela fica na porta validando, não navega pelo site, e
 * o catálogo é a tela de quem compra — oferecê-lo a ela é oferecer uma viagem
 * que termina em recusa.
 *
 * O ORGANIZADOR tem só o primeiro, e a diferença é a razão de o campo existir:
 * ele **precisa** do catálogo público, porque é ali que ele confere que a
 * sessão que acabou de publicar apareceu à venda (FR-004). Registrá-lo com
 * `telaUnica: true` o trancaria fora justamente da tela onde ele verifica o
 * próprio trabalho — e o middleware nega por padrão, então isso não daria erro
 * nenhum: daria um organizador preso, com a suíte inteira passando.
 *
 * O CLIENTE não tem nenhum dos dois. A casa de trabalho dele é "Meus
 * ingressos", mas ele circula pelo site inteiro e **pousa no catálogo**, porque
 * entra para COMPRAR e comprar vem antes de ter ingresso. Mandá-lo direto para
 * a lista faria um cliente novo aterrissar no estado vazio — e essa é a
 * regressão mais provável desta mudança, fixada por teste próprio.
 */
export const CASA_DO_PAPEL: Partial<
  Record<Papel, { href: string; rotulo: string; pousa: boolean; telaUnica: boolean }>
> = {
  customer: {
    href: "/meus-ingressos",
    rotulo: "Meus ingressos",
    pousa: false,
    telaUnica: false,
  },
  gate: { href: "/portaria", rotulo: "Validar ingressos", pousa: true, telaUnica: true },
  organizer: { href: "/programacao", rotulo: "Programação", pousa: true, telaUnica: false },
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
 *
 * LÊ `pousa`, e não `telaUnica`. Era `telaUnica` até a 013, quando pousar
 * deixou de implicar ficar preso: o organizador aterrissa no painel e continua
 * alcançando o catálogo.
 */
export function destinoAposEntrada(papel: Papel, caminhoDeRetorno: string): string {
  // "/" é o que `caminhoDeRetornoSeguro` devolve quando NÃO houve pedido — é
  // por isso que ele significa "sem destino", e não "leve-me à home".
  if (caminhoDeRetorno !== "/") return caminhoDeRetorno;

  const casa = CASA_DO_PAPEL[papel];
  return casa?.pousa ? casa.href : "/";
}

/**
 * Para onde devolver um papel de tela única que saiu da tela dele.
 *
 * Devolve `null` quando não há nada a fazer — papel sem tela única, ou já
 * está onde deveria.
 *
 * CONTINUA LENDO `telaUnica`, E ISSO É INVARIANTE. Se um dia esta função
 * passar a consultar `pousa`, a portaria não muda de comportamento e o
 * organizador perde a home — o sintoma aparece longe da causa, numa tela que
 * ninguém associaria a este arquivo. `devolverParaCasa("organizer", …)`
 * devolve `null` para qualquer caminho, e há teste fixando isso.
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
 * servidor, e é ela que devolve 403 quando a portaria tenta reservar, pagar ou
 * programar.
 */
export function devolverParaCasa(papel: Papel, caminho: string): string | null {
  const casa = CASA_DO_PAPEL[papel];
  if (!casa?.telaUnica) return null;

  const jaEstaEmCasa = caminho === casa.href || caminho.startsWith(`${casa.href}/`);
  return jaEstaEmCasa ? null : casa.href;
}
