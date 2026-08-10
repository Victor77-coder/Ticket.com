import styles from "./highlights.module.css";

/**
 * Esqueleto com a mesma altura do painel final (FR-021).
 *
 * A altura vem do mesmo token `--altura-painel` usado pelo carrossel — é o
 * que impede o restante da página de saltar quando o conteúdo chega.
 */
export function HighlightsSkeleton() {
  return (
    <div className={styles.esqueleto} aria-hidden="true">
      <div className={styles.esqueletoBarra} style={{ width: "9rem", height: "1rem" }} />
      <div className={styles.esqueletoBarra} style={{ width: "min(24ch, 90%)", height: "3rem" }} />
      <div className={styles.esqueletoBarra} style={{ width: "min(46ch, 95%)", height: "1rem" }} />
      <div className={styles.esqueletoBarra} style={{ width: "min(38ch, 80%)", height: "1rem" }} />
      <div
        className={styles.esqueletoBarra}
        style={{ width: "13rem", height: "3rem", borderRadius: "var(--raio-pilula)" }}
      />
    </div>
  );
}
