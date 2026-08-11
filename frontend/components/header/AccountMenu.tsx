"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { Sessao } from "@/lib/types";
import { AccountButton } from "./AccountButton";
import styles from "./header.module.css";

type Props = {
  sessao: Sessao | null;
  caminhoEntrada: string;
};

/**
 * Ilha cliente que dá dono ao `onAbrirConta` do `AccountButton`.
 *
 * O `AccountButton` da feature 002 já previa o estado autenticado com um
 * callback deliberadamente sem dono, esperando esta feature. Estado de
 * abertura e ação de rede são de cliente; o `SiteHeader` é server component e
 * não pode hospedá-los. A ilha isolada resolve os dois sem arrastar o layout
 * inteiro para o bundle.
 */
export function AccountMenu({ sessao, caminhoEntrada }: Props) {
  const router = useRouter();
  const [aberto, setAberto] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;

    function aoClicarFora(evento: MouseEvent) {
      if (!containerRef.current?.contains(evento.target as Node)) {
        setAberto(false);
      }
    }

    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") setAberto(false);
    }

    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  async function sair() {
    setSaindo(true);
    try {
      // POST, nunca GET: um GET que encerra sessão pode ser disparado por
      // pré-carregamento de link ou por imagem em outro site (R8).
      await fetch("/api/sair", { method: "POST" });
    } finally {
      setAberto(false);
      setSaindo(false);
      // `refresh` faz o cabeçalho reler a sessão no servidor, devolvendo-o ao
      // estado de visitante em todas as páginas (FR-015).
      router.refresh();
    }
  }

  if (!sessao) {
    return <AccountButton usuario={null} caminhoEntrada={caminhoEntrada} />;
  }

  return (
    <div className={styles.contaContainer} ref={containerRef}>
      <AccountButton
        usuario={{ nome: sessao.nome }}
        onAbrirConta={() => setAberto((atual) => !atual)}
      />

      {aberto && (
        <div className={styles.contaMenu} role="menu" aria-label="Sua conta">
          <p className={styles.contaMenuPapel}>{rotuloDoPapel(sessao.papel)}</p>
          <button
            type="button"
            role="menuitem"
            className={styles.contaMenuItem}
            onClick={sair}
            disabled={saindo}
          >
            {saindo ? "Saindo…" : "Sair"}
          </button>
        </div>
      )}
    </div>
  );
}

function rotuloDoPapel(papel: Sessao["papel"]): string {
  const rotulos = {
    organizer: "Organizador",
    customer: "Cliente",
    gate: "Portaria",
  } as const;
  return rotulos[papel];
}
