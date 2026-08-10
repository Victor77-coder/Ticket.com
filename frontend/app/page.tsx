import { fetchHighlights } from "@/lib/api";
import { HighlightsCarousel } from "@/components/highlights/HighlightsCarousel";
import styles from "@/components/highlights/highlights.module.css";

// A elegibilidade ao destaque depende de "sessão futura", que muda com o
// relógio — a home não pode ser estática (R5).
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const resultado = await fetchHighlights();

  if (!resultado.ok) {
    return (
      <main>
        <section className={styles.aviso} role="alert">
          <h1 className={styles.avisoTitulo}>Não conseguimos carregar a programação</h1>
          <p className={styles.avisoTexto}>
            O servidor não respondeu agora. Atualize a página em alguns instantes — se
            continuar assim, a programação volta assim que o serviço for restabelecido.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <h1 className={styles.apenasLeitorDeTela}>Filmes em cartaz</h1>
      <HighlightsCarousel highlights={resultado.data.results} />
    </main>
  );
}
