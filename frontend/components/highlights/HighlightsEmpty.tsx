import styles from "./highlights.module.css";

/**
 * Estado vazio (FR-022).
 *
 * Diz o que aconteceu e o que fazer a seguir. Nunca área em branco, nunca
 * "algo deu errado" (SC-008).
 */
export function HighlightsEmpty() {
  return (
    <section className={styles.aviso}>
      <h2 className={styles.avisoTitulo}>Nenhum filme em cartaz agora</h2>
      <p className={styles.avisoTexto}>
        A programação da próxima semana ainda não foi publicada. Volte em breve para ver as
        estreias.
      </p>
    </section>
  );
}
