import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { COOKIE_SESSAO, fetchSession } from "@/lib/api";
import { devolverParaCasa } from "@/lib/papeis";

/**
 * Mantém cada papel na tela dele.
 *
 * Hoje isso quer dizer uma coisa só: a **portaria** valida ingressos e não
 * navega pelo catálogo. Ela fica na porta; o catálogo é a tela de quem compra,
 * e oferecê-lo a ela é oferecer uma viagem que termina em recusa.
 *
 * POR QUE AQUI, E NÃO EM CADA PÁGINA. Esta é a terceira vez neste projeto que
 * uma regra de alcance precisa valer para *todas* as telas — e as duas
 * primeiras vazaram justamente por serem aplicadas página a página: o menu da
 * conta ganhou um destino e o resto do sistema não soube, e depois a entrada
 * pousava no lugar errado. Uma lista de páginas proibidas esquece a página que
 * alguém acrescentar amanhã. O middleware **nega por padrão**: a tela nova
 * nasce coberta sem ninguém precisar lembrar.
 *
 * ISTO É PRODUTO, NÃO SEGURANÇA. O catálogo é PÚBLICO — um visitante vê as
 * mesmas páginas, e a portaria veria tudo isso bastando sair da conta. Não há
 * nada a proteger aqui. A autorização de verdade continua no servidor, e é ela
 * que devolve `403` quando a portaria tenta reservar, pagar ou abrir ingressos
 * de cliente. Se um dia esta regra sumir, nada fica exposto — só volta a ser
 * confuso.
 *
 * O CUSTO, dito claramente: resolver o papel exige perguntar ao Django quem é o
 * dono da sessão, e o layout raiz já faz essa mesma pergunta a cada página.
 * Para quem está autenticado, são duas chamadas por navegação em vez de uma.
 * Aceitável na escala deste projeto, e o caminho barato — guardar o papel num
 * cookie legível pelo navegador — foi rejeitado por criar um segundo lugar para
 * a verdade morar, que é exatamente a classe de erro que este arquivo existe
 * para fechar. Visitante não paga nada: sem cookie, sai antes de perguntar.
 */

export async function middleware(request: NextRequest) {
  const chave = request.cookies.get(COOKIE_SESSAO)?.value;

  // Visitante não tem papel a respeitar, e não paga a consulta.
  if (!chave) return NextResponse.next();

  const sessao = await fetchSession(chave);

  // Sessão vencida ou recusada é estado normal: quem decide o que fazer com
  // isso é a página, como sempre foi (FR-017 da 003).
  if (!sessao.ok) return NextResponse.next();

  const destino = devolverParaCasa(sessao.data.papel, request.nextUrl.pathname);
  if (!destino) return NextResponse.next();

  return NextResponse.redirect(new URL(destino, request.url));
}

export const config = {
  /**
   * Tudo, menos o que não é página.
   *
   * `api` fica de fora porque os Route Handlers são o caminho do próprio
   * navegador até o Django — bloquear `/api/validar` para a portaria seria
   * bloquear exatamente o que ela veio fazer. A autorização deles é do
   * servidor.
   */
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
