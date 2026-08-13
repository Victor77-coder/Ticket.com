"use client";

import { useEffect } from "react";

const INTERVALO_MS = 4000;
const TRAVA_MS = 20000;
const TRAVA_CHAVE = "ticketcom-wake-reload";
const WAKE_URL = process.env.NEXT_PUBLIC_API_WAKE_URL;

/**
 * Plano free: a API dorme. O navegador pinge o /healthz público — isso a
 * acorda. Quando responde ok, recarrega a home uma vez.
 *
 * Sem a trava, /healthz ok + SSR ainda falhando vira refresh infinito.
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
            const ultima = Number(sessionStorage.getItem(TRAVA_CHAVE) || 0);
            if (Date.now() - ultima < TRAVA_MS) {
              return;
            }
            sessionStorage.setItem(TRAVA_CHAVE, String(Date.now()));
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
