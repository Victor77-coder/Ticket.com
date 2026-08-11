import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postLogout } from "@/lib/api";

/**
 * `POST /api/sair`.
 *
 * Aceita apenas POST: um GET que encerra sessão pode ser disparado por
 * pré-carregamento de link ou por uma imagem hospedada em outro site (R8).
 */

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const chave = extrairCookie(request.headers.get("cookie"), COOKIE_SESSAO);

  if (chave) {
    // Invalida do lado do Django. Falha aqui não impede apagar o cookie: o
    // usuário pediu para sair, e sair localmente é o mínimo a garantir.
    await postLogout(chave);
  }

  const resposta = new NextResponse(null, { status: 204 });
  resposta.cookies.set({
    name: COOKIE_SESSAO,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });

  return resposta;
}

function extrairCookie(cabecalho: string | null, nome: string): string | null {
  if (!cabecalho) return null;

  for (const parte of cabecalho.split(";")) {
    const [chave, ...resto] = parte.trim().split("=");
    if (chave === nome) return resto.join("=");
  }
  return null;
}
