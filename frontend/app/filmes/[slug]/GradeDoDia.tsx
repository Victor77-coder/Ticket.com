"use client";

import Link from "next/link";
import { useState } from "react";

import { agruparSessoesPorDia } from "@/lib/grade-sessoes";
import type { Screening } from "@/lib/types";

import styles from "./filme.module.css";

function formatarHora(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatarHorarioAcessivel(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

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
        <section key={sala.nome} className={styles.sala} aria-label={sala.nome}>
          <h3 className={styles.salaNome}>{sala.nome}</h3>
          <ul className={styles.horarios}>
            {sala.horarios.map((sessao) => {
              const hora = formatarHora(sessao.starts_at);
              const acessivel = `Escolher lugares — ${formatarHorarioAcessivel(sessao.starts_at)}, ${sessao.room_name}`;

              return (
                <li key={sessao.id}>
                  {sessao.has_available_seats ? (
                    <Link
                      href={`/sessoes/${sessao.id}`}
                      className={styles.horario}
                      aria-label={acessivel}
                    >
                      {hora}
                    </Link>
                  ) : (
                    <span className={styles.horarioEsgotado}>
                      <span className={styles.horarioHora}>{hora}</span>
                      <span>Esgotada</span>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
