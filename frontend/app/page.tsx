import { fetchHighlights, fetchHomeRows } from "@/lib/api";
import { HighlightsCarousel } from "@/components/highlights/HighlightsCarousel";
import { MovieRow } from "@/components/rows/MovieRow";
import destaques from "@/components/highlights/highlights.module.css";
import trilhas from "@/components/rows/rows.module.css";

// A elegibilidade ao destaque depende de "sessão futura", que muda com o
// relógio (R5 da feature 001).
export const dynamic = "force-dynamic";

export default async function HomePage() {
  // As duas buscas são independentes: uma falhar não pode derrubar a outra.
  const [highlights, rows] = await Promise.all([fetchHighlights(), fetchHomeRows()]);

  const temDestaques = highlights.ok && highlights.data.results.length > 0;
  const temTrilhas = rows.ok && rows.data.rows.length > 0;

  // Nada carregou: um estado explicativo, nunca página em branco (FR-007).
  if (!temDestaques && !temTrilhas) {
    const falhou = !highlights.ok && !rows.ok;

    return (
      <main>
        <section className={trilhas.aviso} role={falhou ? "alert" : undefined}>
          <h1 className={trilhas.avisoTitulo}>
            {falhou ? "Não conseguimos carregar a programação" : "Nenhum filme em cartaz agora"}
          </h1>
          <p className={trilhas.avisoTexto}>
            {falhou
              ? "O servidor não respondeu agora. Atualize a página em alguns instantes — a programação volta assim que o serviço for restabelecido."
              : "A programação da próxima semana ainda não foi publicada. Volte em breve para ver as estreias."}
          </p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <h1 className={destaques.apenasLeitorDeTela}>Filmes em cartaz</h1>

      {temDestaques && <HighlightsCarousel highlights={highlights.data.results} />}

      {/* A ordem é do servidor; o cliente renderiza o que veio. Trilha vazia
       * nem chega aqui — o back-end a omite (FR-006). */}
      {temTrilhas &&
        rows.data.rows.map((trilha) => <MovieRow key={trilha.key} trilha={trilha} />)}
    </main>
  );
}
