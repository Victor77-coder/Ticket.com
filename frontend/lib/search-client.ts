"use client";

import { useEffect, useRef, useState } from "react";

import type { SearchResponse, SearchSuggestion } from "./types";

/**
 * Busca de sugestões no navegador.
 *
 * Três mecanismos combinados garantem que a lista sempre corresponda ao termo
 * atual (FR-015, SC-005) — ver research.md (R3):
 *
 *   1. debounce, para não disparar uma requisição por tecla;
 *   2. AbortController, para cancelar a requisição anterior;
 *   3. guarda por número de sequência, porque o abort NÃO fecha a janela: uma
 *      resposta já decodificada pode chegar depois da mais nova.
 *
 * O item 3 é o que torna SC-005 verdadeiro em vez de provável.
 */

export const DEBOUNCE_MS = 250;

export type SituacaoBusca = "ocioso" | "buscando" | "com-resultados" | "sem-resultados" | "erro";

export type EstadoBusca = {
  situacao: SituacaoBusca;
  sugestoes: SearchSuggestion[];
  truncado: boolean;
  /** O termo a que este estado corresponde — usado nas mensagens. */
  termoAplicado: string;
  mensagemErro: string | null;
};

const OCIOSO: EstadoBusca = {
  situacao: "ocioso",
  sugestoes: [],
  truncado: false,
  termoAplicado: "",
  mensagemErro: null,
};

async function buscarSugestoes(termo: string, signal: AbortSignal): Promise<SearchResponse> {
  const resposta = await fetch(`/api/busca?q=${encodeURIComponent(termo)}`, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(
      typeof corpo?.erro === "string"
        ? corpo.erro
        : "Não foi possível buscar agora. Tente de novo em instantes.",
    );
  }

  return (await resposta.json()) as SearchResponse;
}

export function useSugestoes(termo: string): EstadoBusca {
  const [estado, setEstado] = useState<EstadoBusca>(OCIOSO);

  // Sequência da última requisição disparada e da última já aplicada ao
  // estado. Resposta com número menor que o aplicado é descartada.
  const sequenciaRef = useRef(0);
  const ultimaAplicadaRef = useRef(0);

  useEffect(() => {
    const limpo = termo.trim();

    if (!limpo) {
      // Campo vazio não consulta o servidor (FR-014). A sequência avança
      // assim mesmo, para invalidar qualquer resposta ainda em voo.
      sequenciaRef.current += 1;
      ultimaAplicadaRef.current = sequenciaRef.current;
      setEstado(OCIOSO);
      return;
    }

    setEstado((anterior) => ({ ...anterior, situacao: "buscando", termoAplicado: limpo }));

    const controlador = new AbortController();
    const minhaSequencia = (sequenciaRef.current += 1);

    const aplicar = (proximo: EstadoBusca) => {
      if (minhaSequencia < ultimaAplicadaRef.current) return;
      ultimaAplicadaRef.current = minhaSequencia;
      setEstado(proximo);
    };

    const temporizador = setTimeout(() => {
      buscarSugestoes(limpo, controlador.signal)
        .then((resposta) => {
          aplicar({
            situacao: resposta.results.length > 0 ? "com-resultados" : "sem-resultados",
            sugestoes: resposta.results,
            truncado: resposta.truncated,
            termoAplicado: limpo,
            mensagemErro: null,
          });
        })
        .catch((erro: unknown) => {
          // Requisição abortada não é falha: o usuário só continuou digitando.
          if (erro instanceof DOMException && erro.name === "AbortError") return;

          aplicar({
            situacao: "erro",
            sugestoes: [],
            truncado: false,
            termoAplicado: limpo,
            mensagemErro:
              erro instanceof Error
                ? erro.message
                : "Não foi possível buscar agora. Tente de novo em instantes.",
          });
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(temporizador);
      controlador.abort();
    };
  }, [termo]);

  return estado;
}
