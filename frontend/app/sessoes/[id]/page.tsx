import Link from "next/link";
import { notFound } from "next/navigation";

import SeatSelection from "@/components/seats/SeatSelection";
import { fetchSeatMap } from "@/lib/api";
import { formatarPreco } from "@/lib/moeda";

import estilos from "./sessao.module.css";

// Sem "force-dynamic", pelo mesmo motivo da página do filme: ele faz o Next
// começar a transmitir antes de a página decidir, e notFound() perde a chance
// de trocar o status para 404. O cache: "no-store" do fetch já basta.

function formatarHorario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default async function SessaoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const numero = Number(id);

  if (!Number.isInteger(numero) || numero <= 0) notFound();

  const resultado = await fetchSeatMap(numero);

  if (!resultado.ok) {
    // Rascunho, cancelada, já iniciada e inexistente chegam aqui iguais, e é
    // assim que devem ficar: distinguir revelaria a grade de programação.
    if (resultado.error === "NAO_ENCONTRADO" || resultado.status === 404) notFound();

    return (
      <main className={estilos.pagina}>
        <section className={estilos.erro} role="alert">
          <h1>Não conseguimos carregar esta sessão</h1>
          <p>
            O servidor não respondeu agora. Atualize a página em alguns instantes ou
            escolha outro horário.
          </p>
          <Link href="/" className={estilos.voltar}>
            Ver filmes em cartaz
          </Link>
        </section>
      </main>
    );
  }

  const mapa = resultado.data;

  return (
    <main className={estilos.pagina}>
      <Link href={`/filmes/${mapa.filme.slug}`} className={estilos.voltar}>
        ← {mapa.filme.titulo}
      </Link>

      <header className={estilos.cabecalho}>
        <h1 className={estilos.titulo}>Escolha seus lugares</h1>
        <p className={estilos.detalhes}>
          {formatarHorario(mapa.inicio)} · {mapa.sala.nome} ·{" "}
          {formatarPreco(mapa.preco)} por lugar
        </p>
      </header>

      <SeatSelection mapa={mapa} />
    </main>
  );
}
