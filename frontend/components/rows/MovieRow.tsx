"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { MovieRowData } from "@/lib/types";
import { MovieCard } from "./MovieCard";
import styles from "./rows.module.css";

type Props = {
  trilha: MovieRowData;
};

/**
 * Trilha horizontal de cartazes.
 *
 * Usa `scroll-snap` nativo — ao contrário do carrossel da home, que foi
 * escrito à mão. Aqui não há ciclo a fechar nem rotação automática, que eram
 * os dois motivos daquela decisão. Sem eles o CSS entrega gesto, inércia e
 * rolagem por teclado de graça e melhor (R1).
 *
 * O JavaScript aqui faz uma coisa só: decidir se as setas aparecem.
 */
export function MovieRow({ trilha }: Props) {
  const trilhaRef = useRef<HTMLDivElement>(null);
  const [podeVoltar, setPodeVoltar] = useState(false);
  const [podeAvancar, setPodeAvancar] = useState(false);
  const [temTransbordo, setTemTransbordo] = useState(false);

  const avaliarPosicao = useCallback(() => {
    const el = trilhaRef.current;
    if (!el) return;

    // Margem de 1px absorve o arredondamento subpixel do navegador, que
    // senão deixaria a seta "avançar" habilitada no fim da trilha.
    const transbordou = el.scrollWidth > el.clientWidth + 1;
    setTemTransbordo(transbordou);
    setPodeVoltar(el.scrollLeft > 1);
    setPodeAvancar(transbordou && el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  useEffect(() => {
    const el = trilhaRef.current;
    if (!el) return;

    avaliarPosicao();

    // ResizeObserver e não só a montagem: o transbordo muda quando a janela é
    // redimensionada, e checar uma vez daria resposta errada depois (R7).
    const observador = new ResizeObserver(avaliarPosicao);
    observador.observe(el);

    return () => observador.disconnect();
  }, [avaliarPosicao]);

  function deslizar(direcao: 1 | -1) {
    const el = trilhaRef.current;
    if (!el) return;
    // Rola quase uma tela inteira, deixando um cartaz de referência visível.
    el.scrollBy({ left: direcao * el.clientWidth * 0.85 });
  }

  const idTitulo = `trilha-${trilha.key}`;

  return (
    <section className={styles.secao} aria-labelledby={idTitulo}>
      <div className={styles.cabecalho}>
        <h2 className={styles.titulo} id={idTitulo}>
          {trilha.title}
          {/* A quantidade é anunciada sem poluir o visual (FR-019). */}
          <span className={styles.apenasLeitorDeTela}>
            {` — ${trilha.count} ${trilha.count === 1 ? "filme" : "filmes"}`}
          </span>
        </h2>

        {/* Seta só existe quando há conteúdo além da borda. Uma seta
         * permanentemente desabilitada sugere conteúdo que não existe. */}
        {temTransbordo && (
          <div className={styles.controles}>
            <button
              type="button"
              className={styles.seta}
              onClick={() => deslizar(-1)}
              disabled={!podeVoltar}
              aria-label={`Ver filmes anteriores em ${trilha.title}`}
            >
              <Seta direcao="esquerda" />
            </button>
            <button
              type="button"
              className={styles.seta}
              onClick={() => deslizar(1)}
              disabled={!podeAvancar}
              aria-label={`Ver mais filmes em ${trilha.title}`}
            >
              <Seta direcao="direita" />
            </button>
          </div>
        )}
      </div>

      <div className={styles.trilha} ref={trilhaRef} onScroll={avaliarPosicao}>
        {trilha.movies.map((filme) => (
          <MovieCard key={filme.id} filme={filme} />
        ))}
      </div>
    </section>
  );
}

function Seta({ direcao }: { direcao: "esquerda" | "direita" }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d={direcao === "esquerda" ? "M15 5l-7 7 7 7" : "M9 5l7 7-7 7"}
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
