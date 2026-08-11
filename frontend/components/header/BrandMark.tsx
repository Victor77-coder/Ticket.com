import Link from "next/link";

import styles from "./header.module.css";

/**
 * Identidade do site (FR-002).
 *
 * Wordmark textual, não imagem (R8): escala com o zoom, é selecionável e é
 * lido corretamente por leitor de tela sem precisar de texto alternativo.
 *
 * O sufixo `.com` é parte do nome, não uma URL — o destino é sempre a home
 * deste site.
 *
 * O `aria-label` não é redundante: o algoritmo de nome acessível insere um
 * espaço na fronteira entre elementos, e sem ele o link seria anunciado como
 * "ticket .com". A separação em dois elementos existe só para o tratamento
 * tipográfico e não pode vazar para o que o leitor de tela fala.
 */
export function BrandMark() {
  return (
    <Link href="/" className={styles.marca} aria-label="ticket.com, ir para a página inicial">
      ticket<span className={styles.marcaSufixo}>.com</span>
    </Link>
  );
}
