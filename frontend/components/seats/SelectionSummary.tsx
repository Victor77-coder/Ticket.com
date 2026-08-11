"use client";

import type { LugarReservado } from "@/lib/types";

import estilos from "./seats.module.css";

/**
 * O rodapé da seleção: quantos lugares, quanto custa, e o botão de confirmar.
 *
 * Puramente apresentacional — quem guarda a seleção é `SeatSelection`. Assim
 * o resumo pode ser testado com uma seleção montada à mão, sem simular
 * cliques no mapa inteiro.
 */

export type SelectionSummaryProps = {
  lugares: LugarReservado[];
  total: number;
  limite: number;
  aviso: string | null;
  enviando: boolean;
  onConfirmar: () => void;
};

export function formatarMoeda(valor: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    valor,
  );
}

export function nomearLugares(lugares: LugarReservado[]) {
  return lugares.map((l) => `${l.fileira}${l.numero}`).join(", ");
}

export default function SelectionSummary({
  lugares,
  total,
  limite,
  aviso,
  enviando,
  onConfirmar,
}: SelectionSummaryProps) {
  const vazio = lugares.length === 0;

  return (
    <div className={estilos.resumo}>
      {aviso && (
        <p className={estilos.aviso} role="alert">
          {aviso}
        </p>
      )}

      <div>
        {vazio ? (
          <p className={estilos.resumoVazio}>
            Escolha até {limite} lugares no mapa para continuar.
          </p>
        ) : (
          <>
            <p className={estilos.resumoLugares}>
              {lugares.length === 1 ? "1 lugar" : `${lugares.length} lugares`} ·{" "}
              {nomearLugares(lugares)}
            </p>
            <p className={estilos.resumoTotal}>{formatarMoeda(total)}</p>
          </>
        )}
      </div>

      <button
        type="button"
        className={estilos.confirmar}
        onClick={onConfirmar}
        disabled={vazio || enviando}
      >
        {enviando ? "Reservando…" : "Confirmar lugares"}
      </button>
    </div>
  );
}
