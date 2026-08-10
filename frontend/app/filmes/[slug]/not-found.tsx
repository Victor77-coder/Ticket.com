import Link from "next/link";

import styles from "./filme.module.css";

export default function NotFound() {
  return (
    <main className={styles.pagina}>
      <section className={styles.erro}>
        <h1>Filme não encontrado</h1>
        <p>
          O endereço acessado não corresponde a nenhum filme da programação. Ele pode ter saído de
          cartaz.
        </p>
        <Link href="/" className={styles.voltar}>
          Ver filmes em cartaz
        </Link>
      </section>
    </main>
  );
}
