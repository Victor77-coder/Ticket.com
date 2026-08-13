import { formatarPreco } from "@/lib/moeda";
import type { Reserva } from "@/lib/types";

import estilos from "./payment.module.css";

/**
 * O que está sendo comprado, antes de digitar o cartão.
 *
 * Existe para que ninguém pague sem saber o quê: filme, sessão, sala, lugares
 * e o total, que é **calculado pelo servidor** — o valor exibido aqui é o que
 * veio dele, nunca uma conta refeita no navegador (FR-002, FR-003).
 */

export type ResumoDaCompraProps = {
  reserva: Reserva;
  filme: string;
  sala: string;
  inicio: string;
};

export function nomearLugares(assentos: { fileira: string; numero: number }[]) {
  return assentos.map((a) => `${a.fileira}${a.numero}`).join(", ");
}

function formatarHorario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function ResumoDaCompra({
  reserva,
  filme,
  sala,
  inicio,
}: ResumoDaCompraProps) {
  const quantidade = reserva.assentos.length;
  const unitario = quantidade > 0 ? Number(reserva.total) / quantidade : 0;

  return (
    <section className={estilos.resumo} aria-labelledby="resumo-titulo">
      <h2 id="resumo-titulo" className={estilos.resumoTitulo}>
        {filme}
      </h2>

      <dl className={estilos.linhas}>
        <div className={estilos.linha}>
          <dt>Sessão</dt>
          <dd>{formatarHorario(inicio)}</dd>
        </div>
        <div className={estilos.linha}>
          <dt>Sala</dt>
          <dd>{sala}</dd>
        </div>
        <div className={estilos.linha}>
          <dt>{quantidade > 1 ? "Lugares" : "Lugar"}</dt>
          <dd>{nomearLugares(reserva.assentos)}</dd>
        </div>
        <div className={estilos.linha}>
          <dt>
            {quantidade > 1
              ? `${quantidade} ingressos de ${formatarPreco(String(unitario))}`
              : "1 ingresso"}
          </dt>
          <dd>{formatarPreco(reserva.total)}</dd>
        </div>
      </dl>

      <p className={estilos.total}>
        <span>Total</span>
        <strong>{formatarPreco(reserva.total)}</strong>
      </p>
    </section>
  );
}
