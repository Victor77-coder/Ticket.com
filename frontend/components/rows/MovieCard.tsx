"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import type { MovieCard as MovieCardType } from "@/lib/types";
import styles from "./rows.module.css";

type Props = {
  filme: MovieCardType;
};

function formatarDuracao(minutos: number | null): string | null {
  if (!minutos) return null;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  if (horas === 0) return `${resto}min`;
  if (resto === 0) return `${horas}h`;
  return `${horas}h${String(resto).padStart(2, "0")}`;
}

export function MovieCard({ filme }: Props) {
  const [arteFalhou, setArteFalhou] = useState(false);

  const mostrarCartaz = Boolean(filme.poster_url) && !arteFalhou;
  const duracao = formatarDuracao(filme.runtime_minutes);
  const meta = [filme.certification_br, duracao].filter(Boolean).join(" · ");

  return (
    <Link
      href={filme.movie_path}
      className={styles.cartao}
      // O nome acessível vem do próprio link, não do alt da imagem: quando o
      // cartaz falta, o cartão continua identificando o filme (FR-012).
      aria-label={filme.title}
    >
      <div className={styles.moldura}>
        {mostrarCartaz ? (
          <Image
            src={filme.poster_url as string}
            alt=""
            width={210}
            height={315}
            className={styles.cartaz}
            onError={() => setArteFalhou(true)}
          />
        ) : (
          /* Sem cartaz o título aparece dentro da moldura, mantendo a
           * proporção dos demais para não desalinhar a trilha (FR-011). */
          <div className={styles.cartazAusente} aria-hidden="true">
            {filme.title}
          </div>
        )}
      </div>

      {/* Título em texto, não apenas dentro da imagem (FR-009). */}
      <p className={styles.cartaoTitulo}>{filme.title}</p>
      {meta && <p className={styles.cartaoMeta}>{meta}</p>}
    </Link>
  );
}
