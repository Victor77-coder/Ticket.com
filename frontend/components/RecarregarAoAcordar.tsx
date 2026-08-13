"use client";

import { useEffect } from "react";

const INTERVALO_MS = 5000;

/**
 * O plano free do Render dorme. A home acorda num instante; a API leva cerca
 * de um minuto. Sem isto, um refresh nesse intervalo vê a tela de erro e
 * fica nela — o avaliador não tem por que ficar apertando F5.
 */
export function RecarregarAoAcordar() {
  useEffect(() => {
    const id = window.setTimeout(() => {
      window.location.reload();
    }, INTERVALO_MS);
    return () => window.clearTimeout(id);
  }, []);

  return null;
}
