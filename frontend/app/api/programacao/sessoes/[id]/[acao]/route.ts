import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postAcaoDeSessao } from "@/lib/api";

/**
 * `POST /api/programacao/sessoes/<id>/publicar` e `.../cancelar`.
 *
 * UM handler para as duas ações, e não dois arquivos iguais: o que muda é o
 * segmento do endereço, e nada mais. A LISTA DE AÇÕES ACEITAS É FECHADA — sem
 * ela, este proxy repassaria qualquer segmento que alguém digitasse na URL
 * para o Django, transformando um handler de duas ações num encaminhador
 * genérico.
 *
 * As pré-condições continuam do servidor: horário futuro, sala com lugares,
 * estado não terminal. Este arquivo não conhece nenhuma delas (FR-037).
 */

export const dynamic = "force-dynamic";

const ACOES = ["publicar", "cancelar"] as const;

type Acao = (typeof ACOES)[number];

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string; acao: string }> },
) {
  const { id, acao } = await params;
  const sessao = Number(id);

  if (!Number.isInteger(sessao) || sessao <= 0) {
    return NextResponse.json({ detail: "Requisição inválida." }, { status: 400 });
  }

  if (!ACOES.includes(acao as Acao)) {
    return NextResponse.json({ detail: "Ação desconhecida." }, { status: 404 });
  }

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;
  const resultado = await postAcaoDeSessao(sessionKey, sessao, acao as Acao);

  if (!resultado.ok) {
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
