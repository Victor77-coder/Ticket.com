import type { Highlight } from "@/lib/types";

let contador = 0;

export function criarHighlight(sobrescreve: Partial<Highlight> = {}): Highlight {
  contador += 1;
  return {
    id: contador,
    slug: `filme-${contador}`,
    title: `Filme ${contador}`,
    synopsis_short: "Uma sinopse curta o suficiente para caber no painel.",
    backdrop_url: "https://image.tmdb.org/t/p/w1280/backdrop.jpg",
    poster_url: "https://image.tmdb.org/t/p/w500/poster.jpg",
    certification_br: "14",
    runtime_minutes: 128,
    genres: ["Ficção científica"],
    trailer: { provider: "youtube", external_key: `chave-${contador}` },
    next_screening_at: "2026-08-11T19:30:00-03:00",
    has_available_seats: true,
    movie_path: `/filmes/filme-${contador}`,
    ...sobrescreve,
  };
}

export function criarHighlights(quantidade: number): Highlight[] {
  return Array.from({ length: quantidade }, (_, i) =>
    criarHighlight({ title: `Filme ${String.fromCharCode(65 + i)}` }),
  );
}
