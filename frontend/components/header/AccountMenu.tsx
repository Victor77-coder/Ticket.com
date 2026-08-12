"use client";

import Link from "next/link";
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
 * Onde cada papel trabalha.
 *
 * `organizer` está ausente de propósito: o painel do organizador ainda não
 * existe, e apontar para uma tela que recusa por papel seria pior do que não
 * ter o item. Quando ele existir, entra aqui — e é por isso que isto é uma
 * tabela e não dois `if`.
 */
const DESTINO_DO_PAPEL: Partial<Record<Sessao["papel"], { href: string; rotulo: string }>> =
  {
    customer: { href: "/meus-ingressos", rotulo: "Meus ingressos" },
    gate: { href: "/portaria", rotulo: "Validar ingressos" },
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

          {/* O destino de trabalho de cada papel.
            *
            * Cada papel tem UM lugar onde faz o que veio fazer, e é daqui que
            * ele chega lá. Sem este item o usuário de portaria entra, cai no
            * catálogo de filmes — que não é a tela dele — e não tem caminho
            * nenhum até a validação a não ser digitar o endereço. Um papel
            * cuja tela só é alcançável por endereço decorado é uma tela que,
            * na prática, não existe.
            *
            * O organizador não aparece aqui porque o painel dele não existe
            * ainda, e um item que leva a uma recusa por papel é pior do que
            * item nenhum. Quando o painel existir, ele entra nesta tabela.
            *
            * O menu da conta é o lugar certo, e não a navegação principal do
            * cabeçalho: o destino MUDA por papel, e um item de navegação
            * global que troca de rótulo conforme quem olha seria mais
            * confuso do que útil. */}
          {DESTINO_DO_PAPEL[sessao.papel] && (
            <Link
              href={DESTINO_DO_PAPEL[sessao.papel]!.href}
              role="menuitem"
              className={styles.contaMenuItem}
              onClick={() => setAberto(false)}
            >
              {DESTINO_DO_PAPEL[sessao.papel]!.rotulo}
            </Link>
          )}

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
