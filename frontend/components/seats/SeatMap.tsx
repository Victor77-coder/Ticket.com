"use client";

import type { Assento, Fileira } from "@/lib/types";

import Seat from "./Seat";
import estilos from "./seats.module.css";

/**
 * A sala: a tela no topo, as fileiras identificadas por letra, o corredor
 * central e a legenda.
 *
 * O corredor não é enfeite — é o que faz a grade ler como sala de cinema em
 * vez de tabela de caixas, e dá ao mapa a orientação que o rótulo "TELA"
 * sozinho não daria (R7).
 */

const LUGARES_ANTES_DO_CORREDOR = 5;

export type SeatMapProps = {
  fileiras: Fileira[];
  selecionados: Set<number>;
  onAlternar: (assento: Assento, fileira: string) => void;
};

export default function SeatMap({ fileiras, selecionados, onAlternar }: SeatMapProps) {
  return (
    <div className={estilos.sala}>
      <div className={estilos.tela}>
        <div className={estilos.telaArco} aria-hidden="true" />
        <span className={estilos.telaRotulo}>Tela</span>
      </div>

      <div className={estilos.fileiras}>
        {fileiras.map((fileira) => (
          <div key={fileira.letra} className={estilos.fileira}>
            <span className={estilos.letra} aria-hidden="true">
              {fileira.letra}
            </span>

            {fileira.assentos.map((assento, indice) => (
              <div key={assento.id} style={{ display: "contents" }}>
                {indice === LUGARES_ANTES_DO_CORREDOR && (
                  <span className={estilos.corredor} aria-hidden="true" />
                )}
                <Seat
                  assento={assento}
                  fileira={fileira.letra}
                  selecionado={selecionados.has(assento.id)}
                  onAlternar={onAlternar}
                />
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* A legenda não substitui a distinção por forma — ela nomeia o que a
          forma já diz. Um mapa que só é legível com a legenda ao lado falha
          o FR-008. */}
      <ul className={estilos.legenda}>
        <li className={estilos.itemLegenda}>
          <span className={`${estilos.amostra} ${estilos.livre}`} aria-hidden="true" />
          Livre
        </li>
        <li className={estilos.itemLegenda}>
          <span
            className={`${estilos.amostra} ${estilos.selecionado}`}
            aria-hidden="true"
          />
          Selecionado
        </li>
        <li className={estilos.itemLegenda}>
          <span className={`${estilos.amostra} ${estilos.tomado}`} aria-hidden="true" />
          Indisponível
        </li>
        <li className={estilos.itemLegenda}>
          <span
            className={`${estilos.amostra} ${estilos.acessibilidade}`}
            aria-hidden="true"
          />
          Acessibilidade
        </li>
      </ul>
    </div>
  );
}
