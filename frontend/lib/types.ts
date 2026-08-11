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
  /** Alimenta "Estreia em DD/MM/AAAA" quando não há sessões (FR-025). */
  release_date: string | null;
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

/** Papéis do sistema (Princípio IV da constitution). */
export type Papel = "organizer" | "customer" | "gate";

/**
 * Sessão ativa, resolvida no servidor a cada requisição.
 *
 * `papel` escolhe **o que apresentar**, nunca concede acesso: toda
 * autorização continua sendo decidida no servidor (FR-022).
 */
export type Sessao = {
  nome: string;
  papel: Papel;
};

/** Resposta de `POST /api/v1/auth/login/`. */
export type LoginResponse = {
  session_key: string;
  expires_at: string;
  user: Sessao;
};

/** Cartão de filme nas trilhas da home. Sem backdrop e sem trailer. */
export type MovieCard = {
  id: number;
  slug: string;
  title: string;
  /** Nulo aciona o substituto legível no cartão (FR-011). */
  poster_url: string | null;
  certification_br: string | null;
  runtime_minutes: number | null;
  release_date: string | null;
  movie_path: string;
};

export type MovieRowData = {
  key: "em-cartaz" | "em-alta" | "em-breve";
  title: string;
  count: number;
  movies: MovieCard[];
};

/**
 * Trilhas da home.
 *
 * Uma trilha sem filmes **não vem** no array — o servidor a omite. Se veio,
 * renderiza (FR-006).
 */
export type HomeRowsResponse = {
  rows: MovieRowData[];
};

// --- Mapa de assentos (feature 007) --------------------------------------

/**
 * Um lugar do mapa.
 *
 * `tipo` e `situacao` são independentes: um lugar de acessibilidade pode
 * estar livre ou tomado como qualquer outro. "Selecionado" não aparece aqui
 * porque é estado do navegador — não existe no servidor até virar reserva.
 */
export type Assento = {
  id: number;
  numero: number;
  tipo: "comum" | "acessibilidade";
  situacao: "livre" | "tomado";
};

export type Fileira = {
  letra: string;
  assentos: Assento[];
};

/**
 * O mapa de uma sessão.
 *
 * Sem a capacidade da sala: é dado de gestão, e o cliente já recebe todos os
 * lugares (gate do Princípio IV).
 */
export type MapaSessao = {
  id: number;
  filme: { titulo: string; slug: string };
  sala: { nome: string };
  inicio: string;
  preco: string;
  esgotada: boolean;
  limite_por_reserva: number;
  fileiras: Fileira[];
};

/** Um lugar como a reserva confirmada o nomeia. */
export type LugarReservado = {
  fileira: string;
  numero: number;
};

export type Reserva = {
  id: number;
  sessao: number;
  assentos: LugarReservado[];
  total: string;
  /** Instante absoluto — o relógio do navegador pode estar errado. */
  expira_em: string;
  situacao: "reservada" | "expirada";
};
