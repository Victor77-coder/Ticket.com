import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, fetchBuscaTmdb } from "@/lib/api";

/**
 * `GET /api/programacao/filmes/busca?q=` — a busca no TMDb, pelo navegador.
 *
 * É AQUI QUE A CHAVE NÃO PASSA. O navegador fala com este handler, ele fala
 * com o Django, e só o Django fala com o TMDb — a chave nunca entra no bundle
 * nem no tráfego que o navegador enxerga (FR-010, Princípio VII).
 *
 * O `502` do TMDb fora do ar é repassado inteiro, com a frase que o
 * `TMDBError` escreveu em português. Traduzir aqui criaria a segunda redação
 * da mesma falha.
 */

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const termo = new URL(request.url).searchParams.get("q") ?? "";
  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  const resultado = await fetchBuscaTmdb(sessionKey, termo);

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
