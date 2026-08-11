/** Tipos derivados de specs/001-movie-highlights-carousel/contracts/highlights-api.md */

export type Trailer = {
  provider: "youtube";
  external_key: string;
};

export type Highlight = {
  id: number;
  slug: string;
  title: string;
  synopsis_short: string;
  backdrop_url: string | null;
  poster_url: string | null;
  certification_br: string | null;
  runtime_minutes: number | null;
  genres: string[];
  /** Nulo esconde o botão "Trailer" no painel (FR-015). */
  trailer: Trailer | null;
  next_screening_at: string;
  has_available_seats: boolean;
  movie_path: string;
};

export type HighlightsResponse = {
  count: number;
  results: Highlight[];
};

export type Screening = {
  id: number;
  starts_at: string;
  price: string;
  room_name: string;
  has_available_seats: boolean;
};

export type MovieDetail = {
  id: number;
  slug: string;
  title: string;
  synopsis: string;
  backdrop_url: string | null;
  poster_url: string | null;
  certification_br: string | null;
  runtime_minutes: number | null;
  genres: string[];
  screenings: Screening[];
};

/** Derivado de specs/002-site-header-navigation/contracts/search-api.md */

export type SearchSuggestion = {
  slug: string;
  title: string;
  poster_url: string | null;
  year: number | null;
  movie_path: string;
};

export type SearchResponse = {
  /** O termo já normalizado pelo servidor — confirma a qual busca isto responde. */
  termo: string;
  count: number;
  /** Há mais correspondências do que o limite pedido (FR-011). */
  truncated: boolean;
  results: SearchSuggestion[];
};

/**
 * Resultado de uma busca na API.
 *
 * O erro é um valor de retorno, não uma exceção: cada tela precisa decidir o
 * que mostrar, e um `throw` levaria a home inteira para a página de erro do
 * Next em vez do estado de erro do carrossel (FR-024).
 */
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };
