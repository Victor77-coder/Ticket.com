/**
 * Resolução da sessão no servidor.
 *
 * Componentes de servidor chamam `getSessao()` e recebem a sessão já
 * resolvida — sem piscar entre "Entrar" e o nome do usuário, que é o defeito
 * mais visível de fazer isso no cliente (R6).
 *
 * O papel volta daqui para a interface **escolher o que apresentar**, nunca
 * para conceder acesso. Ele é resolvido no servidor a cada requisição;
 * guardá-lo no navegador criaria a ilusão de que dá para confiar nele
 * (FR-022, Princípio IV).
 */

import { cookies } from "next/headers";

import { COOKIE_SESSAO, fetchSession } from "./api";
import type { Sessao } from "./types";

/** Sessão ativa, ou `null` para visitante. */
export async function getSessao(): Promise<Sessao | null> {
  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;
  if (!chave) return null;

  const resultado = await fetchSession(chave);

  // 401 é estado normal: a sessão expirou ou nunca existiu. O visitante segue
  // navegando e o cabeçalho volta a convidar a entrar — nunca uma página de
  // erro (FR-017).
  return resultado.ok ? resultado.data : null;
}

/**
 * Valida o destino de retorno após a entrada (FR-011, R7).
 *
 * `//exemplo.com` e `/\exemplo.com` são lidos por navegadores como endereços
 * absolutos — é a forma clássica de transformar um parâmetro de retorno em
 * redirecionamento aberto, que serve para phishing convincente porque o link
 * parte do site legítimo.
 *
 * A validação é por forma, não por lista de destinos: qualquer rota interna
 * futura continua funcionando sem manutenção.
 */
export function caminhoDeRetornoSeguro(valor: string | null | undefined): string {
  if (!valor) return "/";
  if (!valor.startsWith("/")) return "/";
  if (valor.startsWith("//")) return "/";
  if (valor.startsWith("/\\")) return "/";

  // Barras invertidas em qualquer posição inicial: alguns navegadores as
  // normalizam para barra, reabrindo o mesmo buraco.
  if (/^\/[\\/]/.test(valor)) return "/";

  return valor;
}
