import styles from "./rows.module.css";

/**
 * Esqueleto com a mesma altura da trilha final (FR-028).
 *
 * As dimensões saem das mesmas classes do cartão real, então o conteúdo da
 * página não salta quando os cartazes chegam.
 */
export function MovieRowSkeleton({ cartoes = 6 }: { cartoes?: number }) {
  return (
    <section className={styles.secao} aria-hidden="true">
      <div className={styles.cabecalho}>
        <div
          className={styles.esqueletoMoldura}
          style={{ width: "8rem", height: "1.5rem", aspectRatio: "auto" }}
        />
      </div>
      <div className={styles.trilha}>
        {Array.from({ length: cartoes }, (_, i) => (
          <div key={i} className={styles.esqueletoCartao}>
            <div className={styles.esqueletoMoldura} />
          </div>
        ))}
      </div>
    </section>
  );
}
