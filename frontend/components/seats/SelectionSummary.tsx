"use client";

import { valorDoLugar, type TipoDeIngresso } from "@/lib/meia";
import { formatarPreco } from "@/lib/moeda";
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
  filme: string;
  horario: string;
  sala: string;
  lugares: LugarReservado[];
  /** O preço cheio da sessão — a meia é derivada dele (014). */
  precoUnitario: string;
  /** Ids marcados como meia (014). Vazio = tudo inteira. */
  meias: Set<number>;
  onEscolherTipo: (id: number, tipo: TipoDeIngresso) => void;
  total: number;
  limite: number;
  aviso: string | null;
  enviando: boolean;
  onConfirmar: () => void;
};

/**
 * Mantido como nome exportado porque os testes e o mapa já o consomem daqui;
 * a regra em si tem dono único em `lib/moeda`.
 */
export const formatarMoeda = formatarPreco;

export function nomearLugares(lugares: LugarReservado[]) {
  return lugares.map((l) => `${l.fileira}${l.numero}`).join(", ");
}

export default function SelectionSummary({
  filme,
  horario,
  sala,
  lugares,
  precoUnitario,
  meias,
  onEscolherTipo,
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
        <p className={estilos.resumoFilme}>{filme}</p>
        <p className={estilos.resumoSessao}>
          {horario} · {sala}
        </p>
        {vazio ? (
          <p className={estilos.resumoVazio}>
            Escolha até {limite} lugares no mapa para continuar.
          </p>
        ) : (
          <>
            <p className={estilos.resumoLugares}>
              {lugares.length === 1 ? "1 lugar" : `${lugares.length} lugares`}
            </p>
            <p className={estilos.dicaTipo}>Tipo de ingresso em cada lugar</p>

            {/* UMA LINHA POR LUGAR, com as DUAS opções à vista. Um interruptor
                que troca o próprio rótulo esconde a escolha; um seletor único
                para a compra inteira também não serviria: o caso comum da meia
                é a família em que uma pessoa paga meia e a outra não. */}
            <ul className={estilos.linhas}>
              {lugares.map((lugar) => {
                const meia = lugar.id !== undefined && meias.has(lugar.id);
                const lugarNome = `${lugar.fileira}${lugar.numero}`;
                return (
                  <li key={lugarNome} className={estilos.linha}>
                    <span className={estilos.linhaLugar}>{lugarNome}</span>
                    <div
                      className={estilos.tipos}
                      role="group"
                      aria-label={`Tipo do ingresso ${lugarNome}`}
                    >
                      <button
                        type="button"
                        className={estilos.tipo}
                        aria-pressed={!meia}
                        aria-label={`Inteira para o lugar ${lugarNome}`}
                        onClick={() =>
                          lugar.id !== undefined && onEscolherTipo(lugar.id, "inteira")
                        }
                      >
                        <span className={estilos.tipoNome}>Inteira</span>
                        <span className={estilos.tipoValor}>
                          {formatarMoeda(valorDoLugar(precoUnitario, "inteira"))}
                        </span>
                      </button>
                      <button
                        type="button"
                        className={estilos.tipo}
                        aria-pressed={meia}
                        aria-label={`Meia para o lugar ${lugarNome}`}
                        onClick={() =>
                          lugar.id !== undefined && onEscolherTipo(lugar.id, "meia")
                        }
                      >
                        <span className={estilos.tipoNome}>Meia</span>
                        <span className={estilos.tipoValor}>
                          {formatarMoeda(valorDoLugar(precoUnitario, "meia"))}
                        </span>
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>

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
