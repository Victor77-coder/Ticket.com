import Link from "next/link";

import styles from "./header.module.css";

/**
 * Ponto de acesso à conta (FR-019, FR-020).
 *
 * ⚠️ NÃO MONTADO NO CABEÇALHO AINDA. O FR-023 proíbe que este ponto conduza a
 * um destino inexistente, e a rota de entrada pertence à feature de
 * autenticação. O componente e seus testes existem para que a US3 feche
 * assim que o destino existir — ver Complexity Tracking no plan.md.
 *
 * Este componente não decide nada sobre permissão. Ele lê um estado e escolhe
 * o que mostrar; toda autorização continua no servidor (FR-025, Princípio IV).
 */

type Props = {
  /** Sessão ativa, ou `null` para visitante não autenticado. */
  usuario?: { nome: string } | null;
  /** Destino do estado de visitante. Entregue pela feature de autenticação. */
  caminhoEntrada?: string;
  /** Ação do estado autenticado. Também entregue pela feature de autenticação. */
  onAbrirConta?: () => void;
};

/**
 * Ícone de pessoa desenhado para este cabeçalho.
 *
 * Traço com a mesma espessura do resto da interface e ombros largos o
 * bastante para continuar legível a 20px — não é um glifo genérico importado
 * de biblioteca (Princípio V).
 */
function IconePessoa() {
  return (
    <svg
      className={styles.contaIcone}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.8 20c0-3.6 3.2-5.8 7.2-5.8s7.2 2.2 7.2 5.8" />
    </svg>
  );
}

export function AccountButton({ usuario = null, caminhoEntrada = "/entrar", onAbrirConta }: Props) {
  if (usuario) {
    return (
      <button type="button" className={styles.conta} onClick={onAbrirConta}>
        <IconePessoa />
        {/* O nome é o que diferencia os dois estados. Cor sozinha não
         * comunicaria a diferença (FR-028). */}
        <span className={styles.contaTexto}>{usuario.nome}</span>
      </button>
    );
  }

  return (
    <Link href={caminhoEntrada} className={styles.conta} aria-label="Entrar na sua conta">
      <IconePessoa />
      <span className={styles.contaTexto} aria-hidden="true">
        Entrar
      </span>
    </Link>
  );
}
