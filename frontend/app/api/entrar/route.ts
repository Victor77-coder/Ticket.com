import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postLogin } from "@/lib/api";

/**
 * `POST /api/entrar` — o único endereço de entrada que o navegador conhece.
 *
 * O cookie de sessão é emitido **aqui**, não repassado do Django. Assim o
 * navegador enxerga uma origem só, e o `SameSite=Lax` passa a ser defesa real
 * contra requisição forjada, em vez de exigir propagar o par
 * csrftoken/X-CSRFToken através do proxy (R1).
 *
 * Contrato: specs/003-user-authentication/contracts/auth-api.md
 */

export const dynamic = "force-dynamic";

const DUAS_SEMANAS_EM_SEGUNDOS = 60 * 60 * 24 * 14;

export async function POST(request: Request) {
  let corpo: { username?: unknown; password?: unknown };
  try {
    corpo = await request.json();
  } catch {
    return NextResponse.json({ detail: "Requisição inválida." }, { status: 400 });
  }

  const username = typeof corpo.username === "string" ? corpo.username : "";
  const password = typeof corpo.password === "string" ? corpo.password : "";

  const resultado = await postLogin(username, password);

  if (!resultado.ok) {
    // 401 (credencial inválida) e 429 (limite de tentativas) chegam com a
    // frase já em pt-BR do Django. Repassar preserva a mensagem única de
    // FR-004 sem reescrevê-la aqui.
    return NextResponse.json({ detail: resultado.error }, { status: resultado.status || 502 });
  }

  const resposta = NextResponse.json({ user: resultado.data.user });

  resposta.cookies.set({
    name: COOKIE_SESSAO,
    value: resultado.data.session_key,
    httpOnly: true, // script na página não alcança o identificador (FR-018)
    sameSite: "lax", // o navegador não envia em requisição de outro site (FR-019)
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: DUAS_SEMANAS_EM_SEGUNDOS,
  });

  return resposta;
}
