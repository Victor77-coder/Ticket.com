import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { COOKIE_SESSAO, postPagamento } from "@/lib/api";

/**
 * `POST /api/pagar` — o endereço de pagamento que o navegador conhece.
 *
 * Repassa o corpo ao Django com o cookie de sessão e devolve status e corpo
 * **sem alterá-los**: o `402` chega ao navegador com a mesma frase em pt-BR, e
 * o `403` de quem não pode comprar chega como recusa do servidor, não como
 * botão escondido.
 *
 * ESTE É O ÚNICO PONTO DO SISTEMA POR ONDE O NÚMERO COMPLETO DO CARTÃO PASSA,
 * e ele passa **sem parar**: nada aqui guarda, registra ou ecoa o corpo. Um
 * `console.log` de depuração nesta função põe número de cartão no log do
 * servidor (FR-011, R10).
 *
 * Contrato: specs/008-payment-ticket-issuance/contracts/payment-ticket-api.md
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

  const reserva = Number(corpo.reserva);
  if (!Number.isInteger(reserva) || reserva <= 0) {
    return NextResponse.json(REQUISICAO_INVALIDA, { status: 400 });
  }

  const texto = (valor: unknown) => (typeof valor === "string" ? valor : "");

  const sessionKey = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Sem cookie a chamada segue mesmo assim: quem decide é o Django, e a
  // resposta dele (401) é o que conduz à entrada. Recusar aqui duplicaria a
  // regra de autorização no lugar errado.
  const resultado = await postPagamento(sessionKey, reserva, {
    numero: texto(corpo.numero),
    nome: texto(corpo.nome),
    validade: texto(corpo.validade),
    cvv: texto(corpo.cvv),
  });

  if (!resultado.ok) {
    // O corpo do Django vai inteiro, não só a frase: o `402` traz o motivo e
    // o prazo intocado da reserva, e o `409` de reserva já paga traz os
    // ingressos que já existem. A tela precisa dos dois.
    const corpoErro =
      resultado.corpoErro && typeof resultado.corpoErro === "object"
        ? resultado.corpoErro
        : { detail: resultado.error };

    return NextResponse.json(corpoErro, { status: resultado.status || 502 });
  }

  return NextResponse.json(resultado.data, { status: resultado.status });
}
