"use client";

import type { Assento } from "@/lib/types";

import estilos from "./seats.module.css";

/**
 * Um lugar da sala.
 *
 * É um `<button>` de verdade, não uma `<div>` com `onClick`. Botão dá
 * teclado, foco e semântica de graça — reconstruir isso à mão é o erro que
 * torna mapa de assento inacessível (R11).
 *
 * `aria-disabled` em vez de `disabled` nos lugares indisponíveis: `disabled`
 * tira o elemento da ordem de tabulação, e quem navega por teclado deixaria
 * de perceber que ali existe um lugar tomado. O clique é recusado no
 * manipulador, não pelo navegador (FR-011).
 */

export type SeatProps = {
  assento: Assento;
  fileira: string;
  selecionado: boolean;
  onAlternar: (assento: Assento, fileira: string) => void;
};

const MOTIVO: Record<string, string> = {
  tomado: "indisponível",
  acessibilidade: "reservado para acessibilidade",
};

export function situacaoDoAssento(assento: Assento, selecionado: boolean) {
  if (assento.situacao === "tomado") return "tomado";
  if (assento.tipo === "acessibilidade") return "acessibilidade";
  return selecionado ? "selecionado" : "livre";
}

export default function Seat({ assento, fileira, selecionado, onAlternar }: SeatProps) {
  const situacao = situacaoDoAssento(assento, selecionado);
  const indisponivel = situacao === "tomado" || situacao === "acessibilidade";

  // O rótulo carrega fileira, número e situação. É o que faz o mapa ser
  // compreensível sem enxergar a cor — e sem enxergar nada (FR-008, FR-011).
  const rotulo = `Fileira ${fileira}, lugar ${assento.numero}, ${
    MOTIVO[situacao] ?? situacao
  }`;

  return (
    <button
      type="button"
      className={`${estilos.assento} ${estilos[situacao]}`}
      aria-label={rotulo}
      aria-pressed={indisponivel ? undefined : selecionado}
      aria-disabled={indisponivel || undefined}
      data-situacao={situacao}
      onClick={() => {
        if (indisponivel) return;
        onAlternar(assento, fileira);
      }}
    >
      <span className={estilos.numero} aria-hidden="true">
        {assento.numero}
      </span>
    </button>
  );
}
