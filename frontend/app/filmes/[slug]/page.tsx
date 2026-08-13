import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchMovie } from "@/lib/api";

import FilmeCliente from "./FilmeCliente";
import styles from "./filme.module.css";

// Sem "force-dynamic" de propósito: ele faz o Next começar a transmitir a
// resposta antes de a página decidir, e aí notFound() não consegue mais
// trocar o status para 404. O cache: "no-store" do fetch já garante
// renderização dinâmica.

function formatarDuracao(minutos: number | null) {
  if (!minutos) return null;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas}h` : `${horas}h${String(resto).padStart(2, "0")}`;
}

export default async function MoviePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const resultado = await fetchMovie(slug);

  if (!resultado.ok) {
    if (resultado.error === "NAO_ENCONTRADO") notFound();

    return (
      <main className={styles.pagina}>
        <section className={styles.erro} role="alert">
          <h1>Não conseguimos carregar este filme</h1>
          <p>
            O servidor não respondeu agora. Atualize a página em alguns instantes ou volte para a
            programação.
          </p>
          <Link href="/" className={styles.voltar}>
            Ver filmes em cartaz
          </Link>
        </section>
      </main>
    );
  }

  const filme = resultado.data;
  const duracao = formatarDuracao(filme.runtime_minutes);
  const metadados = [duracao, filme.genres.join(", ")].filter(Boolean).join(" · ");


  return (
    <main className={styles.pagina}>
      <Link href="/" className={styles.voltar}>
        ← Filmes em cartaz
      </Link>

      <article className={styles.filme}>
        <div className={styles.cartaz}>
          {filme.poster_url ? (
            <Image
              src={filme.poster_url}
              alt={`Cartaz de ${filme.title}`}
              width={320}
              height={480}
              className={styles.cartazImagem}
            />
          ) : (
            <div className={styles.cartazFallback} aria-hidden="true" />
          )}
        </div>

        <div className={styles.informacoes}>
          <h1 className={styles.titulo}>{filme.title}</h1>

          <p className={styles.metadados}>
            {filme.certification_br && (
              <span className={styles.classificacao}>{filme.certification_br}</span>
            )}
            {metadados}
          </p>

          <FilmeCliente filme={filme} />
        </div>
      </article>
    </main>
  );
}
