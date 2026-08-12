import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postSessao } from "@/lib/api";

/**
 * `POST /api/programacao/sessoes` — programar, pelo navegador.
 *
 * Mesmo padrão de proxy de 002, 003, 007, 008, 009 e 010: o navegador nunca
 * fala com o Django direto. No Compose `API_BASE_URL` é `http://backend:8000`,
 * um nome que só resolve dentro da rede do Compose.
 *
 * STATUS E CORPO VÃO INTEIROS E SEM ALTERAÇÃO. O `409` do conflito de horário e
 * os `400` de campo já chegam com a frase em português que o Django escreveu;
 * reescrevê-los aqui criaria a segunda redação da mesma recusa. O `403` de
 * quem não é organizador chega como recusa do servidor — nunca como tela
 * escondida (FR-037).
 *
 * Contrato: specs/013-painel-do-organizador/contracts/programacao-api.md
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

  // Sem cookie a chamada segue: quem decide é o Django, e o `401` dele é o que
  // conduz à entrada. Recusar aqui duplicaria a autorização no lugar errado.
  const resultado = await postSessao(sessionKey, {
    filme: Number(corpo.filme),
    sala: Number(corpo.sala),
    inicio: String(corpo.inicio ?? ""),
    preco: String(corpo.preco ?? ""),
    publicar: Boolean(corpo.publicar),
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
