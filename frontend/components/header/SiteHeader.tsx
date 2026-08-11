import type { Sessao } from "@/lib/types";
import { AccountMenu } from "./AccountMenu";
import { BrandMark } from "./BrandMark";
import { SearchBox } from "./SearchBox";
import styles from "./header.module.css";

type Props = {
  /** Sessão já resolvida pelo layout, ou `null` para visitante. */
  sessao?: Sessao | null;
};

/**
 * Cabeçalho global — presente em todas as páginas (FR-001).
 *
 * Server component: nada aqui precisa de estado. Só a busca é interativa, e
 * ela é uma ilha cliente própria. Manter o invólucro no servidor evita
 * arrastar o layout inteiro para o bundle.
 *
 * `<header>` fora de qualquer <article>/<section> é a landmark `banner` — a
 * região que tecnologias assistivas usam para pular direto ao topo do site
 * (FR-027). Não é preciso role explícito.
 */
// A sessão chega pronta do layout, não é buscada aqui: manter o cabeçalho
// síncrono preserva a decisão da feature 002 de mantê-lo testável como
// componente, e deixa a busca de dados num lugar só.
export function SiteHeader({ sessao = null }: Props) {
  return (
    <header className={styles.faixa}>
      <div className={styles.conteudo}>
        <BrandMark />
        <div className={styles.espacoBusca}>
          <SearchBox />
        </div>
        <div className={styles.espacoConta}>
          <AccountMenu sessao={sessao} caminhoEntrada="/entrar" />
        </div>
      </div>
    </header>
  );
}
