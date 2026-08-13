import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, patchSala } from "@/lib/api";

/**
 * `PATCH /api/programacao/salas/<id>` — renomear ou trocar a capacidade.
 *
 * O `409` da sala com ocupação viva é repassado inteiro, com a frase que diz
 * QUANTOS lugares estão ocupados. É essa frase que transforma um botão
 * desabilitado em explicação — sem ela, a interface estaria escondendo um
 * controle, que não conta como autorização nem como resposta (FR-037).
 */

export const dynamic = "force-dynamic";

const REQUISICAO_INVALIDA = { detail: "Requisição inválida." };

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const sala = Number(id);

  let corpo: Record<string, unknown>;
  try {
    corpo = await request.json();
  } catch {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  if (!Number.isInteger(sala) || sala <= 0) {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const alteracao: { nome?: string; capacidade?: number } = {};
  if (typeof corpo.nome === "string") alteracao.nome = corpo.nome;
  if (corpo.capacidade !== undefined) alteracao.capacidade = Number(corpo.capacidade);

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;
  const resultado = await patchSala(sessionKey, sala, alteracao);

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
