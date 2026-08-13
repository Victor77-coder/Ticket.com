import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postSala } from "@/lib/api";

/**
 * `POST /api/programacao/salas` — criar sala, pelo navegador.
 *
 * Status e corpo inteiros e sem alteração: as frases de capacidade fora dos
 * limites já vêm do Django com o teto calculado dentro delas, e reescrevê-las
 * aqui faria a mensagem parar de acompanhar `SEATS_PER_ROW`.
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

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  const resultado = await postSala(sessionKey, {
    nome: String(corpo.nome ?? ""),
    capacidade: Number(corpo.capacidade),
  });

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
