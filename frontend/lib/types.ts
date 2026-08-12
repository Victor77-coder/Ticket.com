/** Tipos derivados de specs/001-movie-highlights-carousel/contracts/highlights-api.md */

export type Trailer = {
  provider: "youtube";
  external_key: string;
};

/**
 * Trailer na página do filme. Distinto do `Trailer` da home de propósito:
 * `kind` e `name` já existem no modelo, mas o carrossel **não** os recebe
 * (contrato da 001). Reaproveitar um tipo só vazaria o campo para a vitrine.
 */
export type TrailerDoFilme = {
  provider: "youtube" | string;
  external_key: string;
  kind: "trailer" | "teaser";
  name: string;
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
  /** Lista, nunca omitida, nunca `null`. Vazia = seção Trailers explica. */
  trailers: TrailerDoFilme[];
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
export type ApiResult<T> =
  | { ok: true; data: T }
  /**
   * `corpoErro` traz a resposta de erro inteira, para os casos em que ela
   * carrega mais do que a frase — o `409` da reserva, por exemplo, nomeia
   * quais lugares causaram a recusa. Opcional de propósito: os consumidores
   * das features 001–003 continuam usando só `error`.
   */
  | { ok: false; error: string; corpoErro?: unknown };

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

/**
 * A cobrança aprovada, como o comprador a vê.
 *
 * Só os quatro últimos dígitos e a bandeira: não há cobrança real, então
 * guardar o número seria risco sem contrapartida (FR-011).
 */
export type Pagamento = {
  cartao_final: string;
  bandeira: string;
  total: string;
  pago_em: string;
};

/**
 * Um ingresso — **um por lugar**, nunca um por reserva.
 *
 * `codigo` e `qr_svg` andam juntos: o código é a verdade assinada pelo
 * servidor, o QR é uma representação dele. O texto fica visível porque a
 * portaria exige digitação manual como alternativa sempre disponível, e um QR
 * que não carrega não pode deixar a pessoa sem nada (FR-038).
 */
export type Ingresso = {
  codigo: string;
  /** `data:` URI — entra num `<img>` com `alt`, sem markup solto no DOM. */
  qr_svg: string;
  filme: string;
  sessao: string;
  sala: string;
  assento: LugarReservado;
};

export type Reserva = {
  id: number;
  sessao: number;
  assentos: LugarReservado[];
  total: string;
  /**
   * Instante absoluto — o relógio do navegador pode estar errado.
   *
   * Continua presente numa reserva paga, com o valor original e **sem
   * significado de prazo**: reserva paga não vence. Quem decide não exibir a
   * contagem é a tela, olhando `situacao`.
   */
  expira_em: string;
  situacao: "reservada" | "expirada" | "paga";
  /** Só quando `situacao === "paga"`. */
  pagamento?: Pagamento;
  /** Só quando `situacao === "paga"`. Um por lugar reservado. */
  ingressos?: Ingresso[];
  detail?: string;
};

/**
 * O estado do link de compartilhamento de um ingresso.
 *
 * O endereço vem **completo** do servidor, pronto para copiar e enviar.
 * Montá-lo aqui exigiria que o navegador soubesse a origem pública, o que
 * erra atrás de proxy (FR-024).
 */
export type LinkDeCompartilhamento = {
  ativo: boolean;
  endereco: string | null;
};

/**
 * O ingresso como o **dono** o vê.
 *
 * Amplia `Ingresso` com o que só faz sentido para quem comprou. Os campos
 * extras **não** existem na página compartilhada, e a separação é estrutural:
 * lá o servidor responde com o recorte de `Ingresso` e mais nada (FR-037).
 */
export type MeuIngresso = Ingresso & {
  /** Identidade pública — endereça o ingresso nas rotas do dono. */
  id: string;
  grupo: "futuro" | "passado";
  sessao_cancelada: boolean;
  /** Só na rota do ingresso individual, nunca na lista. */
  link?: LinkDeCompartilhamento;
};

/**
 * A lista de "Meus ingressos".
 *
 * Os grupos vêm **separados e ordenados do servidor**: futuros em ordem
 * crescente de sessão, passados em decrescente. A tela não recompara datas —
 * a fronteira entre futuro e passado é decisão do servidor (FR-010).
 */
export type ListaDeIngressos = {
  futuros: MeuIngresso[];
  passados: MeuIngresso[];
};

/**
 * Uma sessão que a portaria pode receber — a "sessão da porta".
 *
 * Filme, horário e sala: o que o operador precisa para reconhecer onde está.
 * Nada de preço, capacidade ou status — a portaria não gerencia nada.
 */
export type SessaoDaPorta = {
  id: number;
  filme: string;
  inicio: string;
  sala: string;
};

/**
 * O desfecho de uma apresentação de código na portaria.
 *
 * `situacao` é um valor FIXO, e é por ele que a tela escolhe símbolo, título e
 * destaque — **nunca** interpretando `detail`, que é apresentação e muda numa
 * revisão de redação.
 *
 * `invalido` vem sem nenhum campo além de `situacao` e `detail`, e a ausência é
 * requisito: qualquer detalhe a mais entregaria a quem tenta adivinhar a
 * informação que o desfecho existe para negar.
 */
export type Desfecho = {
  situacao: "valido" | "invalido" | "ja_utilizado" | "sessao_errada";
  detail: string;
  /** Em `valido` e `ja_utilizado`. */
  ingresso?: {
    filme: string;
    sessao: string;
    sala: string;
    assento: LugarReservado;
  };
  /** Só em `ja_utilizado` — é o que permite julgar quem está apresentando. */
  utilizado_em?: string;
  /** Só em `sessao_errada` — é o que permite orientar a pessoa. */
  sessao_do_ingresso?: {
    filme: string;
    inicio: string;
    sala: string;
    cancelada: boolean;
  };
};

/** O corpo do `201` do pagamento aprovado. */
export type PagamentoAprovado = {
  situacao: "paga";
  pagamento: Pagamento;
  ingressos: Ingresso[];
};

/**
 * O corpo do `402`.
 *
 * `expira_em` volta de propósito: é a prova observável de que a recusa **não
 * mexeu no prazo** da reserva (FR-027).
 */
export type PagamentoRecusado = {
  situacao: "recusada";
  motivo: string;
  detail: string;
  expira_em: string;
};

// --- Programação do organizador (feature 013) -----------------------------
//
// FRONTEIRA DE DADOS: estes tipos carregam `status`, `capacidade` e ocupação
// NUMÉRICA — campos que nenhuma resposta pública expõe (data-model.md §fronteira
// entre painel e público). Não reaproveitar `MovieCard`, `MapaSessao` ou
// `SessaoDaPorta` aqui: a projeção pobre daqueles tipos é o que impede um campo
// de gestão vazar para a vitrine, e um tipo compartilhado dissolveria a
// fronteira sem que nada quebrasse.

/** Um filme do catálogo LOCAL, para escolher sem passar pelo TMDb (FR-013). */
export type FilmeDoPainel = {
  id: number;
  tmdb_id: number;
  titulo: string;
  ano: number | null;
  poster_url: string | null;
  duracao_min: number | null;
  /** Sessões não canceladas — agregado, nunca contado por linha. */
  sessoes: number;
};

/** Um resultado da busca no TMDb, feita pelo back-end (FR-009, FR-010). */
export type ResultadoTmdb = {
  tmdb_id: number;
  titulo: string;
  ano: number | null;
  poster_url: string | null;
  /** Resolvido em UMA consulta `__in`, nunca uma por resultado. */
  ja_no_catalogo: boolean;
};

export type SalaDoPainel = {
  id: number;
  nome: string;
  capacidade: number;
  /** Pode divergir de `capacidade` numa sala do seed acima do teto. */
  lugares: number;
  acessiveis: number;
  ocupacao_viva: number;
  /**
   * `ocupacao_viva === 0`. Existe para a interface **desabilitar com
   * explicação**, nunca como autorização — o PATCH revalida (FR-020, FR-037).
   */
  pode_trocar_capacidade: boolean;
};

export type EstadoDaSessao = "draft" | "published" | "cancelled";

/**
 * Uma linha da grade do organizador.
 *
 * É a única superfície do sistema que expõe `estado` (FR-029).
 *
 * Os três `pode_*` são conveniência de interface e o servidor revalida os três
 * na ação. Um deles vindo `true` nunca é permissão — é uma dica sobre o que
 * vale a pena oferecer.
 */
export type SessaoDaGrade = {
  id: number;
  estado: EstadoDaSessao;
  estado_rotulo: string;
  filme: { id: number; titulo: string; poster_url: string | null };
  sala: { id: number; nome: string; lugares: number };
  inicio: string;
  preco: string;
  /** Agregada em UMA consulta sobre a grade, nunca `seats_taken` por linha. */
  ocupacao: number;
  /** `sellable()` — publicada E no futuro. Leitura, sem responsabilidade nova. */
  a_venda: boolean;
  pode_editar: boolean;
  pode_publicar: boolean;
  pode_cancelar: boolean;
};

export type ListaDeFilmesDoPainel = { count: number; results: FilmeDoPainel[] };
export type BuscaTmdbResponse = { termo: string; count: number; results: ResultadoTmdb[] };
export type ListaDeSalas = { count: number; results: SalaDoPainel[] };
export type GradeResponse = { count: number; results: SessaoDaGrade[] };

/** O que o formulário envia para criar uma sessão. */
export type NovaSessao = {
  filme: number;
  sala: number;
  inicio: string;
  preco: string;
  publicar: boolean;
};
