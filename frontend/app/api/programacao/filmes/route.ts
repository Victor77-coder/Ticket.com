import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postImportarFilme } from "@/lib/api";

/**
 * `POST /api/programacao/filmes` — traz o filme escolhido na busca.
 *
 * Status e corpo vão inteiros e sem alteração. O `200` de filme que já existia
 * **não é erro** e chega como `200` — a interface distingue "trouxe agora" de
 * "já era seu" pelo status, sem interpretar texto (FR-012).
 */

export const dynamic = "force-dynamic";

const REQUISICAO_INVALIDA = { detail: "Requisição inválida." };

export async function POST(request: Request) {
  let corpo: Record<string, unknown>;
  try {
    corpo = await request.json();
  } catch {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const tmdbId = Number(corpo.tmdb_id);
  if (!Number.isInteger(tmdbId) || tmdbId <= 0) {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;
  const resultado = await postImportarFilme(sessionKey, tmdbId);

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
