"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Reserva } from "@/lib/types";

import { nomearLugares } from "./SelectionSummary";
import estilos from "./seats.module.css";

/**
 * A reserva confirmada, com o prazo correndo e o caminho para o pagamento.
 *
 * A contagem regressiva é calculada a partir de `expira_em`, que é instante
 * absoluto: guardar "faltam 600 segundos" e decrementar faria a conta
 * derivar a cada aba em segundo plano, e o navegador é livre para atrasar
 * temporizadores.
 */

export type ReservationPanelProps = {
  reserva: Reserva;
  /** Existe para o teste fixar o relógio; em produção é sempre `Date.now`. */
  agora?: () => number;
};

function restante(expiraEm: string, agora: number) {
  return Math.max(0, Math.floor((new Date(expiraEm).getTime() - agora) / 1000));
}

function formatarRestante(segundos: number) {
  const min = Math.floor(segundos / 60);
  const seg = segundos % 60;
  return `${min}:${String(seg).padStart(2, "0")}`;
}

export default function ReservationPanel({
  reserva,
  agora = Date.now,
}: ReservationPanelProps) {
  const [segundos, setSegundos] = useState(() => restante(reserva.expira_em, agora()));

  useEffect(() => {
    const id = setInterval(() => {
      setSegundos(restante(reserva.expira_em, agora()));
    }, 1000);
    return () => clearInterval(id);
  }, [reserva.expira_em, agora]);

  const expirada = segundos === 0 || reserva.situacao === "expirada";

  return (
    <div className={estilos.confirmada}>
      <h2 className={estilos.confirmadaTitulo}>
        {expirada ? "Esta reserva expirou" : "Lugares reservados"}
      </h2>

      <p className={estilos.confirmadaLugares}>
        {nomearLugares(reserva.assentos)} · {reserva.total.replace(".", ",")}
      </p>

      {expirada ? (
        <>
          <p className={`${estilos.prazo} ${estilos.expirada}`}>
            O prazo terminou e os lugares voltaram para outras pessoas.
          </p>
          <Link href={`/sessoes/${reserva.sessao}`} className={estilos.seguir}>
            Escolher lugares de novo
          </Link>
        </>
      ) : (
        <>
          {/* `role="timer"` com `aria-live` educado: quem usa leitor de tela
              precisa saber que há prazo, sem ser interrompido a cada
              segundo. */}
          <p className={estilos.prazo} role="timer" aria-live="polite">
            Você tem {formatarRestante(segundos)} para concluir o pagamento.
          </p>
          {/* Nenhum ingresso foi emitido (FR-029). O pagamento é a próxima
              feature, e o caminho já existe para não terminar em beco. */}
          <Link href={`/pagamento/${reserva.id}`} className={estilos.seguir}>
            Continuar para pagamento
          </Link>
        </>
      )}
    </div>
  );
}
