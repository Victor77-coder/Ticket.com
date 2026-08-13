import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, patchSessao } from "@/lib/api";

/**
 * `PATCH /api/programacao/sessoes/<id>` — corrigir um rascunho.
 *
 * O `409` de "só rascunho é editável" e o `409` de conflito de horário chegam
 * inteiros, com as frases do Django. A segunda nomeia a sala e o horário; a
 * primeira manda cancelar e programar outra. Reescrevê-las aqui criaria duas
 * redações da mesma recusa.
 */

export const dynamic = "force-dynamic";

const REQUISICAO_INVALIDA = { detail: "Requisição inválida." };

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const sessao = Number(id);

  let corpo: Record<string, unknown>;
  try {
    corpo = await request.json();
  } catch {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  if (!Number.isInteger(sessao) || sessao <= 0) {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  const resultado = await patchSessao(sessionKey, sessao, {
    filme: Number(corpo.filme),
    sala: Number(corpo.sala),
    inicio: String(corpo.inicio ?? ""),
    preco: String(corpo.preco ?? ""),
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
