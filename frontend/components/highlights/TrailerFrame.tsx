"use client";

import { useEffect, useRef, useState } from "react";

import type { Trailer } from "@/lib/types";
import styles from "./highlights.module.css";

type Props = {
  trailer: Trailer;
  tituloDoFilme: string;
  onFechar: () => void;
};

/**
 * Trailer reproduzido dentro do painel (R2, FR-012).
 *
 * Este componente só é montado depois do clique, e desmontá-lo encerra a
 * reprodução — é isso que garante "parar ao trocar de painel" (FR-014) e
 * "no máximo um trailer por vez" (FR-016) sem depender da API JavaScript do
 * YouTube nem carregar script de terceiro na abertura da home.
 */
export function TrailerFrame({ trailer, tituloDoFilme, onFechar }: Props) {
  const [falhou, setFalhou] = useState(false);
  const botaoFecharRef = useRef<HTMLButtonElement>(null);

  // O foco vai para o botão de fechar: quem abriu por teclado precisa de uma
  // saída imediata, sem tabular através do iframe (SC-005).
  useEffect(() => {
    botaoFecharRef.current?.focus();
  }, []);

  useEffect(() => {
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        evento.stopPropagation();
        onFechar();
      }
    }
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  // youtube-nocookie evita cookie de rastreamento; autoplay é honrado porque
  // o iframe nasce de um gesto direto do usuário (FR-017).
  const src =
    `https://www.youtube-nocookie.com/embed/${encodeURIComponent(trailer.external_key)}` +
    `?autoplay=1&rel=0&modestbranding=1&playsinline=1`;

  return (
    <div className={styles.trailer}>
      <button
        ref={botaoFecharRef}
        type="button"
        className={styles.trailerFechar}
        onClick={onFechar}
      >
        Fechar trailer
      </button>

      {falhou ? (
        <div className={styles.trailerErro} role="alert">
          <p className={styles.avisoTitulo}>O trailer não pôde ser carregado</p>
          <p className={styles.avisoTexto}>
            O vídeo está indisponível no momento. Você ainda pode ver as sessões e comprar
            seu ingresso normalmente.
          </p>
        </div>
      ) : (
        <iframe
          className={styles.trailerVideo}
          src={src}
          title={`Trailer de ${tituloDoFilme}`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          onError={() => setFalhou(true)}
        />
      )}
    </div>
  );
}
