import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postReserva } from "@/lib/api";

/**
 * `POST /api/reservar` — o endereço de reserva que o navegador conhece.
 *
 * Repassa o corpo ao Django com o cookie de sessão e devolve status e corpo
 * **sem alterá-los**: o `409` chega ao navegador com a mesma frase em pt-BR,
 * e o `403` de quem não pode comprar chega como recusa do servidor, não como
 * botão escondido.
 *
 * Contrato: specs/007-seat-selection/contracts/reservation-api.md
 */

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let corpo: {
    sessao?: unknown;
    assentos?: unknown;
    meias?: unknown;
    chave_idempotencia?: unknown;
  };
  try {
    corpo = await request.json();
  } catch {
    return NextResponse.json({ detail: "Requisição inválida." }, { status: 400 });
  }

  const sessao = Number(corpo.sessao);
  const assentos = Array.isArray(corpo.assentos) ? corpo.assentos.map(Number) : [];
  // ESTE PROXY FILTRA O CORPO CAMPO A CAMPO, e é por isso que `meias` precisa
  // ser nomeado aqui: um campo novo que só o serializer do Django conheça
  // chegaria vazio, e a compra sairia toda inteira sem nenhum erro — defeito
  // que passa em todo teste de unidade e só aparece ponta a ponta.
  //
  // A filtragem continua valendo a pena: ela é o que impede um corpo arbitrário
  // do navegador de atravessar para a API.
  const meias = Array.isArray(corpo.meias) ? corpo.meias.map(Number) : [];
  const chave = typeof corpo.chave_idempotencia === "string" ? corpo.chave_idempotencia : "";

  if (!Number.isInteger(sessao) || !chave) {
    return NextResponse.json({ detail: "Requisição inválida." }, { status: 400 });
  }

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Sem cookie a chamada segue mesmo assim: quem decide é o Django, e a
  // resposta dele (401) é o que conduz à entrada. Recusar aqui duplicaria a
  // regra de autorização no lugar errado.
  const resultado = await postReserva(sessionKey, {
    sessao,
    assentos,
    meias,
    chave_idempotencia: chave,
  });

  if (!resultado.ok) {
    // O corpo do Django vai inteiro, não só a frase: o 409 nomeia quais
    // lugares causaram a recusa, e a tela precisa disso para apontá-los.
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
