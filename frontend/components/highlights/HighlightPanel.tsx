"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import type { Highlight } from "@/lib/types";
import styles from "./highlights.module.css";
import { TrailerFrame } from "./TrailerFrame";

type Props = {
  highlight: Highlight;
  posicao: number;
  total: number;
  ativo: boolean;
  trailerAberto: boolean;
  onAbrirTrailer: () => void;
  onFecharTrailer: () => void;
};

function formatarDuracao(minutos: number | null): string | null {
  if (!minutos) return null;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  if (horas === 0) return `${resto}min`;
  if (resto === 0) return `${horas}h`;
  return `${horas}h${String(resto).padStart(2, "0")}`;
}

export function HighlightPanel({
  highlight,
  posicao,
  total,
  ativo,
  trailerAberto,
  onAbrirTrailer,
  onFecharTrailer,
}: Props) {
  const [arteFalhou, setArteFalhou] = useState(false);

  const duracao = formatarDuracao(highlight.runtime_minutes);
  const genero = highlight.genres[0] ?? null;
  const mostrarArte = Boolean(highlight.backdrop_url) && !arteFalhou;

  // Metadados presentes viram uma linha; ausentes simplesmente não aparecem.
  // Nunca "N/A", nunca caixa vazia (Princípio V).
  const metadados = [duracao, genero].filter(Boolean) as string[];

  return (
    <div
      className={styles.painel}
      role="group"
      aria-roledescription="slide"
      aria-label={`${posicao} de ${total}: ${highlight.title}`}
      // Painéis fora de vista não podem receber Tab (SC-005).
      inert={!ativo ? true : undefined}
    >
      {mostrarArte ? (
        <Image
          src={highlight.backdrop_url as string}
          alt=""
          fill
          priority={posicao === 1}
          sizes="100vw"
          className={styles.arte}
          onError={() => setArteFalhou(true)}
        />
      ) : (
        <div className={styles.arteFallback} aria-hidden="true" />
      )}

      <div className={styles.veu} aria-hidden="true" />
      <div className={styles.veuBase} aria-hidden="true" />

      <div className={styles.conteudo}>
        <div className={styles.metadados}>
          {highlight.certification_br && (
            <span
              className={styles.classificacao}
              aria-label={`Classificação indicativa: ${highlight.certification_br} anos`}
            >
              {highlight.certification_br}
            </span>
          )}
          {metadados.map((item, indice) => (
            <span key={item}>
              {indice > 0 && (
                <span className={styles.separador} aria-hidden="true">
                  {" · "}
                </span>
              )}
              {item}
            </span>
          ))}
        </div>

        <h2 className={styles.titulo}>{highlight.title}</h2>

        {highlight.synopsis_short && <p className={styles.sinopse}>{highlight.synopsis_short}</p>}

        <div className={styles.acoes}>
          {highlight.has_available_seats ? (
            <Link href={highlight.movie_path} className={styles.botaoPrimario}>
              Ver ingressos
            </Link>
          ) : (
            <span className={styles.botaoEsgotado} aria-disabled="true">
              Ingressos esgotados
            </span>
          )}

          {/* Sem trailer o botão não existe — nunca desabilitado (FR-015). */}
          {highlight.trailer && (
            <button type="button" className={styles.botaoSecundario} onClick={onAbrirTrailer}>
              Trailer
            </button>
          )}
        </div>
      </div>

      {trailerAberto && highlight.trailer && (
        <TrailerFrame
          trailer={highlight.trailer}
          tituloDoFilme={highlight.title}
          onFechar={onFecharTrailer}
        />
      )}
    </div>
  );
}
