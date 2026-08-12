import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { COOKIE_SESSAO, fetchReserva, fetchSeatMap } from "@/lib/api";

import PagamentoCliente from "./PagamentoCliente";
import estilos from "./pagamento.module.css";

/**
 * `/pagamento/[id]` — UMA rota, quatro estados (R13).
 *
 * | Estado da reserva        | O que aparece                          |
 * |--------------------------|----------------------------------------|
 * | viva, não paga           | revisão da compra + formulário         |
 * | paga                     | os ingressos com QR                    |
 * | vencida                  | explicação e volta ao mapa             |
 * | de outro cliente, ou inexistente | não encontrada                 |
 *
 * O endereço não é escolha nova: `ReservationPanel` da 007 já aponta para cá.
 *
 * Uma rota só resolve de graça três coisas: recarregar depois de pagar mostra
 * os ingressos, voltar aqui com a reserva já paga leva aos ingressos em vez de
 * a um formulário inútil, e a confirmação ganha endereço estável. Com rotas
 * separadas, cada uma dessas viraria um redirecionamento a mais.
 *
 * O ESTADO VEM DO SERVIDOR A CADA VISITA. Os ingressos não moram em estado de
 * componente — é isso que faz a confirmação sobreviver a um recarregamento
 * (FR-022, US1-6).
 */

export const dynamic = "force-dynamic";

export default async function PagamentoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numero = Number(id);

  if (!Number.isInteger(numero) || numero <= 0) notFound();

  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Visitante sem sessão vai para a entrada e volta para cá — o mesmo retorno
  // seguro que a 003 validou. Nada é cobrado no caminho (FR-044).
  if (!chave) redirect(`/entrar?next=/pagamento/${numero}`);

  const resultado = await fetchReserva(chave, numero);

  if (!resultado.ok) {
    if (resultado.status === 401) redirect(`/entrar?next=/pagamento/${numero}`);

    // 404 cobre "não existe" e "é de outro cliente", e é assim que deve
    // ficar: um 403 confirmaria que a reserva existe.
    if (resultado.status === 404) notFound();

    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1>Não conseguimos carregar esta reserva</h1>
          <p>
            O servidor não respondeu agora. Atualize a página em alguns instantes — seus
            lugares seguem reservados até o fim do prazo.
          </p>
          <Link href="/" className={estilos.voltar}>
            Voltar ao início
          </Link>
        </section>
      </main>
    );
  }

  const reserva = resultado.data;

  // Reserva vencida e não paga: estado explicativo, sem formulário. A decisão
  // é do servidor — a contagem na tela é informativa (FR-029).
  if (reserva.situacao === "expirada") {
    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1>O prazo desta reserva terminou</h1>
          <p>
            Os lugares voltaram para outras pessoas e nada foi cobrado. Escolha os
            lugares de novo para continuar.
          </p>
          <Link href={`/sessoes/${reserva.sessao}`} className={estilos.voltar}>
            Escolher lugares de novo
          </Link>
        </section>
      </main>
    );
  }

  // O mapa traz filme, sala e horário. Falha aqui não impede pagar: são dados
  // de apresentação, e a reserva já tem o que a cobrança precisa.
  const mapa = await fetchSeatMap(reserva.sessao);
  const filme = mapa.ok ? mapa.data.filme.titulo : "Sua sessão";
  const sala = mapa.ok ? mapa.data.sala.nome : "";
  const inicio = mapa.ok ? mapa.data.inicio : new Date().toISOString();

  return (
    <main className={estilos.pagina}>
      <PagamentoCliente reserva={reserva} filme={filme} sala={sala} inicio={inicio} />
    </main>
  );
}
