"use client";

import { useState } from "react";

import type { Assento, LugarReservado, MapaSessao } from "@/lib/types";

import SeatMap from "./SeatMap";
import SelectionSummary from "./SelectionSummary";
import estilos from "./seats.module.css";

/**
 * Guarda a seleção e coordena mapa e resumo.
 *
 * A seleção vive só aqui, no navegador: o servidor não sabe o que alguém
 * marcou até a confirmação virar reserva. É por isso que `situacao` no
 * contrato só tem "livre" e "tomado" — "selecionado" não é estado do
 * sistema, é estado de quem está escolhendo.
 */

export type SeatSelectionProps = {
  mapa: MapaSessao;
};

export default function SeatSelection({ mapa }: SeatSelectionProps) {
  const [selecionados, setSelecionados] = useState<LugarReservado[]>([]);
  const [ids, setIds] = useState<Set<number>>(new Set());
  const [aviso, setAviso] = useState<string | null>(null);

  function alternar(assento: Assento, fileira: string) {
    setAviso(null);

    if (ids.has(assento.id)) {
      const proximos = new Set(ids);
      proximos.delete(assento.id);
      setIds(proximos);
      setSelecionados((atual) =>
        atual.filter((l) => !(l.fileira === fileira && l.numero === assento.numero)),
      );
      return;
    }

    if (ids.size >= mapa.limite_por_reserva) {
      setAviso(
        `São no máximo ${mapa.limite_por_reserva} lugares por reserva. ` +
          "Desmarque um para escolher outro.",
      );
      return;
    }

    setIds(new Set(ids).add(assento.id));
    setSelecionados((atual) => [...atual, { fileira, numero: assento.numero }]);
  }

  if (mapa.esgotada) {
    return (
      <div className={estilos.confirmada}>
        <p className={estilos.confirmadaTitulo}>Esta sessão esgotou</p>
        <p className={estilos.confirmadaLugares}>
          Todos os lugares desta sessão já foram reservados. Escolha outro horário na
          página do filme.
        </p>
      </div>
    );
  }

  const total = ids.size * Number(mapa.preco);

  return (
    <>
      <SeatMap fileiras={mapa.fileiras} selecionados={ids} onAlternar={alternar} />
      <SelectionSummary
        lugares={selecionados}
        total={total}
        limite={mapa.limite_por_reserva}
        aviso={aviso}
        enviando={false}
        onConfirmar={() => undefined}
      />
    </>
  );
}
