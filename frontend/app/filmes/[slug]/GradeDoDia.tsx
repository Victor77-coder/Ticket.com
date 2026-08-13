"use client";

import { useState } from "react";

import CartaoDeSessao from "@/components/sessao/CartaoDeSessao";
import { agruparSessoesPorDia } from "@/lib/grade-sessoes";
import type { Screening } from "@/lib/types";

import styles from "./filme.module.css";

/**
 * O dia ativo e os cartões daquele dia.
 *
 * A 012 entregou o agrupamento em dois níveis — dia, depois sala — e a 014
 * mantém os dois: o que mudou é que a sala deixou de ser um `<h3>` solto acima
 * de uma lista e virou CARTÃO, com as ações de leitura no topo dele.
 *
 * O agrupamento continua ACONTECENDO NO CLIENTE, a partir das sessões que o
 * detalhe do filme já entrega. Nenhuma requisição nova nasceu para desenhar a
 * grade, e o contrato de `GET /api/v1/filmes/<slug>/` não mudou.
 */

/**
 * Data de estreia, apenas quando ela é futura.
 *
 * Sem data conhecida ou com data no passado, devolve null: anunciar "estreia
 * em" numa data já vencida seria informação errada, e estimar uma data que
 * não temos seria inventar (FR-027, SC-009).
 */
export function estreiaFutura(iso: string | null): string | null {
  if (!iso) return null;

  const data = new Date(`${iso}T00:00:00`);
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  if (data <= hoje) return null;

  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(data);
}

export default function GradeDoDia({
  sessoes,
  releaseDate,
}: {
  sessoes: Screening[];
  releaseDate: string | null;
}) {
  const grade = agruparSessoesPorDia(sessoes);
  const [diaAtivo, setDiaAtivo] = useState(grade[0]?.dia ?? "");

  if (sessoes.length === 0) {
    const estreia = estreiaFutura(releaseDate);
    return (
      <div className={styles.vazio}>
        {estreia && <p className={styles.estreia}>Estreia em {estreia}</p>}
        <p className={styles.vazioTexto}>
          No momento, este filme não possui sessões programadas.
        </p>
      </div>
    );
  }

  const dia = grade.find((item) => item.dia === diaAtivo) ?? grade[0];

  return (
    <div className={styles.grade}>
      <div className={styles.dias} role="tablist" aria-label="Dias com sessão">
        {grade.map((item) => {
          const ativo = item.dia === dia.dia;
          return (
            <button
              key={item.dia}
              type="button"
              role="tab"
              aria-selected={ativo}
              aria-current={ativo ? "date" : undefined}
              className={ativo ? `${styles.dia} ${styles.diaAtivo}` : styles.dia}
              onClick={() => setDiaAtivo(item.dia)}
            >
              {item.rotulo}
            </button>
          );
        })}
      </div>

      {dia.salas.map((sala) => (
        <CartaoDeSessao key={sala.nome} sala={sala.nome} horarios={sala.horarios} />
      ))}
    </div>
  );
}
