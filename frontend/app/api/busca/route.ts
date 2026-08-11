import { NextResponse } from "next/server";

import { fetchSearch } from "@/lib/api";

/**
 * `GET /api/busca` — o único endereço de busca que o navegador conhece.
 *
 * Existe para preservar duas propriedades já estabelecidas no projeto: o
 * navegador não fala com o Django direto, e o endereço do back-end não entra
 * no bundle. No Compose o Django atende em `http://backend:8000`, que o
 * navegador não consegue resolver (R1).
 *
 * Contrato: specs/002-site-header-navigation/contracts/search-proxy.md
 */

// O resultado depende do catálogo corrente e do termo; uma resposta estática
// serviria sugestão obsoleta.
export const dynamic = "force-dynamic";

const TERMO_MAX_CHARS = 80;

const VAZIO = { termo: "", count: 0, truncated: false, results: [] };

export async function GET(request: Request) {
  const bruto = new URL(request.url).searchParams.get("q") ?? "";
  const termo = bruto.trim().slice(0, TERMO_MAX_CHARS);

  // Mesmo comportamento do Django: campo vazio é o estado inicial, não erro.
  if (!termo) {
    return NextResponse.json(VAZIO);
  }

  const resultado = await fetchSearch(termo);

  if (!resultado.ok) {
    // O corpo de erro do Django nunca atravessa: stack, rota interna e o
    // valor de API_BASE_URL ficam do lado do servidor. O navegador recebe só
    // a frase em pt-BR.
    console.error(`[busca] falha ao consultar o back-end: ${resultado.error}`);

    const expirou = resultado.error.includes("demorou demais");
    return NextResponse.json(
      {
        erro: expirou
          ? "A busca demorou demais para responder."
          : "Não foi possível buscar agora. Tente de novo em instantes.",
      },
      { status: expirou ? 504 : 502 },
    );
  }

  // Repassa sem enriquecer nem reordenar: transformar aqui criaria uma
  // segunda verdade sobre o formato da busca.
  return NextResponse.json(resultado.data);
}
