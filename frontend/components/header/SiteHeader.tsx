import { BrandMark } from "./BrandMark";
import { SearchBox } from "./SearchBox";
import styles from "./header.module.css";

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
export function SiteHeader() {
  return (
    <header className={styles.faixa}>
      <div className={styles.conteudo}>
        <BrandMark />
        <div className={styles.espacoBusca}>
          <SearchBox />
        </div>
        {/* conta — preenchida na US3, hoje bloqueada pela feature de autenticação */}
        <div className={styles.espacoConta} />
      </div>
    </header>
  );
}
