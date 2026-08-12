import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postValidacao } from "@/lib/api";

/**
 * `POST /api/validar` — a validação, pelo navegador.
 *
 * Mesmo padrão de proxy de 002, 003, 007, 008 e 009: o navegador nunca fala com
 * o Django direto.
 *
 * Status e corpo vão inteiros e **sem alteração**. Os quatro desfechos chegam
 * como `200` com o campo `situacao`, e o `403` de quem não é portaria chega
 * como recusa do servidor — nunca como tela escondida.
 *
 * Contrato: specs/010-gate-validation/contracts/gate-api.md
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

  const codigo = typeof corpo.codigo === "string" ? corpo.codigo : "";
  const sessao = Number(corpo.sessao);

  if (!Number.isInteger(sessao) || sessao <= 0) {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Sem cookie a chamada segue: quem decide é o Django, e a resposta dele
  // (401) é o que conduz à entrada. Recusar aqui duplicaria a regra de
  // autorização no lugar errado.
  const resultado = await postValidacao(sessionKey, { codigo, sessao });

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
