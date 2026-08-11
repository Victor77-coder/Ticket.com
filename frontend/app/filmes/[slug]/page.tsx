import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchMovie } from "@/lib/api";
import type { Screening } from "@/lib/types";
import styles from "./filme.module.css";

// Sem "force-dynamic" de propósito: ele faz o Next começar a transmitir a
// resposta antes de a página decidir, e aí notFound() não consegue mais
// trocar o status para 404. O cache: "no-store" do fetch já garante
// renderização dinâmica.

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

/**
 * Data de estreia, apenas quando ela é futura.
 *
 * Sem data conhecida ou com data no passado, devolve null: anunciar "estreia
 * em" numa data já vencida seria informação errada, e estimar uma data que
 * não temos seria inventar (FR-027, SC-009).
 */
function estreiaFutura(iso: string | null): string | null {
  if (!iso) return null;

  const data = new Date(`${iso}T00:00:00`);
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  if (data <= hoje) return null;

  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(data);
}

function ListaDeSessoes({
  sessoes,
  releaseDate,
}: {
  sessoes: Screening[];
  releaseDate: string | null;
}) {
  if (sessoes.length === 0) {
    const estreia = estreiaFutura(releaseDate);

    return (
      <div className={styles.vazio}>
        {estreia && <p className={styles.estreia}>Estreia em {estreia}</p>}
        <p className={styles.vazioTexto}>
          No momento, este filme não possui sessões programadas.
        </p>
      </div>
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
            <ListaDeSessoes sessoes={filme.screenings} releaseDate={filme.release_date} />
          </section>
        </div>
      </article>
    </main>
  );
}
