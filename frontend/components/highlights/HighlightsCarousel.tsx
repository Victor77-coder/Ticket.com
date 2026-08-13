"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { Highlight } from "@/lib/types";
import { CarouselControls } from "./CarouselControls";
import { HighlightPanel } from "./HighlightPanel";
import { HighlightsEmpty } from "./HighlightsEmpty";
import styles from "./highlights.module.css";

const INTERVALO_ROTACAO_MS = 7000;
const LIMIAR_ARRASTO_PX = 50;

type Props = {
  highlights: Highlight[];
};

/**
 * Carrossel de filmes em destaque.
 *
 * Trilha deslocada por translateX com índice modular (R1): o ciclo (FR-008)
 * sai de graça, ao custo de escrever o gesto de toque à mão.
 *
 * Ao dar a volta (último → primeiro) a trilha salta sem animação, em vez de
 * rebobinar atravessando todos os painéis. É honesto e legível — a ilusão de
 * fita infinita não vale a complexidade para 5 painéis.
 */
export function HighlightsCarousel({ highlights }: Props) {
  const total = highlights.length;

  const [indice, setIndice] = useState(0);
  const [semAnimacao, setSemAnimacao] = useState(false);
  const [trailerAberto, setTrailerAberto] = useState(false);
  const [pausadoPorPonteiro, setPausadoPorPonteiro] = useState(false);
  const [pausadoPorFoco, setPausadoPorFoco] = useState(false);
  const [movimentoReduzido, setMovimentoReduzido] = useState(false);
  // aria-live fica "off" durante a rotação automática e vira "polite" quando a
  // troca partiu do usuário — anunciar cada troca automática inundaria o
  // leitor de tela (R9).
  const [trocaFoiDoUsuario, setTrocaFoiDoUsuario] = useState(false);

  const arrastoInicialRef = useRef<number | null>(null);

  useEffect(() => {
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");
    setMovimentoReduzido(consulta.matches);

    const aoMudar = (evento: MediaQueryListEvent) => setMovimentoReduzido(evento.matches);
    consulta.addEventListener("change", aoMudar);
    return () => consulta.removeEventListener("change", aoMudar);
  }, []);

  const irPara = useCallback(
    (proximo: number, doUsuario = true) => {
      if (total === 0) return;

      const normalizado = ((proximo % total) + total) % total;
      const deuVolta =
        (indice === total - 1 && normalizado === 0) || (indice === 0 && normalizado === total - 1);

      setTrocaFoiDoUsuario(doUsuario);
      // Fechar o trailer ao trocar de painel desmonta o iframe e encerra a
      // reprodução (FR-014, FR-016).
      setTrailerAberto(false);

      if (deuVolta) {
        setSemAnimacao(true);
        setIndice(normalizado);
        // Devolve a animação no quadro seguinte, senão o próximo avanço
        // normal também sairia sem transição.
        requestAnimationFrame(() => requestAnimationFrame(() => setSemAnimacao(false)));
      } else {
        setIndice(normalizado);
      }
    },
    [indice, total],
  );

  const proximo = useCallback((doUsuario = true) => irPara(indice + 1, doUsuario), [indice, irPara]);
  const anterior = useCallback(() => irPara(indice - 1), [indice, irPara]);

  const rotacaoPausada =
    pausadoPorPonteiro || pausadoPorFoco || trailerAberto || movimentoReduzido || total <= 1;

  useEffect(() => {
    if (rotacaoPausada) return;

    const temporizador = window.setInterval(() => proximo(false), INTERVALO_ROTACAO_MS);
    return () => window.clearInterval(temporizador);
  }, [rotacaoPausada, proximo]);

  function aoTeclar(evento: React.KeyboardEvent<HTMLElement>) {
    if (evento.key === "ArrowRight") {
      evento.preventDefault();
      proximo();
    } else if (evento.key === "ArrowLeft") {
      evento.preventDefault();
      anterior();
    }
  }

  function aoPressionarPonteiro(evento: React.PointerEvent<HTMLElement>) {
    if (evento.pointerType === "mouse") return;
    arrastoInicialRef.current = evento.clientX;
  }

  function aoSoltarPonteiro(evento: React.PointerEvent<HTMLElement>) {
    const inicio = arrastoInicialRef.current;
    arrastoInicialRef.current = null;
    if (inicio === null) return;

    const deslocamento = evento.clientX - inicio;
    if (Math.abs(deslocamento) < LIMIAR_ARRASTO_PX) return;

    if (deslocamento < 0) proximo();
    else anterior();
  }

  if (total === 0) {
    return <HighlightsEmpty />;
  }

  return (
    <section
      className={styles.regiao}
      role="region"
      aria-roledescription="carousel"
      aria-label="Filmes em cartaz"
      onKeyDown={aoTeclar}
      onMouseEnter={() => setPausadoPorPonteiro(true)}
      onMouseLeave={() => setPausadoPorPonteiro(false)}
      onFocusCapture={() => setPausadoPorFoco(true)}
      onBlurCapture={(evento) => {
        if (!evento.currentTarget.contains(evento.relatedTarget as Node | null)) {
          setPausadoPorFoco(false);
        }
      }}
      onPointerDown={aoPressionarPonteiro}
      onPointerUp={aoSoltarPonteiro}
      onPointerCancel={() => {
        arrastoInicialRef.current = null;
      }}
    >
      <div
        className={`${styles.trilha} ${semAnimacao ? styles.trilhaSemAnimacao : ""}`}
        style={{ transform: `translateX(-${indice * 100}%)` }}
        aria-live={trocaFoiDoUsuario ? "polite" : "off"}
      >
        {highlights.map((highlight, i) => (
          <HighlightPanel
            key={highlight.id}
            highlight={highlight}
            posicao={i + 1}
            total={total}
            ativo={i === indice}
            trailerAberto={trailerAberto && i === indice}
            onAbrirTrailer={() => setTrailerAberto(true)}
            onFecharTrailer={() => setTrailerAberto(false)}
          />
        ))}
      </div>

      {total > 1 && (
        <CarouselControls
          indice={indice}
          titulos={highlights.map((h) => h.title)}
          onAnterior={anterior}
          onProximo={() => proximo()}
          onIr={irPara}
        />
      )}
    </section>
  );
}
