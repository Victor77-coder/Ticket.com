import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, deleteLink, postLink } from "@/lib/api";

/**
 * `POST` e `DELETE /api/link-do-ingresso` — gerar e revogar, pelo navegador.
 *
 * Mesmo padrão de proxy de 002, 003, 007 e 008: o navegador nunca fala com o
 * Django direto. No Compose `API_BASE_URL` é `http://backend:8000`, um nome
 * que só resolve dentro da rede do Compose.
 *
 * Status e corpo do Django vão inteiros e **sem alteração**: o `403` de quem
 * não pode chega como recusa do servidor, e o `404` de ingresso alheio chega
 * como `404` — nunca como `403`, que confirmaria a existência.
 *
 * Dois verbos aqui porque são dois verbos lá: gerar e revogar são criar e
 * apagar o mesmo recurso.
 *
 * Contrato: specs/009-my-tickets-sharing/contracts/my-tickets-api.md
 */

export const dynamic = "force-dynamic";

const REQUISICAO_INVALIDA = { detail: "Requisição inválida." };

async function idDoCorpo(request: Request): Promise<string | null> {
  try {
    const corpo = await request.json();
    const id = corpo?.ingresso;
    return typeof id === "string" && id.length > 0 ? id : null;
  } catch {
    return null;
  }
}

function responder(resultado: {
  ok: boolean;
  data?: unknown;
  corpoErro?: unknown;
  error?: string;
  status: number;
}) {
  if (!resultado.ok) {
    const corpo =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };
    return NextResponse.json(corpo, { status: resultado.status || 502 });
  }
  return NextResponse.json(resultado.data, { status: resultado.status });
}

export async function POST(request: Request) {
  const id = await idDoCorpo(request);
  if (!id) return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Sem cookie a chamada segue: quem decide é o Django, e a resposta dele
  // (401) é o que conduz à entrada. Recusar aqui duplicaria a regra de
  // autorização no lugar errado.
  return responder(await postLink(sessionKey, id));
}

export async function DELETE(request: Request) {
  const id = await idDoCorpo(request);
  if (!id) return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  return responder(await deleteLink(sessionKey, id));
}
