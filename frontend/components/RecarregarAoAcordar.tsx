"use client";

import { useEffect } from "react";

const INTERVALO_MS = 4000;
const WAKE_URL = process.env.NEXT_PUBLIC_API_WAKE_URL;

/**
 * O plano free do Render dorme. A home acorda num instante; a API, não.
 *
 * O Next fala com o Django pela rede interna. Essa rota NÃO acorda um
 * serviço dormindo — e a URL pública, chamada de dentro do Render, dá
 * ETIMEDOUT (hairpin). Quem consegue acordar a API é o navegador.
 */
export function RecarregarAoAcordar() {
  useEffect(() => {
    let cancelado = false;

    async function tentar() {
      if (WAKE_URL) {
        try {
          const resposta = await fetch(`${WAKE_URL}/healthz`, { cache: "no-store" });
          const corpo = await resposta.text();
          if (!cancelado && resposta.ok && corpo.trim() === "ok") {
            window.location.reload();
            return;
          }
        } catch {
          // Ainda dormindo ou CORS — tenta de novo.
        }
      }
      if (!cancelado) {
        window.setTimeout(tentar, INTERVALO_MS);
      }
    }

    void tentar();
    return () => {
      cancelado = true;
    };
  }, []);

  return null;
}
