import { NextResponse } from "next/server";

import { fetchSeatMap } from "@/lib/api";

/**
 * `GET /api/mapa/<id>` — a ocupação, para quem lê do navegador.
 *
 * POR QUE UM PROXY PARA DADO PÚBLICO. O mapa já é público e a página da sessão
 * o busca direto no servidor, sem passar por aqui. O painel do cartão é
 * componente de CLIENTE: `API_BASE_URL` vale `http://backend:8000`, nome que só
 * resolve dentro da rede do Compose, e o navegador não alcança. Este arquivo é
 * a ponte, e nada além disso.
 *
 * SEM COOKIE, ao contrário de `/api/reservar` e `/api/pagar`: não há nada a
 * autorizar. Encaminhar a sessão aqui daria ao endereço público um poder que
 * ele não precisa ter.
 *
 * NENHUMA SEGUNDA LEITURA DE OCUPAÇÃO acontece aqui. O corpo é repassado como
 * veio — quem decide o que é "tomado" é `Reservation.OCUPANDO`, e essa regra tem
 * dono desde a 008 (R4).
 */

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sessao = Number(id);

  if (!Number.isInteger(sessao) || sessao <= 0) {
    return NextResponse.json({ detail: "Sessão inválida." }, { status: 400 });
  }

  const resultado = await fetchSeatMap(sessao);

  if (!resultado.ok) {
    // `status: 0` é o que `lib/api` devolve quando não houve resposta nenhuma —
    // timeout ou rede. Zero não é status HTTP válido para devolver ao navegador,
    // e 502 é a leitura correta: quem falhou foi o serviço atrás deste.
    const status = resultado.status > 0 ? resultado.status : 502;
    // A frase é a mesma que o painel exibe, e vem daqui para que o estado de
    // erro tenha UMA redação — não uma no servidor e outra no componente.
    return NextResponse.json(
      { detail: "Não foi possível carregar a lotação desta sessão. Tente de novo." },
      { status },
    );
  }

  return NextResponse.json(resultado.data);
}
