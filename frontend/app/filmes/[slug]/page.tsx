import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchMovie } from "@/lib/api";
import type { Screening } from "@/lib/types";
import styles from "./filme.module.css";

export const dynamic = "force-dynamic";

function formatarHorario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatarPreco(valor: string) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    Number(valor),
  );
}

function formatarDuracao(minutos: number | null) {
  if (!minutos) return null;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas}h` : `${horas}h${String(resto).padStart(2, "0")}`;
}

function ListaDeSessoes({ sessoes }: { sessoes: Screening[] }) {
  if (sessoes.length === 0) {
    return (
      <p className={styles.vazio}>
        Não há sessões abertas para este filme no momento. A programação da próxima semana é
        publicada às quartas-feiras.
      </p>
    );
  }

  return (
    <ul className={styles.sessoes}>
      {sessoes.map((sessao) => (
        <li key={sessao.id} className={styles.sessao}>
          <div>
            <span className={styles.sessaoHorario}>{formatarHorario(sessao.starts_at)}</span>
            <span className={styles.sessaoSala}>{sessao.room_name}</span>
          </div>
          <div className={styles.sessaoDireita}>
            <span className={styles.sessaoPreco}>{formatarPreco(sessao.price)}</span>
            {sessao.has_available_seats ? (
              <span className={styles.sessaoStatus}>Disponível</span>
            ) : (
              <span className={styles.sessaoEsgotada}>Esgotada</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
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
            {[duracao, filme.genres.join(", ")].filter(Boolean).join(" · ")}
          </p>

          {filme.synopsis && <p className={styles.sinopse}>{filme.synopsis}</p>}

          <section aria-labelledby="titulo-sessoes">
            <h2 id="titulo-sessoes" className={styles.subtitulo}>
              Sessões
            </h2>
            <ListaDeSessoes sessoes={filme.screenings} />
          </section>
        </div>
      </article>
    </main>
  );
}
