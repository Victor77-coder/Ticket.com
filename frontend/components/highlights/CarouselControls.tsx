"use client";

import styles from "./highlights.module.css";

type Props = {
  indice: number;
  titulos: string[];
  onAnterior: () => void;
  onProximo: () => void;
  onIr: (indice: number) => void;
};

export function CarouselControls({
  indice,
  titulos,
  onAnterior,
  onProximo,
  onIr,
}: Props) {
  return (
    <div className={styles.controles}>
      <button
        type="button"
        className={`${styles.seta} ${styles.setaAnterior}`}
        onClick={onAnterior}
        aria-label="Filme anterior"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M15 5l-7 7 7 7"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <button
        type="button"
        className={`${styles.seta} ${styles.setaProximo}`}
        onClick={onProximo}
        aria-label="Próximo filme"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M9 5l7 7-7 7"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* Botões reais, não divs clicáveis: teclado e leitor de tela de graça. */}
      <div className={styles.indicadores}>
        {titulos.map((titulo, i) => (
          <button
            key={titulo + i}
            type="button"
            className={`${styles.indicador} ${i === indice ? styles.indicadorAtivo : ""}`}
            onClick={() => onIr(i)}
            aria-label={`Ir para ${titulo}`}
            aria-current={i === indice ? "true" : undefined}
          />
        ))}
      </div>
    </div>
  );
}
